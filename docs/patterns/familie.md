# Persons and families

**A person, the couples they were part of, and which of them is whose child. Everything else - when, where,
and how we know - is an Angabe with its Beleg (#8).** The models follow GEDCOM's INDI and FAM closely
enough that an import (#22) and an export (#26) map field to field without a translation layer.

One installation holds one tree (several are #34). The models live in `apps/stammbaum/models/`, one module
each.

## The models

| Model | Is | GEDCOM |
|---|---|---|
| `Person` | Vornamen, Familienname, Rufname, Geschlecht, Lebensstatus | `INDI` with `NAME`/`GIVN`/`SURN`, `NICK`, `SEX` |
| `Partnerschaft` | Two people as a couple: Art, Beginn, Ende. The through model of `Person.partner` | `FAM` with `HUSB`/`WIFE`, `MARR`, `DIV` |
| `ElternKind` | One parent and one child, optionally the Partnerschaft the child belongs to, and the Art | `CHIL` in a `FAM`, `PEDI` |
| `Geschwister` | Two siblings whose shared parents nobody knows | a `FAM` with children and no parents |
| `Einstellung` | The tree's settings - one row - holding the Ausgangsperson | - |

**Geschlecht** is GEDCOM's `SEX`: `M`, `F`, `X` (divers) and `U` (unbekannt, the default).

**Lebensstatus** is `lebend`, `verstorben` or `unbekannt`, and `unbekannt` is the default. GEDCOM has no
such field - "verstorben" is a death record, "lebend" its absence on someone young enough - and an import of
someone born in 1820 without a death record must not land as alive. Whether a person is alive decides what
may be shown and exported about them, so a guess is worse than "unbekannt".

**Beginn and Ende of a Partnerschaft** are text in GEDCOM DATE syntax for now: `1985`, `ABT 1931`,
`BET 1950 AND 1952`. A wedding date wants a source like any other fact, so #8 replaces both with the
structured uncertain date of [Belege](belege.md) and its Zitat.

## Children belong to a couple, or to one parent

An `ElternKind` row is one edge: a child with two known parents has two rows. Each may name the
`Partnerschaft` the child was born into, so the children of a second marriage stay with the second couple.
A child with one known parent - a father's son from before the marriage, a cousin whose mother nobody has
recorded - has a single row and no Partnerschaft.

`Art` is `leiblich` (the default), `adoptiert`, `pflege` or `unbekannt`. A child has at most two `leiblich`
parents; adoptive and foster parents come on top.

## Siblings are derived

**Two people who share a parent are siblings, and nothing stores that.** Half-siblings are siblings
through the one parent they share. A `Geschwister` row exists only for siblings whose shared parents are
unknown - "Katharina and Stefan are siblings, but we do not know their parents" - and it is refused once a
shared parent is recorded: two ways to say the same thing are two things to keep in step.

`readers.person.verwandte(person=…)` returns parents, partners, children and siblings, the siblings derived
and explicit together. Every screen that lists relatives goes through it.

## The rules, and who holds them

Every model inherits `ValidateConstraintsOnSaveMixin`, so `save()` runs `clean()` and the constraints first
and a forbidden row ends in a `ValidationError` with the German message below - see
[rules in the database](app-layout.md#rules-in-the-database).

| Rule | Constraint | Message |
|---|---|---|
| Geschlecht and Lebensstatus are one of their choices | `person_geschlecht_gueltig`, `person_lebensstatus_gueltig` | "Das Geschlecht ist männlich, weiblich, divers oder unbekannt." |
| The Art of a Partnerschaft or an ElternKind is one of its choices | `partnerschaft_art_gueltig`, `elternkind_art_gueltig` | "Eine Partnerschaft ist eine Ehe, …" |
| Nobody is their own partner, parent or sibling | `partnerschaft_nicht_selbst`, `elternkind_nicht_selbst`, `geschwister_nicht_selbst` | "Niemand ist sein eigener Partner." |
| One Partnerschaft and one Geschwister row per pair, whichever way round | `partnerschaft_einmal_pro_paar`, `geschwister_einmal_pro_paar` - unique on `Least`/`Greatest` of the two, so which of them is `person_a` means nothing | "Diese beiden sind schon ein Paar." |
| One ElternKind row per parent and child | `elternkind_einmal` | "Diese Eltern-Kind-Verbindung gibt es schon." |
| One row of Einstellung | `einstellung_nur_eine_zeile`, on `id = 1`; the admin offers no second and no delete | "Es gibt nur eine Zeile Einstellungen." |
| The Ausgangsperson cannot be deleted | `on_delete=PROTECT`; choosing another one first is #19 | - |

What spans several rows no constraint can hold, so it is in `clean()`, which the mixin runs on every save:

| Rule | In |
|---|---|
| An ElternKind's Partnerschaft contains its parent | `ElternKind.clean()` |
| At most two `leiblich` parents | `ElternKind.clean()` against the saved rows, and the admin's `ElternFormSet` for several entered at once |
| No Geschwister row for people with a shared parent | `Geschwister.clean()`, and `ElternKind.clean()` refuses the shared parent while the row is still there |

A name may be empty: GEDCOM allows a person without one, and "the unknown first wife" belongs in the tree.
`loaddata` writes past `save()`, so the Familie Huber fixture is held by the constraints alone.

## Raw GEDCOM

Every model but `Einstellung` has `gedcom_roh`, a JSON list of the records an import brought along that
Zweigerl does not understand, so an export can write them back (#22, #26). Nothing in Zweigerl reads it, and
nothing but the importer writes it.

## The Ausgangsperson

The person the tree is laid out around (#11), stored as `Einstellung.ausgangsperson` and read with
`readers.einstellung.ausgangsperson()`, which returns `None` while nobody has been chosen. #18, #19 and #20
read it there; #20 makes it changeable from the person card.

## Familie Huber

`apps/stammbaum/fixtures/familie_huber.json` is the invented family of the mockup: fifteen people over four
generations around Lena Huber, the Ausgangsperson. It holds every case above - two couples with their
children, a son with one known parent, two cousins with only their father - and it is what the browser run
of [`/implement-story`](../../.claude/skills/implement-story/SKILL.md) plays with. Tests never load it to get
data, see [test data](testing-data.md).

```bash
uv run python manage.py loaddata familie_huber
```

## See also

- [Belege](belege.md) - facts, sources and the uncertain date that replaces Beginn and Ende
- [Test data](testing-data.md) - the factories for these models
- [Where code goes](app-layout.md) - models, readers and the admin at the app root
