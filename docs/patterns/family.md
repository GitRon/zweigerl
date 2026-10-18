# Persons and families

**A person, the couples they were part of, and which of them is whose child. Everything else - when, where,
and how we know - is an Angabe with its Beleg (#8).** The models follow GEDCOM's INDI and FAM closely
enough that an import (#22) and an export (#26) map field to field without a translation layer.

One installation holds one tree (several are #34). The models live in `apps/family_tree/models/`, one module
each.

## The models

| Model | Is | GEDCOM |
|---|---|---|
| `Person` | `given_names`, `surname`, `call_name` (Rufname), `sex`, `living_status` | `INDI` with `NAME`/`GIVN`/`SURN`, `NICK`, `SEX` |
| `Partnership` | Two people as a couple, with its `kind`. The through model of `Person.partners`. When they married or divorced are [facts](evidence.md) on it | `FAM` with `HUSB`/`WIFE`; `MARR`, `DIV` |
| `ParentChild` | One parent and one child, optionally the `partnership` the child belongs to, and the `pedigree` | `CHIL` in a `FAM`, `PEDI` |
| `SiblingPair` | Two siblings whose shared parents nobody knows | a `FAM` with children and no parents |
| `TreeSettings` | The tree's settings - one row - holding the `home_person` (Ausgangsperson) | - |

The names are English like all code, close to GEDCOM where it has a word; what a person reads - the
`verbose_name`s, the choice labels, the messages - is German.

**`sex`** is GEDCOM's `SEX`: `M`, `F`, `X` (divers) and `U` (unbekannt, the default).

**`living_status`** is `living`, `deceased` or `unknown`, and `unknown` is the default. GEDCOM has no
such field - "deceased" is a death record, "living" its absence on someone young enough - and an import of
someone born in 1820 without a death record must not land as alive. Whether a person is alive decides what
may be shown and exported about them, so a guess is worse than "unknown".

**When a couple married or divorced** is not a field of the Partnership but a `Fact` on it, of kind
`marriage` or `divorce`, with the uncertain date and the citations every fact has - see
[Belege](evidence.md). Until #8 the Partnership held it as text in `start` and `end`; migration `0003`
turned that into facts.

## Children belong to a couple, or to one parent

A `ParentChild` row is one edge: a child with two known parents has two rows. Each may name the
`Partnership` the child was born into, so the children of a second marriage stay with the second couple.
A child with one known parent - a father's son from before the marriage, a cousin whose mother nobody has
recorded - has a single row and no Partnership.

`pedigree` is `birth` (the default), `adopted`, `foster` or `unknown`. A child has at most two `birth`
parents; adoptive and foster parents come on top.

## Siblings are derived

**Two people who share a parent are siblings, and nothing stores that.** Half-siblings are siblings
through the one parent they share. A `SiblingPair` row exists only for siblings whose shared parents are
unknown - "Katharina and Stefan are siblings, but we do not know their parents" - and it is refused once a
shared parent is recorded: two ways to say the same thing are two things to keep in step.

`readers.person.relatives(person=…)` returns parents, partners, children and siblings, the siblings derived
and explicit together. Every screen that lists relatives goes through it.

## The rules, and who holds them

Every model inherits `ValidateConstraintsOnSaveMixin`, so `save()` runs `clean()` and the constraints first
and a forbidden row ends in a `ValidationError` with the German message below - see
[rules in the database](app-layout.md#rules-in-the-database).

| Rule | Constraint | Message |
|---|---|---|
| `sex` and `living_status` are one of their choices | `person_sex_valid`, `person_living_status_valid` | "Das Geschlecht ist männlich, weiblich, divers oder unbekannt." |
| The `kind` of a Partnership and the `pedigree` of a ParentChild are one of their choices | `partnership_kind_valid`, `parentchild_pedigree_valid` | "Eine Partnerschaft ist eine Ehe, …" |
| Nobody is their own partner, parent or sibling | `partnership_not_self`, `parentchild_not_self`, `siblingpair_not_self` | "Niemand ist sein eigener Partner." |
| One Partnership and one SiblingPair row per pair, whichever way round | `partnership_once_per_pair`, `siblingpair_once_per_pair` - unique on `Least`/`Greatest` of the two, so which of them is `person_a` means nothing | "Diese beiden sind schon ein Paar." |
| One ParentChild row per parent and child | `parentchild_once` | "Diese Eltern-Kind-Verbindung gibt es schon." |
| One row of TreeSettings | `treesettings_single_row`, on `id = 1`; the admin offers no second and no delete | "Es gibt nur eine Zeile Einstellungen." |
| The home person cannot be deleted | `on_delete=PROTECT`; choosing another one first is #19 | - |

What spans several rows no constraint can hold, so it is in `clean()`, which the mixin runs on every save:

| Rule | In |
|---|---|
| A ParentChild's Partnership contains its parent | `ParentChild.clean()` |
| At most two `birth` parents | `ParentChild.clean()` against the saved rows, and the admin's `ParentsFormSet` for several entered at once |
| No SiblingPair row for people with a shared parent | `SiblingPair.clean()`, and `ParentChild.clean()` refuses the shared parent while the row is still there |

A name may be empty: GEDCOM allows a person without one, and "the unknown first wife" belongs in the tree.
`loaddata` writes past `save()`, so the Familie Huber fixture is held by the constraints alone.

## Raw GEDCOM

Every model but `TreeSettings` has `gedcom_raw`, a JSON list of the records an import brought along that
Zweigerl does not understand, so an export can write them back (#22, #26). Nothing in Zweigerl reads it, and
nothing but the importer writes it.

## The home person

The Ausgangsperson - the person the tree is laid out around (#11) - is stored as
`TreeSettings.home_person` and read with `readers.tree_settings.home_person()`, which returns `None` while
nobody has been chosen; #18 and #19 read it there. It is chosen on the settings page, `/settings/` (#20), and
saved by `actions.tree_settings.choose_home_person`; the tree and the relationship names follow it on the next
page they render. Until one is chosen, the tree is laid out around the person entered first, see
[tree layout](tree-layout.md).

## How someone is related to the home person

`domain.relationship.relationship_name(family=…, home_id=…, person_id=…)` names, in German and by the person's
`sex`, what someone is to the home person: "Urgroßvater", "Großnichte", "Schwägerin", "Cousine 2. Grades". It is
a pure function over a `FamilyGraph`, which `readers.relationship.family_graph()` loads from the whole tree in
four queries - so a list names every row from one load (#9).

- **Blood first**, through the nearest common ancestor: the generations up from the home person and from the
  other person decide the word. Every parent link counts, whatever its `pedigree`, and half-siblings are
  siblings. A group of explicit siblings shares one unknown parent, so their children are cousins too.
- **Then the partner**: Ehemann and Ehefrau for a `marriage`, Partner and Partnerin otherwise.
- **Then by marriage**: the partner of a child, parent or sibling (Schwiegersohn, Stiefvater, Schwager), the
  parent, child or sibling of a partner (Schwiegermutter, Stieftochter, Schwägerin). Uncles, aunts, nephews and
  nieces by marriage keep the blood word.
- **"verwandt"** when no word fits - cousins of different generations, the partner of a grandchild - and
  `None` for someone not connected to the home person at all.

`X` and `U` take the neutral word where German has one (Elternteil, Kind, Geschwister) and "Onkel oder Tante"
where it has none. Four generations and more repeat the "Ur": Ururgroßvater, Ururenkel.

## Familie Huber

`apps/family_tree/fixtures/huber_family.json` is the invented family of the mockup: sixteen people over four
generations around Lena Huber, the home person. It holds every case above - two couples with their
children, a father married twice with a son from his first marriage, two cousins with only their father -
and it is what the browser run
of [`/implement-story`](../../.claude/skills/implement-story/SKILL.md) plays with. Tests never load it to get
data, see [test data](testing-data.md).

```bash
uv run python manage.py loaddata huber_family
```

## See also

- [Belege](evidence.md) - facts, sources, citations and the uncertain date, including a couple's marriage
- [Test data](testing-data.md) - the factories for these models
- [Where code goes](app-layout.md) - models, readers and the admin at the app root
