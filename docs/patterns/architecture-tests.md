# Architecture tests

An architecture test checks the whole tree at once rather than one testee. It holds a rule that is
otherwise silent when broken: the code keeps working, just wrongly, and no unit test of a single function
can see it. They live in `apps/stammbaum/tests/architecture/`.

An allowlist in one of them is part of the rule, not a way around it: every entry carries its reason.

**There are none yet.** The rules that need one so far are held by other tools:

| Rule | Held by |
|---|---|
| Views call actions and readers, never the other way round | import-linter, see [linting](../contributing/linting.md#import-boundaries) |
| `apps.common` does not import the domain | import-linter |
| A template variable that does not resolve fails | `FAIL_INVALID_TEMPLATE_VARS`, see [testing strategy](testing-strategy.md#views) |

## When to write one

When a rule is about every file of a kind — every view, every component, every action — and breaking it
in one place would go unnoticed. Two that are likely to come:

- **Every component renders with every parameter**, once enough components exist that a test per
  component stops being checked by hand — see [template components](components.md#tests).
- **No real data in the repository**: no fixture or test names a person who is not invented — see
  [data storage](data-storage.md).

A new architecture test replaces the "There are none yet" above with a table of its own: the module, the
rule it holds, and the doc that states the rule.
