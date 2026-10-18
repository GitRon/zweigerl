# Local setup

Zweigerl is a Django 6.1 application on Python 3.14 with a SQLite database.

Dependencies are managed with [uv](https://docs.astral.sh/uv/) from `pyproject.toml`. uv installs the
interpreter pinned in `.python-version` itself, so a matching Python does not have to be on the system
beforehand:

```bash
uv sync                                  # creates .venv and installs everything, dev group included
```

## The data directory and the key

The family data does not live in the project: the database and the media go into a directory outside the
repository, and Zweigerl refuses to start without one - see [data storage](../patterns/data-storage.md).
Create the directory in an encrypted area, then name it and a secret key in `.env`, which git ignores:

```bash
mkdir -p /path/to/encrypted/zweigerl-daten
cp .env.example .env                     # set ZWEIGERL_DATA_DIR and DJANGO_SECRET_KEY
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

A variable set in the shell wins over `.env`. The suite and the browser run of `/implement-story` need
neither: their settings bring their own.

## Running the app

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser  # every page is behind the login
uv run python manage.py runserver        # binds 127.0.0.1 - keep it that way
```

## Frontend assets

The stylesheet is compiled with Tailwind, which comes from the npm registry and is managed with **yarn**,
whose `yarn.lock` is the lock file CI installs from. Use `yarn add` rather than `npm install`: npm writes
a `package-lock.json` of its own, which nothing here reads and which goes stale without anybody noticing.

```bash
yarn install
yarn build:css                           # compiles assets/css/tailwind.css -> static/dist/tailwind.css
```

The typefaces come from the same place: fontsource packages in `package.json`. `yarn build:css` copies
their font files to `static/dist/files/` before it compiles, see [visual identity](../patterns/visual-identity.md#the-typefaces).

`static/dist/` is not in version control, so a fresh clone has to compile it once. **Without it the app
renders with no styles at all**, which looks like a broken page but is a missing build step.

Tailwind emits only the utilities it finds in the templates and Python under `apps/`, so **the
stylesheet has to be rebuilt after a template gains a class it did not use before** — otherwise the class
resolves to nothing and the page silently loses that bit of layout. During development, leave the
watcher running instead:

```bash
yarn watch:css
```

The datastar bundle is not installed by either tool: it is vendored in `static/vendor/datastar/`, see
[datastar](../patterns/datastar.md#the-version).

## Running the tests

```bash
uv run pytest           # the suite
uv run pytest --cov     # with the coverage gate
```

See [testing strategy](../patterns/testing-strategy.md) before writing any test, and
[coverage](../patterns/coverage.md) for what the gate covers.

## Dependencies

`uv.lock` is committed and is the single source of truth for what gets installed:

```bash
uv add <package>              # runtime dependency
uv add --dev <package>        # development dependency
uv lock --upgrade             # refresh the lock within the declared constraints
```

`uv sync` re-reads the lock and matches the virtualenv to it exactly, removing anything that no longer
belongs. CI runs `uv sync --locked`, which fails on a lock file that has drifted from `pyproject.toml`
rather than re-resolving silently.

## CI

`.github/workflows/tests.yml` runs three jobs on every pull request and on `main`:

| Job | Runs |
|---|---|
| `pytest` | the suite behind the coverage gate, then `lint-imports` |
| `assets` | `yarn build:css`, the only thing that notices a stylesheet build that stopped working |
| `pre-commit` | every hook over every file, see [linting](linting.md) |
