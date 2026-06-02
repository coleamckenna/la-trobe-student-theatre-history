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
