# Agent guide

Zweigerl is a Django app for a family tree in which every fact carries its source.

**[README.md](README.md) indexes every doc.** It is the map — there is deliberately no second list here to
drift out of step with it.

The docs are normative for the areas they cover, not background reading. Read the relevant one *before*
touching that area, and do not infer the conventions from whatever code happens to be nearby.

Seven where getting it wrong is both expensive and silent:

| Before you… | Read |
|---|---|
| add a model, a constraint, an action, a reader, a view, a template tag, a fixture or a management command | [Where code goes](docs/patterns/app-layout.md) |
| write or change any test, factory or fixture | [Testing strategy](docs/patterns/testing-strategy.md) |
| put a name, a date, a document or a photo anywhere in the repository | [Data storage and privacy](docs/patterns/data-storage.md) |
| touch a fact, a source, a citation or a date | [Belege](docs/patterns/belege.md) |
| add or change anything datastar does: signals, fragments, toasts, a page answering both ways | [datastar](docs/patterns/datastar.md) |
| add or reuse a template piece | [Template components](docs/patterns/components.md) |
| write a colour, a typeface or a width into any template | [Visual identity](docs/patterns/visual-identity.md) and [Responsive layout](docs/patterns/responsive-layout.md) |

**Real family data never goes into the repository** — not in fixtures, not in tests, not in an example,
not in an issue. Test data is invented.

## Working on a story

**A story is implemented with [`/implement-story`](.claude/skills/implement-story/SKILL.md)**, from issue to
open PR: plan, implement, the local CI gates, a code review whose findings are fixed before the PR opens,
and a browser run of the story. The review is part of every story, not an extra.
[`/clean-worktrees`](.claude/skills/clean-worktrees/SKILL.md) removes the worktrees of merged PRs.

**A design skill reviews; it does not choose the look.** `.claude/skills/impeccable` (vendored, see its
`VENDORED.md`) is for evaluating and hardening a screen: `critique`, `audit`, `harden`, `clarify`,
`adapt`, `polish`, `distill`, `quieter`. Its commands that add colour, weight or motion (`bolder`,
`colorize`, `delight`, `animate`, `overdrive`) and its new-work flow do not apply here. Wherever the
skill's defaults and [Visual identity](docs/patterns/visual-identity.md) disagree, the doc wins, and a
finding that argues with the doc is a question for an issue, not an edit.
