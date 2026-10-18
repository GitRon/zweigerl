# Test conventions

The suite runs on **pytest** + **pytest-django**. No `unittest.TestCase` anywhere — plain test functions
and plain `assert` throughout. No `setUpTestData`, no `self.assertEqual`.

`[tool.pytest.ini_options]` in `pyproject.toml` points at `apps.config.settings_test`.

## Layout

- Each app's `tests/` mirrors the structure of its production code:
  `apps/family_tree/views/start.py` → `apps/family_tree/tests/views/test_start.py`.
  The tests that check the whole tree at once rather than one testee live in
  `apps/family_tree/tests/architecture/`, see [architecture tests](architecture-tests.md).
- One test module per testee. If a module would have to hold tests for two testees, split it.
- **Always add `__init__.py`** to every `tests/` package and sub-package. Without it, two packages that
  both contain e.g. `tests/test_person.py` collide during collection and pytest fails on the duplicate
  module name.
- Fixtures shared by one app's tests go into that app's `tests/conftest.py`.
- Order tests to reflect the order of functions and methods in the code under test.
- Group with plain functions. Use a `Test…` class only when several tests genuinely share fixtures, never
  just to namespace them.

## Naming

- `test_[testee]_[case]`, e.g. `test_toast_session_keeps_every_toast_in_order`.
- Don't repeat the module name in the test name — it is already in the path.
- Avoid double underscores when testing protected functions.
- Use semantically useful names: `person_without_parents`, not `p1`.
- No type hints in variable names — avoid `person_qs`, `facts_list`.

## Design

- Tests are atomic: one case per test. Avoid one large test covering every case.
- At least one test per function and one per branch — but don't overengineer, and one test per edge case,
  not more.
- Stick to **Arrange / Act / Assert**, separated by blank lines.
- Keep tests simple and readable: no loops, no clever abstractions, no helper indirection. boa-restrictor
  flags a loop in a test (`PBR008`); `pytest.mark.parametrize` is the way to run one case over several
  inputs.
- Every test needs at least one assert. If the testee returns nothing and there is no other observable
  effect, assert `is None`.

## Assertions

- Use `pytest.raises(SomeError, match="expected message")` — never a bare `pytest.raises`, which also
  passes on the wrong error of the right type.
- Compare booleans identity-wise: `assert result is True` / `assert result is False`, not `assert result` —
  truthiness hides wrong types.
- Same for `None`: `assert result is None`.
- For templates, `pytest_django.asserts.assertTemplateUsed`.

## Imports

No local (function-level) imports in test files.
