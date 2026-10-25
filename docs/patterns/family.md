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
| `TreeSettings` | The tree's settings - one row - holding the `home_person` (Ausgangsperson), the `backup_dir` backups go to (#27) and `last_backup_at`, when the last one was written (#33) | - |
| `Photo` | A photo (#16): its `file`, a `description` and the uncertain date it was taken, the `people` on it | `OBJE` with `FILE` and `TITL` |
| `PhotoPerson` | One person on one photo, and whether it is their portrait (`is_portrait`, the Titelbild). The through model of `Photo.people` | `OBJE` under an `INDI`, `_PRIM` |
| `GedcomImport` | One GEDCOM file read in (#22), its `name` - "PAF Ronny" - and when; the Herkunft of every row it wrote | - |

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

**Photos give a person a face** (#16). The Fotos tab of the person card uploads them -
`actions.photo.add_photos`, through `store_upload` at `photos/<photo-id>/original.<ext>`, see
[data storage](data-storage.md#photos-and-scans) - as JPEG, PNG or WebP; a TIFF or PDF scan is a source's.
The file is kept as it came: the picture frame shows its middle as 3:4 (`object-cover`) and the lightbox
the whole picture, so nothing is ever cut off a photo. The date the camera wrote fills in the date it was
taken, which the tab corrects as German free text, the way a fact's date is entered (#14): "um 1950",
"vor 1960", "zwischen 1950 und 1955". One photo per person may be their portrait, which every frame of them
shows - the card's head, the tree, the list - and the first photo of somebody without one becomes it.

**Names and status are corrected on the person card** (#30): the pencil beside the name opens the form
"Name & Status bearbeiten", saved by `actions.person.change_name_and_status`. Switching to `deceased` asks for
the year of death and records it as a `death` fact of that year, marked *belegt* and so shown as *unbelegt*
until it cites a source. The year is optional, it is asked only while no death fact is recorded, and switching
back leaves a recorded death fact alone - changing facts is #14.

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
| Somebody is on a photo once, and has at most one portrait | `photoperson_once`, `photoperson_one_portrait` - unique on `person` where `is_portrait` | "Eine Person hat höchstens ein Titelbild." |
| A photo's date is complete, sorted, and has a second date only as a range - as a fact's | `photo_date_complete`, `photo_sort_date_with_date`, `photo_date_2_only_between` | "Ein Aufnahmedatum braucht seine Art und seine Genauigkeit." |
| The home person cannot be deleted | `on_delete=PROTECT`, and `actions.person.delete_person` refuses first with a message; the admin says so too (#19) | "Das ist die Ausgangsperson. …" |

What spans several rows no constraint can hold, so it is in `clean()`, which the mixin runs on every save:

| Rule | In |
|---|---|
| A ParentChild's Partnership contains its parent | `ParentChild.clean()` |
| At most two `birth` parents | `ParentChild.clean()` against the saved rows, and the admin's `ParentsFormSet` for several entered at once |
| No SiblingPair row for people with a shared parent | `SiblingPair.clean()`, and `ParentChild.clean()` refuses the shared parent while the row is still there |

A name may be empty: GEDCOM allows a person without one, and "the unknown first wife" belongs in the tree.
`loaddata` writes past `save()`, so the Familie Huber fixture is held by the constraints alone.

## Raw GEDCOM

Person, Partnership, ParentChild, SiblingPair, Fact, Source and Citation have `gedcom_raw`, a JSON list of the
records an import brought along that Zweigerl does not understand, so the export writes them back (#22, #26).
Each is one GEDCOM structure, `{"tag", "value", "children"}` - see [GEDCOM](gedcom.md#raw-gedcom) for the shape
and where it is written. Nothing in Zweigerl reads it but the export, and nothing but the importer writes it.

Beside it each has `gedcom_import`, the Herkunft: the `GedcomImport` the row came from, under the name the import
was given (#22), and empty for a row entered here. The person card names it in its head ("Herkunft: PAF Ronny")
and on each fact. It is not a Beleg - see [Belege](evidence.md#terms). An import is protected while a row points
at it.

## Adding people

A person is added from the sidebar, connected to nobody, or from a person's card as their parent, partner,
child or sibling (#18) - in a short form with the names, `sex` and `living_status`; every fact follows on the new
person's card. `actions.person.add_relative` writes the person and the link in a transaction.

**The relative may be somebody already in the tree** (#89): the same dialog searches the tree once the relation is
chosen, with "Neue Person anlegen" below the hits, and `actions.person.link_relative` writes the link alone. Two
people both in the tree are connected there, never by entering one of them a second time. Afterwards the person's
own card opens again, with the relative among the Verwandte. Both actions write the same rows:

| As | Writes |
|---|---|
| Elternteil | a `ParentChild` of pedigree `birth`; a third birth parent is refused. A child with one parent so far gets the second on the couple the two are; while they are none, "Mit … ein Paar" - ticked to start with - makes them one, and the first parent's row joins it while it names none |
| Partner | a `Partnership` of kind `unknown` |
| Kind | a `ParentChild` to this person, on the couple chosen under "Kind von" - a couple's child gets a row to the partner as well - or to this person alone ("nur von …"). The only couple is chosen to start with, of several none |
| Geschwister | the same `ParentChild` rows the person has, with their `partnership` and `pedigree`, so a full sibling. Somebody already in the tree with parents of their own gives those to a person whose parents nobody knows. While neither has known parents, a `SiblingPair` |

A half-sibling is added as a child of the parent they share. Nobody is their own ancestor: no constraint can hold
that across generations, so both actions refuse such a parent link themselves. `actions.person.create_person` makes
the first person of an empty tree the home person.

`readers.person.relative_candidates` decides whom the search offers. It leaves out whom the rules would refuse or
who makes no sense - the person, who already is that to them, a descendant as parent, an ancestor or somebody with
two birth parents as child, a parent, child or sibling as partner, a parent or child as sibling - and suggests,
before anything is typed, whom the person most likely means:

| As | Suggested |
|---|---|
| Elternteil | the partners of the parent already there |
| Kind | the partner's children who are not yet the person's |
| Partner | the other parent of the person's children |
| Geschwister | the Lose Zweigerl |

Nobody is left out for their Lebensdaten: dates are too often unknown or uncertain, and hiding the right person is
worse than showing a wrong one.

## Deleting and unlinking

Deleting a person or removing one link never leaves a twig behind unnoticed (#19), and it never deletes anybody
else:

- **"Löschen" on the card asks first**, in a dialog from `readers.person.deletion_preview`: how many facts vanish -
  the person's and their partnerships', with the citations of them - how many sources stay (see
  [Belege](evidence.md)), every link that goes, and who would hang loose. People who would lose their connection
  to the home person are named in `brick`, and "Löschen" waits for the tick "Ist mir klar: N Personen hängen dann
  lose" - the view checks the number again, so a tree changed in the meantime asks again.
  `actions.person.delete_person` deletes; everything that goes with the person goes by `CASCADE`.
- **The home person is never deleted.** The dialog offers "Andere Ausgangsperson wählen…" instead, the action
  refuses, and the admin's delete page says she is the home person rather than reporting a missing permission.
- **"Verbindung lösen"** - the cross beside a relative on the Verwandte tab - removes exactly one row after a short
  question: the `ParentChild`, the `Partnership` (with the couple's facts; its children keep each parent) or the
  `SiblingPair`, `actions.person.unlink_relative`. A sibling through a shared parent has no button: their link is
  the parent's, and that is the one to remove.
- **Lose Zweigerl** - everyone with no connection to the home person, `readers.person.loose_people` - are never
  deleted on their own. They stand at the bottom of the sidebar, each linking to their card, to be connected again
  or deleted. Who is connected is `domain.relationship.connected_people`, the same walk the tree is drawn from.

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
