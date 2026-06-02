#!/usr/bin/env python3
"""Generate Zensical wiki pages from exported production metadata."""

from __future__ import annotations

import posixpath
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[1]
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

    productions = read_productions()
    reset_generated_dirs()
    write_production_pages(productions)
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


def write_production_pages(productions: list[Production]) -> None:
    for production in productions:
        output_path = DOCS_ROOT / production.output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = render_production_page(production)
        output_path.write_text(content, encoding="utf-8")


def render_production_page(production: Production) -> str:
    body = escape_shortcut_reference_links(production.body.lstrip("\n"))
    notice_lines = [
        f"> Metadata-only wiki page generated from `{production.source_rel}`.",
        f"> See the [content notice]({link_between(production.output_rel, Path('content-notice.md'))}) before reusing archive metadata.",
    ]

    if production.source_url:
        notice_lines.append(
            f"> Original archive source url: [{production.source_url}]({production.source_url})."
        )

    notice = "\n".join(notice_lines)

    if body.startswith("# "):
        heading, _, rest = body.partition("\n")
        body = f"{heading}\n\n{notice}\n\n{rest.lstrip()}"
    else:
        body = f"# {production.title}\n\n{notice}\n\n{body}"

    if production.frontmatter:
        return f"---\n{production.frontmatter}\n---\n\n{body.rstrip()}\n"

    return f"{body.rstrip()}\n"


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
