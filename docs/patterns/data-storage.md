# Data storage and privacy

> **Scaffold.** This page is written by #3, which moves the data out of the repository. Until then it
> states the rule and what exists today.

**Real family data never goes into the repository.** Not the database, not a scan, not a photo, not a
name in a fixture, a test or an example. Zweigerl holds data about living relatives, and a repository is
copied, pushed and forked.

## Today

- The database is `db.sqlite3` in the project root, ignored by git (`*.sqlite3` in `.gitignore`).
- `SECRET_KEY` is a development value in `apps/config/settings.py`.
- There is no media yet.
- Test data is invented — see [test data](testing-data.md).

## What #3 decides here

- The data directory from `ZWEIGERL_DATA_DIR`, the database and `medien/` inside it, the secret key from
  the environment.
- The login every page sits behind, and `django-axes` against guessed passwords.
- Where the data directory should live and why: local only, in an encrypted area.

## Related

- How media are served only to someone logged in: #21
- How the data is backed up: #27, #33
