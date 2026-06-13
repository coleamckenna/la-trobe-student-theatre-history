#!/usr/bin/env python3
"""Generate Zensical wiki pages from exported production metadata."""

from __future__ import annotations

import os
import posixpath
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

from media_embeds import transform_external_media


REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_CONFIG_PATH = REPO_ROOT / "wiki.toml"
DISCUSSIONS_MAP_PATH = REPO_ROOT / "discussions-map.toml"
SOURCE_ROOT = REPO_ROOT / "productions"
DOCS_ROOT = REPO_ROOT / "docs"
DOCS_PRODUCTIONS = DOCS_ROOT / "productions"
DOCS_CATEGORIES = DOCS_ROOT / "categories"

MONTH_NAMES = {
    "00": "Unknown month",
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}


@dataclass(frozen=True)
class Production:
    source_path: Path
    source_rel: str
    output_rel: Path
    title: str
    year: str
    month: str
    date: str
    categories: tuple[str, ...]
    source_url: str
    body: str
    frontmatter: str


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"Missing source directory: {SOURCE_ROOT}")

    wiki_config = load_wiki_config()
    discussions_map = load_discussions_map()
    productions = read_productions()
    reset_generated_dirs()
    write_production_pages(productions, wiki_config, discussions_map)
    write_production_indexes(productions)
    write_category_indexes(productions)

    print(
        "Generated "
        f"{len(productions)} production pages, "
        f"{count_years(productions)} year indexes, and "
        f"{count_categories(productions)} category indexes."
    )


def read_productions() -> list[Production]:
    productions: list[Production] = []

    for source_path in sorted(SOURCE_ROOT.rglob("production.md")):
        text = source_path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        metadata = parse_frontmatter(frontmatter)
        source_rel = source_path.relative_to(REPO_ROOT).as_posix()
        source_parts = source_path.relative_to(SOURCE_ROOT).parts

        title = metadata.get("title") or extract_heading(body) or source_path.parent.name
        year = metadata.get("year") or path_year(source_parts)
        month = normalize_month(metadata.get("month") or path_month(source_parts))
        date = metadata.get("date", "")
        source_url = metadata.get("source_url", "")
        categories = extract_categories(body)
        output_rel = output_path_for(source_parts)

        productions.append(
            Production(
                source_path=source_path,
                source_rel=source_rel,
                output_rel=output_rel,
                title=title,
                year=year,
                month=month,
                date=date,
                categories=categories,
                source_url=source_url,
                body=body,
                frontmatter=frontmatter,
            )
        )

    return productions


def split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        return "", text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            if text.endswith("\n"):
                body += "\n"
            return frontmatter, body

    return "", text


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    metadata: dict[str, str] = {}

    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        key, separator, value = line.partition(":")
        if not separator:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        metadata[key.strip()] = value

    return metadata


