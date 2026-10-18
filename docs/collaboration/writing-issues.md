# Writing an issue

An issue here is not a reminder to yourself — it is the input to
[`/implement-story`](../../.claude/skills/implement-story/SKILL.md). Phase 0 of that skill copies the
title, body and comments into its spec **once** and never fetches the issue again. Whatever is
not in the body or a comment does not exist for the implementation.

So an issue has to survive being read exactly once, by someone with no memory of the conversation that
produced it. Two things are therefore not optional: the labels, and the review pass in step 3.

**There is no backlog file.** Every idea becomes an issue straight away, as `v2` if it is not worth
planning around yet. A list of ideas somewhere else is a second place nobody looks.

Issues are written in **German**, like the interface. The docs they point at are English.

## 1. Label it

Every issue carries labels on two axes. Both are required.

### Scope — exactly one of `mvp`, `v1`, `v2`

This is the only thing that answers "what do we do next", so an issue without a scope label is invisible
when planning.

- **`mvp`** — without it Zweigerl cannot replace PAF: the family cannot be entered, read, sourced, imported
  or backed up, or something is unsafe.
- **`v1`** — wanted for the first version that is pleasant to use every day. Depth, polish and
  readability; the app works without it, it is just plainer.
- **`v2`** — worth keeping, not worth planning around yet.

When in doubt between `mvp` and `v1`, ask whether the person using it would call the current state
*broken* or merely *plain*. Broken is `mvp`.

**An `mvp` issue never depends on a `v1` or `v2` issue.** If it does, either the dependency moves up or
the `mvp` issue drops the part that needs it.

### Type — at least one of `bug`, `enhancement`, `documentation`, `question`

- **`bug`** — the code does something Zweigerl does not mean, and the issue can name where.
- **`enhancement`** — new behaviour, or behaviour Zweigerl means but does not have.
- **`documentation`** — a doc [indexed in the README](../../README.md) is wrong, missing or has drifted
  from the code.
- **`question`** — a decision has to be made before the work can be specified. A `question` issue is
  finished when the decision is written down — as a comment on the issue that implements it, so that
  `/implement-story` reads it there — not when code changes. #5 is the pattern: it closed with a comment on
  #8.

`bug` + `question` together is legitimate: the behaviour is wrong *and* the right behaviour is open.

## 2. Write the body

