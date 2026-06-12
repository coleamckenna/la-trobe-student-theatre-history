# LTUST Production Wiki

This site turns the public La Trobe University Student Theatre (LTUST)
production database into a searchable wiki.

Use the search box to find productions by title, people, venue, notes, or other
catalogue text. You can also browse by year/month or by category once the wiki
pages have been generated from the export.

## Browse

- [Browse productions](productions/) by year, month, and undated entries.
- [Browse categories](categories/) parsed from production metadata.
- [Read the data guide](data-guide.md) for field and path conventions.
- [Read how to contribute](contributing.md) — edit records via pull requests, debate on GitHub Discussions.
- [Read the content notice](content-notice.md) before reusing archive metadata.

## What is included

The wiki contains structured catalogue metadata: production titles, dates,
venues, abstracts, cast and crew, notes, categories, and source links when those
fields are present in the export.

## What is not included

Programmes, photographs, PDFs, scans, WordPress assets, and other archival media
are not redistributed here. When a production page has a `source_url`, follow it
to the original MUST archive entry for more context.

## Rebuilding this site

The production and category wiki pages are generated from the source export:

```bash
python3 scripts/build_wiki.py
python3 -m zensical build
```

For local preview, install the docs dependency and run:

```bash
python3 -m pip install -r requirements-docs.txt
python3 scripts/build_wiki.py
python3 -m zensical serve
```
