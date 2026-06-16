# La Trobe Student Theatre History

Public, metadata-only database of La Trobe University Student Theatre production
records. A collection of information about productions at La Trobe University, from sources on the internet.

See [CONTENT-NOTICE.md](CONTENT-NOTICE.md) for copyright boundaries. Programs and
images are **not** included in this repository.

## Public site

[La Trobe Student Theatre History](https://la-trobe-history.student-theatre.com)

The public catalog is **live Datasette** on a Raspberry Pi, exposed via **Cloudflare Tunnel**:

```text
ltst.sqlite (Fossil) → Pi fossil-sync → Datasette → cloudflared → Internet
```

Weekly CSV snapshots in `catalog/` are exported from Fossil by GitHub Actions for open-data publishing.

See [docs/DATA_WORKFLOW.md](docs/DATA_WORKFLOW.md) for the full data and deploy model.

## URL map


| URL            | Content                                         |
| -------------- | ----------------------------------------------- |
| `/`            | Homepage with production list                   |
| `/{slug}`      | Production, person, organisation, or venue page |
| `/about`       | About the project                               |
| `/ltst/`       | Datasette table browser                         |
| `/ltst/ltst`   | Download SQLite database                        |
| `/ltst/*.json` | Datasette JSON APIs                             |


Examples: `/the-white-rabbit-show-1975`, `/barry-ziegler`, `/org-drama-group`, `/venue-menzies`

## Licenses


| Path                   | License                      |
| ---------------------- | ---------------------------- |
| `catalog/*.csv`        | [CC-BY-4.0](catalog/LICENSE) |
| `scripts/`, `.github/` | MIT (see LICENSE)            |
| `framework/`           | MIT (submodule)              |


## Setup (local preview)

```bash
git submodule update --init --recursive
python3 -m venv framework/.venv
framework/.venv/bin/pip install -r framework/requirements.txt
framework/.venv/bin/pip install datasette jinja2 markupsafe
./scripts/build.sh
./scripts/serve.sh
```

## Maintainer workflow

1. Edit canonical `ltst.sqlite` via your editor app (or maintainer tool), then `fossil commit` / `fossil push`
2. Pi pulls Fossil on a schedule (`scripts/fossil-sync.sh` via cron) and restarts Datasette
3. GitHub Actions exports weekly CSV snapshots to `catalog/` and verifies export/build round-trip

Recovery from CSV: `./scripts/export.sh` → edit → `./scripts/build.sh` → commit to Fossil.

Public site: [https://la-trobe-history.student-theatre.com](https://la-trobe-history.student-theatre.com)
