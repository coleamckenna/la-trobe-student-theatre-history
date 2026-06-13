# La Trobe Student Theatre History

Public, metadata-only database of La Trobe University Student Theatre production
records. A collection of information about productions at La Trobe University, from sources on the internet.

See [CONTENT-NOTICE.md](CONTENT-NOTICE.md) for copyright boundaries. Programs and
images are **not** included in this repository.

## Public site 

[La Trobe Student Theatre History](https://www.la-trobe-history.student-theatre.com)

The public catalog is **live Datasette** on a Cloudflare Python Worker:

data/catalog/*.csv → data/build.py → ltst.sqlite → datasette-worker bundle → pywrangler deploy

### Maintainer workflow

1. Edit CSV files in `data/catalog/`
2. Commit and push to `main` — CI rebuilds and redeploys.

**Canonical data in git:** `data/catalog/productions.csv`, `organisations.csv`, `people.csv`, `materials.csv`.

## URL map

### Public site (Datasette Worker)

| URL | Content |
|-----|---------|
| `/` | Homepage with production list |
| `/{slug}` | Production, person, organisation, or venue page |
| `/about` | About the project |
| `/ltst/` | Datasette table browser |
| `/ltst/ltst` | Download SQLite database |
| `/ltst/*.json` | Datasette JSON APIs |

Examples: `/the-white-rabbit-show-1975`, `/barry-ziegler`, `/org-drama-group`, `/venue-menzies`

## Licenses

| Path | License |
|------|---------|
| `catalog/*.csv` | [CC-BY-4.0](catalog/LICENSE) |
| `scripts/`, `.github/` | MIT (see LICENSE) |
| `framework/` | MIT (submodule) |

## Setup

```bash
git submodule update --init --recursive
python3 -m venv framework/.venv
framework/.venv/bin/pip install -r framework/requirements.txt
./scripts/preview.sh
```


## Maintainer workflow

1. Edit `catalog/*.csv`
2. `./scripts/preview.sh` or `./scripts/build.sh`
3. Push to `main` — CI deploys the Worker

Public site: https://la-trobe-history.student-theatre.com