Ground every claim. Once the code exists, a claim about it carries a `path/to/file.py:line`; a claim
without one is an opinion, and the next reader has no way to check it. Where there is no code yet, the
claim points at the [mockup](https://claude.ai/artifact/CAPCWJfqucCVNkd5U1gEpj), the
[moodboard](https://claude.ai/artifact/PGFYeKNXchtfE5Z5Hs6zjS) or a doc.

```markdown
<!-- Feature: open with the story. Bug: open with the wrong behaviour. -->
**Als** Familienforscher **möchte ich** …, **damit** …

<!-- What the code does today, with references. -->
`create_person` legt … an (`apps/family_tree/actions/person.py:23`), aber …

**Warum es zählt:** <!-- What it costs. Consequences, not adjectives. -->

**Richtung**
<!-- Where the fix should go. Options with their trade-offs, one bullet each.
     "Vorschlag: …" when you have an opinion. -->

**Offene Frage:** <!-- The decision this issue still needs, if any. -->

**Nicht Teil davon:** <!-- What this issue does not own, and which issue does. -->

**Hängt ab von:** <!-- Issues that must land first, with the reason the order matters. -->

---
**Story Points:** <!-- 1, 2, 3 or 5. More than 5 means the issue is two issues. -->
```

Rules that matter more than the skeleton:

- **The title is a sentence about what a person sees, not about the code.** *"Die Personenliste lässt
  sich durchsuchen"*, not *"Add search to person list view"*. No `Feat:`/`Bug:` prefix — the type label
  already says that.
- **Direction, not design.** Say where the work belongs and what the open question is. An issue may name
  a pattern doc to follow; it should not decide what that doc decides.
- **Name the open question explicitly.** If the issue has one and does not say so, it will be answered by
  accident during implementation. When it is decided, add `**Entschieden am <Datum>:** …` under it rather
  than deleting the question.
- **For a bug, list the branches that need covering.** The suite runs behind a
  [100% branch gate](../patterns/coverage.md), so the cases are part of the story.
- **No real family data in an issue.** Examples use the invented Familie Huber — see
  [data storage](../patterns/data-storage.md).
- Drop a section rather than filling it with nothing.

## 3. Review the draft against the code and the other issues

**This is the step that must not be skipped.** Hand the draft to Claude before it is created, and have it
checked against two things in this order. Expect it to come back with the issue changed — if a draft
survives this untouched, the pass was too shallow.

### Against the codebase

Read [AGENTS.md](../../AGENTS.md) and the docs it points at for the area first.

- Does the described behaviour actually happen? Find the code that produces it and cite `file.py:line`.
  If it cannot be found, the premise is wrong and the issue should not be created.
- Is it already there, or half there? Partly-implemented changes the issue from "build this" to "finish
  this".
- Does the direction fit the patterns — [where code goes](../patterns/app-layout.md) for actions and
  readers, [Belege](../patterns/evidence.md), [data storage](../patterns/data-storage.md),
  [datastar](../patterns/datastar.md), [testing strategy](../patterns/testing-strategy.md)?
- What does it touch, and which existing tests will move? What breaks if it lands?

### Against the other issues

List all issues, open and closed, and read the bodies of everything adjacent — closed ones included,
because a closed issue is where a decision was made.

- **Duplicate** — comment on the existing issue instead of opening a second one.
- **Overlap** — two issues touching the same code. Split the ownership in writing:
  *"Nicht Teil davon: das Hervorheben im Baum — gehört zu #12."*
- **Dependency** — say so and say why: *"#5 legt das Datumsfeld fest, deshalb kann #8 vorher nicht
  beginnen."*
- **Contradiction** — the draft undoes a decision another issue made. That conflict is the issue.
- **Order** — a dependency on an issue with a later scope (`mvp` on `v1` or `v2`) is a finding, see
  step 1.

### The prompt

```
Review this draft issue for Zweigerl before I create it.

1. Read AGENTS.md and the docs it points at for the area this touches.
2. Verify every factual claim against the code, or against the mockup and the docs where there
   is no code yet. Give me file:line for each one, and say plainly which claims you could not
   confirm.
3. Tell me whether this is already implemented, partly implemented, or rests on a wrong premise.
4. Check it against all open and closed issues. Report duplicates, overlaps, dependencies,
   contradictions and mvp-on-v1 dependencies by number.
5. Check the direction against the project's patterns and say where it conflicts.
6. Propose the scope label (mvp/v1/v2), the type labels and the story points, with a reason.
7. Rewrite the issue with the corrections, keeping the German sections: Richtung, Offene Frage,
   Nicht Teil davon, Hängt ab von.

<paste the draft here>
```

## 4. Create it

Then read it back on GitHub — long tables and hard-wrapped bullets do not always render the way they
looked in the editor.

## Checklist

- [ ] Exactly one scope label: `mvp`, `v1` or `v2`
- [ ] At least one type label
- [ ] Title reads as a sentence about what a person sees
- [ ] Every factual claim is grounded: `file.py:line`, the mockup or a doc
- [ ] Reviewed against the codebase — premise confirmed, existing implementation checked
- [ ] Reviewed against all open and closed issues — duplicates, overlaps, dependencies named by number
- [ ] No `mvp` issue depends on a `v1` or `v2` issue
- [ ] The open question is stated, or there is none
- [ ] *Nicht Teil davon* says which issue owns what was left out
- [ ] Story points: 5 or fewer
- [ ] For a bug: the branches that need covering are listed

## See also

- [Commit messages](../contributing/commit-messages.md) — a different, much shorter, set of rules
