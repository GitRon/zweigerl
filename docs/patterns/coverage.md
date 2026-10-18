# Coverage

The gate is **100% branch coverage**, configured as `branch = true` and `fail_under = 100` in
`pyproject.toml`. Run it with `uv run pytest --cov`; CI fails below it.

Statement coverage alone is not enough: it counts an `if` as covered once the body has run, so a missing
`else` and an unexercised loop exit both pass unnoticed. Branch coverage is what makes "one test per
branch" verifiable instead of aspirational.

**The suite meets the gate. Keep it there.**

- Don't lower `fail_under` to turn a red run green.
- Don't reach for `# pragma: no cover`. A line that cannot be reached is dead code — delete it instead.
- An abstract method's body should `raise NotImplementedError`, which is excluded by configuration, rather
  than `pass`, which is not.
- **A branch behind the clock is a coverage bug, not an exception.** It makes the gate pass or fail by the
  time of day. Patch the clock, see [mocking](mocking.md).

## Scope

Measured: everything under `apps/` and `scripts/` — actions, readers, views, models, pure functions,
template tags, the linting rules.

Views **are** measured. They are thin enough that the one-test-per-view rule reaches 100% on its own, so
there is no reason to exempt them.

Excluded from measurement, and why:

| Excluded | Why |
|---|---|
| `*/migrations/*` | Generated |
| `*/tests/*` | The tests themselves |
| `apps/config/*` | Settings, wsgi/asgi |
| `*/admin.py`, `*/apps.py` | Framework declarations |
