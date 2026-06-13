# Data guide

Each production record starts as a Markdown file under `productions/`.

```text
productions/
  YYYY/
    MM/              # 00 = year known, month unknown
      <slug>/
        production.md
  undated/
    <slug>/
      production.md
```

The wiki generator creates one page for each `production.md` file and keeps the
same archive path beneath `docs/productions/`.

## Common fields

Production files generally include YAML frontmatter and Markdown sections.
Completeness varies across the historical archive.

Common frontmatter fields:

- `title`: production title used as the page title.
- `year`: production year when known.
- `month`: production month when known.
- `date`: Production date.
- `source_url`: original web source


Common body sections:

- Date
- Year
- Author
- Produced By
- Venue
- Abstract
- Director
- Designer
- Cast
- Crew
- Notes
- Categories
- Materials
- Location
- Media (optional — photos, videos, programmes linked by URL)

## External media embeds

List stable URLs in **Materials**, **Notes**, or **Media** (plain URL, `Label: URL`, or
`[label](url)`). When the wiki is built, known hosts are turned into inline embeds on
the generated page; the files stay on the original site (Wayback, Internet Archive,
YouTube, and so on).

Supported in v1:

- Archived images and PDFs on `web.archive.org`
- Internet Archive `archive.org/details/...` items
- YouTube and Vimeo
- Direct image URLs (`.jpg`, `.png`, `.gif`, `.webp`, …)
- PDFs on other hosts (iframe where allowed)
- `images.humanitix.com` (event graphics)

Link only (no iframe): public `events.humanitix.com` pages, Facebook, Instagram,
Issuu, and other hosts that block embedding. For Humanitix checkout on your site, paste
the official **embed widget** `src` from the Humanitix dashboard into **Media** — not
the public event listing URL.

Prefer Wayback permalinks for longevity. Broken upstream URLs may show empty embeds.

## Generated indexes

`scripts/build_wiki.py` builds:

- `docs/productions/index.md`
- `docs/productions/<year>/index.md`
- `docs/productions/undated/index.md`
- `docs/productions/<year>/<month>/<slug>/index.md`
- `docs/categories/index.md`
- `docs/categories/<category>.md`

Generated pages are ignored by Git so the wiki can be rebuilt from the latest
export without editing thousands of derived files.

## Source boundaries

The generated wiki is a presentation layer over catalogue metadata. Do not add
manual edits inside generated production or category pages; edit the source
export or the generator instead.

## Contributing corrections

Each generated production page includes **Edit this page** (pull request on the
source `production.md`) and **Discuss this page** (GitHub Discussions). See
[Contributing](contributing.md) for the full workflow, `wiki.toml` configuration,
and optional `discussions-map.toml` for pinned discussion threads.
