# Zweigerl

Ein Stammbaum, in dem jede Angabe ihren Beleg hat.

A Django 6.1 app on Python 3.14 with a SQLite database. Pages are server-rendered and move with
[datastar](https://data-star.dev); components are [django-cotton](https://django-cotton.com).

## Local setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) from `pyproject.toml`. uv installs the
interpreter pinned in `.python-version` itself:

```bash
uv sync                                  # creates .venv and installs everything, dev group included
uv run python manage.py migrate
uv run python manage.py runserver
```

The stylesheet is compiled with Tailwind, installed with **yarn** (use `yarn add`, not `npm install`:
`yarn.lock` is the lock file). `static/dist/` is not in version control, so a fresh clone builds it once,
and again after a template gains a class it did not use before:

```bash
yarn install
yarn build:css                           # assets/css/tailwind.css -> static/dist/tailwind.css
yarn watch:css                           # the same, rebuilding while you work
```

The datastar bundle is vendored in `static/vendor/datastar/` and needs no install - see
[datastar](docs/patterns/datastar.md).

## Tests and linting

```bash
uv run pytest --cov                      # the suite, failing below 100 % branch coverage
uv run lint-imports                      # the import boundaries in pyproject.toml
uvx pre-commit install                   # ruff, django-upgrade, djade, boa-restrictor, complexipy on commit
uvx pre-commit run --all-files
```

CI runs all of it on every pull request (`.github/workflows/tests.yml`).

## Documentation

Each doc is normative for the area it covers. Read the relevant one before working in that area rather
than inferring the conventions from nearby code.

- [Agent guide](AGENTS.md) — what to read before touching what, and where code goes
- [datastar](docs/patterns/datastar.md) — the pinned version, signals, fragments, pages, CSRF, toasts and
  when JavaScript of our own is allowed
