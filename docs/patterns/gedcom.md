# GEDCOM

**The whole tree goes out as one GEDCOM 5.5.1 file in UTF-8, with everybody in it, and comes back in through
the same tags.** GEDCOM is how the data leaves Zweigerl - for another program, and inside every backup (#27) -
so nothing Zweigerl knows is dropped on the way out, and how a tree kept elsewhere comes in (#22). This page is
the one mapping between the models and the tags, both ways.

## The export

"GEDCOM herunterladen" on the settings page (`<c-settings.export>`) downloads `zweigerl-<date>.ged` from
`/export/gedcom/`: a plain GET, not a datastar request, since nothing on the page changes.
`readers.gedcom.gedcom_export()` builds the file and is what #27's backup calls too; `domain.gedcom.write`
writes the lines.

- **Everybody is in it, living or not** (decided 19.10.2026, #26). There is no option to leave people out:
  the export is for the person who keeps the tree, and sharing a tree is not part of v1.
- **The home person is the first `INDI`**, so an import into an empty tree makes them the home person again
  (#22).
- **Xrefs come from the ids**, so two exports of the same tree differ only where the tree does:

  | Xref | Record |
  |---|---|
  | `@I<id>@` | a Person |
  | `@F<id>@` | a Partnership |
  | `@FP<id>@` | a parent with the children no partnership is named for, by the parent's id |
  | `@FS<id>@` | a SiblingPair |
  | `@S<id>@` | a Source |
  | `@O<id>@` | a Photo |
  | `@U1@` | the submitter, "Zweigerl", which GEDCOM 5.5.1 requires |

- **Lines follow GEDCOM 5.5.1**: an `@` in a value is doubled, a line break continues on a `CONT` line and a
  value longer than 200 characters on `CONC` lines, cut beside a space rather than at one.

## What maps to what

### People

| Zweigerl | GEDCOM |
|---|---|
| `given_names`, `surname`, `call_name` | `NAME Lena /Huber/` with `GIVN`, `SURN`, `NICK`; no `NAME` for somebody without any |
| `sex` | `SEX` |
| `living_status` `deceased` | `DEAT Y`, unless a `death` fact or a `DEAT` an import kept raw already says so |
| `living_status` `living` | `_ZWG_STATUS living`; `unknown` writes nothing |
| a source filed with the person | `SOUR @S…@` directly under the `INDI` |
| a photo of the person | `OBJE @O…@`, with `_PRIM Y` for the portrait |

### Facts

One value per fact in Zweigerl, one event per date in GEDCOM - see [Belege](evidence.md#one-value-per-fact).

| `kind` | GEDCOM |
|---|---|
| `birth` and `birthplace` | one `BIRT` with `DATE` and `PLAC` - the first of each; another birth or birthplace is a `BIRT` of its own |
| `baptism`, `death`, `burial` | `CHR`, `DEAT`, `BURI` with `DATE` |
| `occupation`, `education`, `nationality` | `OCCU`, `EDUC`, `NATI` with the value on the line |
| `residence` | `RESI` with the value as `PLAC` |
| `marriage`, `divorce` | `MARR`, `DIV` with `DATE`, on the `FAM` |
| `custom` | `EVEN <value>` with `TYPE <label>` and the `DATE`, on the `INDI` or the `FAM` |

- **The date** is `domain.dates.to_gedcom`: `ABT 1931`, `BET 1820 AND 1825`, `12 MAR 1989`.
- **A citation** is `SOUR @S…@` below its fact, with `PAGE`. The citations of a birth and of a birthplace both
  hang below the joined `BIRT`, since GEDCOM 5.5.1 has none on a `PLAC`.
- **The reliability** is `_ZWG_RELIABILITY probable` or `handed_down` below the fact - below the `PLAC` for a
  birthplace. `documented` is the default and writes nothing, so a fact without a source still reads as
  *unbelegt* after a round trip.

### Families

| Zweigerl | GEDCOM |
|---|---|
| a Partnership | `FAM` with `HUSB` and `WIFE`: a woman is the `WIFE` whenever the other one is not a woman too, otherwise the order the couple was entered in decides - 5.5.1 knows no other roles, and `SEX` says who is who |
| `kind` `marriage` | implied by its `MARR`; without a `marriage` fact, `MARR Y` - unless an import kept a `MARR` raw, such as a date Zweigerl could not read |
| `kind` `cohabitation` | `_ZWG_KIND cohabitation`; `unknown` writes nothing |
| a ParentChild naming a Partnership | `CHIL` in that partnership's `FAM` |
| a ParentChild naming none | `CHIL` in the parent's own `FAM @FP…@`, the parent as `HUSB`, or as `WIFE` for a woman |
| `pedigree` | `PEDI` below the child's `FAMC` when its links into that family agree; two parents of different pedigree are `_FREL` (the `HUSB`'s) and `_MREL` (the `WIFE`'s) below the `CHIL` instead. `unknown` writes nothing |
| a SiblingPair | a `FAM @FS…@` with the two as `CHIL` and no parents |

### Sources and photos

| Zweigerl | GEDCOM |
|---|---|
| a Source | `SOUR` with `TITL`, the `description` as `TEXT`, the `kind` as `_ZWG_KIND` unless it is `other` |
| a SourceFile | `OBJE` with `FILE` and `FORM` inside the `SOUR` |
| a Photo | an `OBJE` record with `FILE`, `FORM` and the `description` as `TITL`, and the date it was taken as `_DATE` |

**A `FILE` is the path in the media directory** - `photos/17/original.jpg`, `sources/3/7.pdf` - named from ids
and roles, never from a name (see [data storage](data-storage.md#the-layout)). The file itself is not in the
`.ged`: the backup (#27) puts the media directory beside it, the `.gedzip` (#36) packs both.

### Tags of Zweigerl's own

What GEDCOM 5.5.1 has no tag for gets one starting `_ZWG_`, written only when the value is not the default, so
a tree entered the plain way exports as plain GEDCOM: `_ZWG_RELIABILITY`, `_ZWG_STATUS` and `_ZWG_KIND`.
`_PRIM`, `_FREL`, `_MREL` and `_DATE` are the tags other programs already write for the same thing.

## The import

`manage.py import_gedcom <file> --name "PAF Ronny"` reads a GEDCOM file into the tree (#22); the dialog with its
preview is #25 and calls the same action, `actions.gedcom_import.import_gedcom`.

- **Only into an empty tree.** Merging with people already there is #35, so the action refuses otherwise.
- **The first `INDI` becomes the home person**, as the export writes the home person first.
- **Every row goes through `save()`**, in one transaction: a row the models refuse names its record -
  "@F2@ in der Datei: Diese beiden sind schon ein Paar." - and nothing is left behind. The PAF export of 412
  people takes a few seconds.
- **Every row the import writes keeps its Herkunft**, the `GedcomImport` under the name given - see
  [Belege](evidence.md#terms). The person card shows it in its head and on each fact.

`domain.gedcom.read` reads the file: ged4py finds the character set - a BOM, the `CHAR` of the header, ANSEL -
and reads the lines, and `CONC` and `CONT` are joined as bytes, `CONC` without a space, so a word or a character
PAF cut in two comes back whole. ged4py's own reading of dates and names is not used: it turns `ABT 1931` into
`ABOUT 1931` and a date phrase into `(…)`. `domain.gedcom_import.read_tree` maps the records - which tag becomes
what is in [Belege](evidence.md#paf); in short, the table above read backwards, and:

| GEDCOM | Zweigerl |
|---|---|
| `NAME` | `given_names` and `surname` from `GIVN` and `SURN`, or from `Given /Surname/` without them; `//` and `/?/` stay as written; `NICK` is the `call_name` |
| `DEAT` or `BURI` | `living_status` `deceased`; without either it is `unknown`, never `living` |
| `MARR` | `kind` `marriage`, with or without a date Zweigerl can read |
| `FAM` with two parents | a Partnership, its children linked to both with it |
| `FAM` with one parent | the children linked to that parent alone, no Partnership |
| `FAM` without parents | a SiblingPair from the first child to each other one |
| `PEDI` below the child's `FAMC` | `pedigree`; a value Zweigerl has no word for is `unknown`, the `PEDI` stays raw |
| `DIV` below an `INDI` | a `DIV` of their family when they have exactly one, raw on the person otherwise |

`HEAD`, `SUBM` and `TRLR` describe the file and are left out. `SOUR` records, citations and `NOTE` as notes come
with #23; until then a `NOTE` stays raw on its record and a citation, being a pointer, is not kept.

## Raw GEDCOM

What an import brings that Zweigerl does not understand stays in the `gedcom_raw` of the row it belongs to (see
[persons and families](family.md#raw-gedcom)) and is written back one level below that row's record - below the
fact's event, below a citation's `SOUR`, below a child's `FAMC` for a ParentChild. Each entry is one GEDCOM
structure:

```json
{"tag": "_UID", "value": "4F2A93", "children": [{"tag": "_SRC", "value": "PAF"}]}
```

`value` and `children` may be missing. A value is the text as it reads, the export escapes it; a pointer to
another record is not kept raw, since its xref means nothing outside the file it came from. Migration `0007`
gave the dates migration `0003` kept (`{"tag": "MARR", "date": "im Krieg"}`) this shape.

- **A `NAME` without a value** on a person holds the parts of their name Zweigerl has no field for - `NPFX`,
  `_MARNM`, `_AKA` - and the export writes them below its own `NAME`, not as a second one.
- **An event without a date Zweigerl can read** stays raw whole on its owner: `{"tag": "DEAT", "children":
  [{"tag": "DATE", "value": "Frühjahr 1939"}]}`. A `DEAT` or a `MARR` that says only that it happened - `Y` or
  nothing - is not kept, since the status and the kind say it and the export writes it back.
- **What a fact has no field for** - the `PLAC` of a baptism, a death or a wedding, the `CAUS` of a death, the
  date of an occupation - stays raw below the fact.
- **A family of one parent has no row** for what its `FAM` carries, so its `_UID`, and a `MARR` or `DIV` it
  might carry, are not kept; the count of facts the import reports is the count written. The PAF export has
  neither on such a family.
- **What a child's `FAMC` and `CHIL` carry** goes on the link to the first parent alone, since the export
  writes the links of a child into one `FAMC`.

## The round trip

The PAF file of [test data](testing-data.md#the-paf-file), imported, exported and read again, gives the same
people and families - names, facts, pedigrees and everything kept raw. It is compared as what the records say,
not line by line: the export cuts a long value beside a space where PAF cuts it in the middle of a word, writes
the records in an order of its own and names them by ids.

## Not yet

- **GEDCOM 7 with the media packed in** is `.gedzip`, #36. The `OBJE` of a PAF export stays raw until #24 finds
  the files.

## See also

- [Belege](evidence.md) - facts, sources, citations and the uncertain date
- [Persons and families](family.md) - Person, Partnership, ParentChild, SiblingPair and the home person
- [Data storage](data-storage.md) - the media directory the `FILE` paths point into
