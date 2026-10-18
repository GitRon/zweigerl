# Review lenses and the shard prompt

Four lenses, ranked. A small diff uses the first N; a deadline cuts from the bottom. The ranking is by how
expensive the class of bug is to find later, not by how often it fires.

| # | File | Lens | Normative docs the shard must read first |
|---|---|---|---|
| 01 | `01-correctness.md` | Correctness, actions, readers and datastar wiring | [app-layout](../../../../docs/patterns/app-layout.md), [datastar](../../../../docs/patterns/datastar.md), [components](../../../../docs/patterns/components.md) |
| 02 | `02-data-layer.md` | Data layer, Belege, privacy and migrations | [belege](../../../../docs/patterns/evidence.md), [data-storage](../../../../docs/patterns/data-storage.md), [app-layout](../../../../docs/patterns/app-layout.md) |
| 03 | `03-tests.md` | Test honesty and coverage substance | [testing-strategy](../../../../docs/patterns/testing-strategy.md), [testing-conventions](../../../../docs/patterns/testing-conventions.md), [testing-data](../../../../docs/patterns/testing-data.md), [mocking](../../../../docs/patterns/mocking.md), [coverage](../../../../docs/patterns/coverage.md) |
| 04 | `04-conformance.md` | Spec conformance and simplification | `spec.md`, [app-layout](../../../../docs/patterns/app-layout.md), [visual-identity](../../../../docs/patterns/visual-identity.md), [responsive-layout](../../../../docs/patterns/responsive-layout.md) |

### What each lens is looking for

**01 Correctness, actions, readers and datastar wiring.** Logic that is wrong for inputs the story will
actually produce. A view that builds a query or writes a row itself instead of calling a reader or an
action. An action that reads through a reader, or a reader that writes. A datastar fragment patched into
an element whose `id` the page does not carry, so the morph lands nowhere. A signal read on the server that
the template never declares, or declared under another name. A `@post` without the CSRF token. A page
datastar navigates to that does not answer both ways through `render_page`. A toast written with
`toast_session` that no redirect follows. Off-by-one and inverted conditions in the rules the story
changed - which relationship name, which reliability, which date sorts first.

**02 Data layer, Belege, privacy and migrations.** An Angabe that can end up claiming *belegt* without a
source and not showing as *unbelegt*, or *unbelegt* stored instead of derived. An uncertain date stored
other than the way [Belege](../../../../docs/patterns/evidence.md) decides. A real person's name, date,
place, document or photo in a fixture, a test or an example - the one finding that is never a nitpick. A
file served without the login check, or an upload that keeps its GPS data. Queries in loops; missing
`select_related`/`prefetch_related` on a path the story made hot, which in a family tree is every walk
over parents and children. A migration that will not apply on an existing database, or model changes with
no migration at all. A delete that cascades further than the person asked for. A rule the data must always
satisfy that is checked only in an action or a form although a constraint could hold it, a model with
constraints that does not inherit `ValidateConstraintsOnSaveMixin`, or uniqueness written as `unique=True`
or `unique_together` - see
[rules in the database](../../../../docs/patterns/app-layout.md#rules-in-the-database).

**03 Test honesty and coverage substance.** Coverage that is reached without asserting anything.
First-party code mocked - the docs call that a review finding outright. Branches covered by patching the
thing under test rather than exercising it. A branch behind the unpatched clock, which makes the gate pass
by the time of day. A reader test without a row that must not come back. A view test asserting on a
page's markup. Tests that would still pass if the story's change were reverted.

**04 Spec conformance and simplification.** Requirements in `spec.md` that the diff does not actually
satisfy, and behaviour in the diff that nothing in `spec.md` asked for. Something `spec.md` puts under
"Nicht Teil davon" built anyway. Code duplicated from somewhere it could have been reused. Abstraction
introduced for one caller. Dead branches left behind by the change. A colour, typeface or width that the
visual identity or the responsive layout rules out. A German identifier, path, URL, choice value or
signal, or English text a person reads - see
[locale and language](../../../../docs/contributing/settings.md#locale-and-language).

## Shard prompt template

Fill the placeholders and pass this as the `Agent` prompt. Keep the wording - the incremental-write rule
and the verify stage are what make a dying shard cheap and a surviving shard trustworthy.

---

You are reviewing one lens of a code change in the Zweigerl repository at `<REPO_ROOT>`.

**Your deliverable is the file `<RUN_DIR>/review/<SHARD_FILE>`, not your reply.** Nothing you return in
chat is read. Write findings into that file as you confirm them, one at a time, appending - never buffer
them to the end. If you are killed halfway through, everything already written still counts, and that is
the point.

The change under review is `git diff <BASE>...HEAD`<SCOPE_NOTE>. Review only that diff. Problems on lines
this change did not touch are out of scope.

**Your lens: <LENS_NAME>.** <LENS_DESCRIPTION>

Read these before you review - they are normative for this project: <LENS_DOCS>. Also read
`<RUN_DIR>/spec.md` for what the change was supposed to do.

Work in two stages, per finding:

1. **Find.** Scan the diff through your lens and note candidates.
2. **Verify.** For each candidate, go back to the actual code and try to *refute* it. Read the
   surrounding function, the callers, the tests. Then score your confidence 0-100 that it is a real defect
   a reviewer should raise: 100 you confirmed it end to end, 80 you verified it and it will bite in
   practice, 50 real but a nitpick, 25 you could not verify it, 0 refuted. **Write it to the file only if
   it scores 80 or higher.** Default to refuting when you are unsure - a false positive costs the
   maintainer more time than a missed nitpick.

Do not report: anything `ruff`, `boa-restrictor` or the 100% branch coverage gate already catches (they
run before you and are green); formatting and import order; pre-existing problems; style a senior
engineer would not raise in review; changes that are obviously intentional parts of the story.

Append each surviving finding in exactly this format:

```finding
file: apps/family_tree/actions/person.py
line: 42
severity: high | medium | low
category: <short-kebab-slug>
claim: One sentence stating the defect.
scenario: Concrete inputs or state, then the wrong output or crash that follows.
confidence: 85
```

When you have finished the whole lens, append this line and nothing after it:

`<!-- shard-complete -->`

If you find nothing, still append the sentinel - a complete file with no findings is a real result and
stops the orchestrator from retrying you.

---

## Retry variant

On the single permitted retry, keep the prompt identical but replace `<SCOPE_NOTE>` with:

> , narrowed for this retry to these files only: `<FILE_LIST>` (the largest by changed lines; the rest of
> the diff is out of scope for you).

and note in the merged `findings.md` that the lens ran at reduced scope.