def extract_heading(body: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_categories(body: str) -> tuple[str, ...]:
    match = re.search(
        r"^## Categories\s*\n(?P<categories>.*?)(?=^##\s|\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ()

    raw_categories = match.group("categories").strip()
    categories: list[str] = []
    seen: set[str] = set()

    for value in re.split(r"[,|]", raw_categories):
        category = " ".join(value.strip().split())
        if not category:
            continue

        key = category.casefold()
        if key in seen:
            continue

        seen.add(key)
        categories.append(category)

    return tuple(categories)


def path_year(parts: tuple[str, ...]) -> str:
    if parts and parts[0].isdigit():
        return parts[0]
    return "Undated"


def path_month(parts: tuple[str, ...]) -> str:
    if len(parts) > 1 and parts[1].isdigit():
        return parts[1]
    return ""


def normalize_month(value: str) -> str:
    if not value:
        return ""
    if value.isdigit():
        return value.zfill(2)
    return value


def output_path_for(parts: tuple[str, ...]) -> Path:
    return Path("productions", *parts[:-1], "index.md")


def reset_generated_dirs() -> None:
    for directory in (DOCS_PRODUCTIONS, DOCS_CATEGORIES):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)


def load_wiki_config() -> dict[str, str]:
    defaults = {
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
        "branch": "main",
        "discussions_category": "historical-corrections-and-contributions",
        "base_url": "",
    }
    if not WIKI_CONFIG_PATH.exists():
        return defaults

    file_values = parse_toml_like(WIKI_CONFIG_PATH.read_text(encoding="utf-8"))
    github = file_values.get("github", {})
    site = file_values.get("site", {})

    config = {
        "repo": github.get("repo", defaults["repo"]),
        "branch": github.get("branch", defaults["branch"]),
        "discussions_category": github.get(
            "discussions_category", defaults["discussions_category"]
        ),
        "base_url": site.get("base_url", defaults["base_url"]),
    }
    if not config["repo"]:
        config["repo"] = defaults["repo"]
    return config


def load_discussions_map() -> dict[str, int]:
    if not DISCUSSIONS_MAP_PATH.exists():
        return {}

    mapping: dict[str, int] = {}
    current_key: str | None = None

    for raw_line in DISCUSSIONS_MAP_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        section_match = re.fullmatch(r'\["([^"]+)"\]', line)
        if section_match:
            current_key = section_match.group(1)
            continue

        discussion_match = re.fullmatch(r"discussion\s*=\s*(\d+)", line)
        if discussion_match and current_key:
            mapping[current_key] = int(discussion_match.group(1))

    return mapping


def parse_toml_like(text: str) -> dict[str, object]:
    """Parse the small subset of TOML used by wiki.toml and discussions-map.toml."""
    root: dict[str, object] = {}
    section: dict[str, object] | None = None
    section_name = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip().strip('"')
            if section_name:
                section = root.setdefault(section_name, {})
                if not isinstance(section, dict):
                    section = {}
                    root[section_name] = section
            else:
                section = None
            continue

        key, separator, value = line.partition("=")
        if not separator:
            continue

        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.isdigit():
            value = int(value)

        if key.startswith('"') and key.endswith('"'):
            table_key = key[1:-1]
            if section is None:
                root[table_key] = value
            else:
                section[table_key] = value
        elif section is None:
            root[key] = value
        else:
            section[key] = value

    return root


def write_production_pages(
    productions: list[Production],
    wiki_config: dict[str, str],
    discussions_map: dict[str, int],
) -> None:
    for production in productions:
        output_path = DOCS_ROOT / production.output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = render_production_page(production, wiki_config, discussions_map)
        output_path.write_text(content, encoding="utf-8")


def render_production_page(
    production: Production,
    wiki_config: dict[str, str],
    discussions_map: dict[str, int],
) -> str:
    body = escape_shortcut_reference_links(production.body.lstrip("\n"))
    body = transform_external_media(body)
    notice_lines = [
        f"> Metadata-only wiki page generated from `{production.source_rel}`.",
        f"> See the [content notice]({link_between(production.output_rel, Path('content-notice.md'))}) before reusing archive metadata.",
    ]

    if production.source_url:
        notice_lines.append(
            f"> Original archive source url: [{production.source_url}]({production.source_url})."
        )

    notice = "\n".join(notice_lines)
    toolbar = render_contribution_toolbar(production, wiki_config, discussions_map)
    footer = render_contribution_footer(production, wiki_config, discussions_map)

    if body.startswith("# "):
        heading, _, rest = body.partition("\n")
        body = f"{heading}\n\n{toolbar}\n\n{notice}\n\n{rest.lstrip()}"
    else:
        body = f"# {production.title}\n\n{toolbar}\n\n{notice}\n\n{body}"

    body = f"{body.rstrip()}\n\n{footer}\n"

    if production.frontmatter:
        return f"---\n{production.frontmatter}\n---\n\n{body}"

    return body


def github_repo(wiki_config: dict[str, str]) -> str:
    return wiki_config.get("repo", "").strip()


def edit_page_url(production: Production, wiki_config: dict[str, str]) -> str | None:
    repo = github_repo(wiki_config)
    if not repo:
        return None
    branch = wiki_config.get("branch", "main").strip() or "main"
    return f"https://github.com/{repo}/edit/{branch}/{production.source_rel}"


def discuss_page_url(
    production: Production,
    wiki_config: dict[str, str],
    discussions_map: dict[str, int],
) -> str | None:
    repo = github_repo(wiki_config)
    if not repo:
        return None

    discussion_number = discussions_map.get(production.source_rel)
    if discussion_number:
        return f"https://github.com/{repo}/discussions/{discussion_number}"

    title = discussion_title(production)
    params: dict[str, str] = {
        "title": title,
        "body": discussion_prefill_body(production, wiki_config),
    }
    category = wiki_config.get("discussions_category", "").strip()
    if category:
        params["category"] = category

    return f"https://github.com/{repo}/discussions/new?{urlencode(params)}"


def contribute_material_url(
    production: Production, wiki_config: dict[str, str]
) -> str | None:
    repo = github_repo(wiki_config)
    if not repo:
        return None

    title = f"Material contribution: {discussion_title(production)}"
    body = (
        f"Production: {production.title}\n"
        f"Source file: `{production.source_rel}`\n\n"
        "Describe programs, photographs, reviews, or other material you can share "
        "(prefer links or where items are held; see the content notice).\n"
    )
    return f"https://github.com/{repo}/issues/new?{urlencode({'title': title, 'body': body})}"


def discussion_title(production: Production) -> str:
    year = production.year if production.year.isdigit() else "undated"
    return f"{production.title} ({year})"


def discussion_prefill_body(production: Production, wiki_config: dict[str, str]) -> str:
    wiki_path = production.output_rel.as_posix()
    lines = [
        "### About this page",
        "",
        f"**Production:** {production.title}",
        f"**Source file:** `{production.source_rel}`",
    ]

    base_url = wiki_config.get("base_url", "").strip().rstrip("/")
    if base_url:
        lines.append(f"**Wiki page:** {base_url}/{wiki_path}")

    lines.extend(
        [
            "",
            "Use this thread for disputed dates, cast recollections, missing "
            "photographs, conflicting sources, or oral history. When evidence is "
            "clear, please open a pull request to update the catalogue record.",
            "",
            "---",
            "_Opened from the LTUST Production Wiki._",
        ]
    )
    return "\n".join(lines)


def render_contribution_toolbar(
    production: Production,
    wiki_config: dict[str, str],
    discussions_map: dict[str, int],
) -> str:
    edit_url = edit_page_url(production, wiki_config)
    discuss_url = discuss_page_url(production, wiki_config, discussions_map)
    contributing = link_between(production.output_rel, Path("contributing.md"))

    if edit_url and discuss_url:
        return (
            '<p class="wiki-contribute">'
            f'<a href="{edit_url}">Edit this page</a>'
            " · "
            f'<a href="{discuss_url}">Discuss this page</a>'
            "</p>"
        )

    return (
        '<p class="wiki-contribute">'
        f"Contribution links are not configured. See "
        f'<a href="{contributing}">Contributing</a> and set '
        "<code>github.repo</code> in <code>wiki.toml</code>."
        "</p>"
    )


def render_contribution_footer(
    production: Production,
    wiki_config: dict[str, str],
    discussions_map: dict[str, int],
) -> str:
    edit_url = edit_page_url(production, wiki_config)
    discuss_url = discuss_page_url(production, wiki_config, discussions_map)
    material_url = contribute_material_url(production, wiki_config)
    contributing = link_between(production.output_rel, Path("contributing.md"))

    if edit_url and discuss_url:
        link_parts = [
            f'<a href="{edit_url}">Edit this page</a>',
            f'<a href="{discuss_url}">Discuss this page</a>',
        ]
        if material_url:
            link_parts.append(f'<a href="{material_url}">Contribute material</a>')
        links_html = " · ".join(link_parts)
        body = (
            "<p><strong>Found an error or have additional information?</strong></p>"
            f"<p>{links_html}</p>"
        )
    else:
        body = (
            "<p><strong>Found an error or have additional information?</strong></p>"
            "<p>Configure <code>wiki.toml</code> to enable GitHub links, or read "
            f'<a href="{contributing}">Contributing</a>.</p>'
        )

    return "\n".join(["---", "", f'<div class="wiki-contribute-footer">{body}</div>', ""])


def escape_shortcut_reference_links(text: str) -> str:
    text = text.replace("[CDATA[", r"\[CDATA\[")
    return re.sub(r"\[([^\]\n]+)\](?!\(|\[)", r"\\[\1\\]", text)


def write_production_indexes(productions: list[Production]) -> None:
    by_year: dict[str, list[Production]] = defaultdict(list)

    for production in productions:
        by_year[production.year].append(production)

    lines = [
        "# Browse productions",
        "",
        "Production pages are generated from the source metadata export.",
        "",
        '<div class="wiki-summary">',
        f"<p><strong>{len(productions)}</strong><br>Total productions</p>",
        f"<p><strong>{count_years(productions)}</strong><br>Dated years</p>",
        f"<p><strong>{len(by_year.get('Undated', []))}</strong><br>Undated entries</p>",
        "</div>",
        "",
        "## Years",
        "",
        "| Year | Productions |",
        "| --- | ---: |",
    ]

    for year in sorted((year for year in by_year if year != "Undated"), key=int):
        target = Path("productions", year, "index.md")
        lines.append(
            f"| [{year}]({link_between(Path('productions/index.md'), target)}) | {len(by_year[year])} |"
        )

    if "Undated" in by_year:
        target = Path("productions", "undated", "index.md")
        lines.extend(
            [
                "",
                "## Undated",
                "",
                f"[Browse undated entries]({link_between(Path('productions/index.md'), target)}) ({len(by_year['Undated'])} productions).",
            ]
        )

    write_markdown(Path("productions/index.md"), lines)

    for year, entries in by_year.items():
        if year == "Undated":
            write_undated_index(entries)
        else:
            write_year_index(year, entries)


def write_year_index(year: str, entries: list[Production]) -> None:
    output_rel = Path("productions", year, "index.md")
    sorted_entries = sorted(entries, key=production_sort_key)
    lines = [
        f"# {year} productions",
        "",
        f"[Back to all productions]({link_between(output_rel, Path('productions/index.md'))})",
        "",
        f"{len(sorted_entries)} production entries are listed for {year}.",
        "",
        "| Month | Date | Production | Categories |",
        "| --- | --- | --- | --- |",
    ]

    for production in sorted_entries:
        month = month_label(production.month)
        date = production.date or "-"
        categories = ", ".join(production.categories) if production.categories else "-"
        lines.append(
            "| "
            f"{escape_table(month)} | "
            f"{escape_table(date)} | "
            f"[{escape_link_text(production.title)}]({link_between(output_rel, production.output_rel)}) | "
            f"{escape_table(categories)} |"
        )

    write_markdown(output_rel, lines)


def write_undated_index(entries: list[Production]) -> None:
    output_rel = Path("productions", "undated", "index.md")
    sorted_entries = sorted(entries, key=lambda item: item.title.casefold())
    lines = [
        "# Undated productions",
        "",
        f"[Back to all productions]({link_between(output_rel, Path('productions/index.md'))})",
        "",
        f"{len(sorted_entries)} production entries do not have a reliable year in the export path.",
        "",
        "| Production | Categories |",
        "| --- | --- |",
    ]

    for production in sorted_entries:
        categories = ", ".join(production.categories) if production.categories else "-"
        lines.append(
            "| "
            f"[{escape_link_text(production.title)}]({link_between(output_rel, production.output_rel)}) | "
            f"{escape_table(categories)} |"
        )

    write_markdown(output_rel, lines)


def write_category_indexes(productions: list[Production]) -> None:
    categories: dict[str, list[Production]] = defaultdict(list)

    for production in productions:
        for category in production.categories:
            categories[category].append(production)

    slug_by_category = category_slugs(categories.keys())
    index_rel = Path("categories/index.md")
    lines = [
        "# Browse categories",
        "",
        "Categories are parsed from the `## Categories` section in production pages.",
        "",
        f"{len(categories)} categories are present in the export.",
        "",
        "| Category | Productions |",
        "| --- | ---: |",
    ]

    for category in sorted(categories, key=str.casefold):
        target = Path("categories", f"{slug_by_category[category]}.md")
        lines.append(
            f"| [{escape_link_text(category)}]({link_between(index_rel, target)}) | {len(categories[category])} |"
        )

    write_markdown(index_rel, lines)

    for category in sorted(categories, key=str.casefold):
        output_rel = Path("categories", f"{slug_by_category[category]}.md")
        entries = sorted(categories[category], key=production_sort_key)
        lines = [
            f"# {category}",
            "",
            f"[Back to all categories]({link_between(output_rel, index_rel)})",
            "",
            f"{len(entries)} production entries use this category.",
            "",
            "| Year | Date | Production |",
            "| --- | --- | --- |",
        ]

        for production in entries:
            lines.append(
                "| "
                f"{escape_table(production.year)} | "
                f"{escape_table(production.date or '-')} | "
                f"[{escape_link_text(production.title)}]({link_between(output_rel, production.output_rel)}) |"
            )

        write_markdown(output_rel, lines)


def category_slugs(categories: object) -> dict[str, str]:
    used: set[str] = set()
    slugs: dict[str, str] = {}

    for category in sorted(categories, key=str.casefold):
        base = slugify(category)
        slug = base
        suffix = 2

        while slug in used:
            slug = f"{base}-{suffix}"
            suffix += 1

        used.add(slug)
        slugs[category] = slug

    return slugs


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "category"


def production_sort_key(production: Production) -> tuple[int, int, str, str]:
    return (
        sortable_year(production.year),
        sortable_month(production.month),
        production.date,
        production.title.casefold(),
    )


def sortable_year(value: str) -> int:
    return int(value) if value.isdigit() else 9999


def sortable_month(value: str) -> int:
    return int(value) if value.isdigit() else 99


def month_label(value: str) -> str:
    if not value:
        return "-"
    return MONTH_NAMES.get(value, value)


def link_between(from_rel: Path, target_rel: Path) -> str:
    from_dir = from_rel.parent.as_posix() or "."
    links_to_index = target_rel.name == "index.md"
    target = target_rel.parent if links_to_index else target_rel
    relative = posixpath.relpath(target.as_posix(), from_dir)

    if relative == ".":
        return "./"

    link = quote_path(relative)
    if links_to_index:
        link += "/"

    return link


def quote_path(path: str) -> str:
    return "/".join(quote(part, safe="-._~") for part in path.split("/"))


def escape_table(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def escape_link_text(value: str) -> str:
    return escape_table(value).replace("[", "\\[").replace("]", "\\]")


def write_markdown(output_rel: Path, lines: list[str]) -> None:
    output_path = DOCS_ROOT / output_rel
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def count_years(productions: list[Production]) -> int:
    return len({production.year for production in productions if production.year.isdigit()})


def count_categories(productions: list[Production]) -> int:
    return len(
        {
            category
            for production in productions
            for category in production.categories
        }
    )


if __name__ == "__main__":
    main()
