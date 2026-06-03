# MUST production metadata

Public, metadata-only database of La Trobe University Student Theatre production
records. Each production has a `production.md` under `productions/` organised by
**year** and **month of first performance** (or `undated/` when unknown).

See [CONTENT-NOTICE.md](CONTENT-NOTICE.md) for copyright boundaries. Programs and
images are **not** included in this repository.

## Layout

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

## Statistics

- Productions exported: 2824
- Rows skipped (no title): 0
- Slug collisions resolved: 0

## Wiki site

This repository includes a [Zensical](https://zensical.org/) wiki layer for
browsing and searching the metadata export. Generated wiki pages are written
under `docs/productions/` and `docs/categories/`, which are ignored by Git and
can be rebuilt from the source export at any time.

Install the documentation dependency, generate the wiki pages, and preview the
site locally:

```bash
python3 -m pip install -r requirements-docs.txt
python3 scripts/build_wiki.py
python3 -m zensical serve
```

Set `github.repo` in [`wiki.toml`](wiki.toml) (or rely on `GITHUB_REPOSITORY` in
Actions) so generated production pages show **Edit this page** and **Discuss this
page** links. See [docs/contributing.md](docs/contributing.md).

Build the static site into `site/`:

```bash
python3 scripts/build_wiki.py
python3 -m zensical build
```

