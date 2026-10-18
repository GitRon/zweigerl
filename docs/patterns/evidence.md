# Belege

**Every fact about a person can say where it comes from and how sure it is. A fact marked *belegt* that
cites nothing shows as *unbelegt*, so what still needs a source stands out.** That is the point of the app,
and this page is the one normative description of how it works.

## Terms

The prose uses the German terms of genealogy; a name in backticks is the one in the code - see
[locale and language](../contributing/settings.md#locale-and-language).

| Term | Code | Means |
|---|---|---|
| **Angabe** | `Fact` | One fact about a person or a couple: born, died, baptised, married, occupation, residence, … with its value or its date |
| **Quelle** | `Source` | Where facts come from: a civil register, a parish register (Matriken), family tradition, … with title, kind, description and files (#15) |
| **Zitat** | `Citation` | The link between a fact and a source, carrying the page or place in the source |
| **Verlässlichkeit** | `reliability` | How sure the fact is: *belegt* (`documented`), *wahrscheinlich* (`probable`) or *überliefert* (`handed_down`) |
| **unbelegt** | `undocumented` | Derived, never stored: a fact marked *belegt* that has no citation |
| **Herkunft** | - | Which import a fact came from, e.g. "PAF Ronny". Not a Beleg: an imported fact without its own source is marked *belegt* and therefore shows as *unbelegt*, so it stands out (#22, #23) |

## The models

`apps/family_tree/models/`, each inheriting `ValidateConstraintsOnSaveMixin` - see
[rules in the database](app-layout.md#rules-in-the-database).

| Model | Holds | GEDCOM |
|---|---|---|
| `Fact` | a `person` **or** a `partnership`, the `kind`, a `value` or an uncertain date, the `reliability` | an event or attribute: `BIRT`, `OCCU`, `MARR`, … |
| `Source` | `title`, `kind`, `description` (what the source says and where it is kept), the `people` it is filed with | `SOUR` |
| `Citation` | one fact citing one source, with the `page` | `SOUR` under a fact, with `PAGE` |
| `SourceFile` | one scan or PDF of a source, its `file` stored through `store_upload` at `sources/<source-id>/<file-id>.<ext>` | `OBJE` under a `SOUR` |

### One value per fact

**A birth date and a birthplace are two facts**, each with its own reliability and its own citations: the
date may come from the birth certificate while the place is only what grandmother said. GEDCOM puts both
into one `BIRT` with `DATE` and `PLAC`; the import (#22) splits it, the export (#26) joins it again.

| `kind` | Carries | Belongs to | GEDCOM |
|---|---|---|---|
| `birth`, `baptism`, `death`, `burial` | a date | a Person | `BIRT`, `CHR`/`BAPM`, `DEAT`, `BURI` `DATE` |
| `birthplace`, `occupation`, `residence`, `education`, `nationality` | a `value` | a Person | `BIRT PLAC`, `OCCU`, `RESI PLAC`, `EDUC`, `NATI` |
| `marriage`, `divorce` | a date | a Partnership | `MARR`, `DIV` on the `FAM` |
| `custom` | a `label`, and a value or a date | either | `EVEN`/`FACT` with `TYPE` |

**A marriage belongs to the couple, not to each partner.** Written on both persons it would be two copies
to keep in step; on the Partnership it is one fact with one set of citations, where GEDCOM keeps it too.

**Places are text**, for now. A place model with coordinates and historical names is a later ticket.

### Sources stand on their own

A source is cited by any number of facts - one parish register serves a whole family. `people` are the
persons it is filed with, so a scanned document can sit on a person's card before anything cites it (#15).
The sources of a person, which #14 offers to cite and #15 lists, are those filed with them and those cited
by their facts or by the facts of their partnerships: `readers.evidence.sources(person=…)`.

The Quellen tab of the person card (#15) shows each of them with its kind, title, description - the Zitat the
form asks for - and its files, and creates a new source filed with the person, with its scans and PDFs, or
attaches more to one: `actions.source.create_source` and `add_source_files`. A file is written only through
`store_upload`, after its row, so the id names it - see [data storage](data-storage.md#photos-and-scans). The
admin shows the files of a source but adds none, since a file saved there would keep its original name.

A source that is cited cannot be deleted (`on_delete=PROTECT` on the citation): its facts would quietly
turn *unbelegt*. A citation goes with its fact. **A source outlives the person it is filed with** (decided
18.10.2026, #19): deleting a person takes their facts and the citations of them, never a source or its scans.

## Unbelegt

**A fact is *unbelegt* when its reliability is `documented` and it has no citation.** It is never stored,
so it cannot fall out of step with the citations:

- `Fact.is_undocumented` for one fact, without a query when the citations are prefetched,
- the `undocumented` annotation of `readers.evidence.facts(person=…)` for a list, in one query.

`documented` is the default. A new fact nobody has found a source for yet shows as *unbelegt* until it
cites one - which is the point. *Wahrscheinlich* and *überliefert* are a statement about the fact, not a
missing source, so they are never *unbelegt*, with or without a citation.

## Uncertain dates

Decided in #5 (18.10.2026): a date is stored structured after GEDCOM, plus a derived date to sort by.

| Field | Is |
|---|---|
| `date_kind` | `exact`, `about` (`ABT`, also `EST`/`CAL`), `before` (`BEF`), `after` (`AFT`), `between` (`BET … AND …`) |
| `date_1` | the date; a month is stored as its first day, a year as 1 January |
| `date_2` | the end of the range - for `between` only, and never before `date_1` |
| `precision` | `day`, `month` or `year`: how much of `date_1` is known |
| `sort_date` | derived in `clean()` and `save()`: `date_1`, and the middle of the range for `between`, the range running to the end of its last month or year - "between 1820 and 1830" sorts beside mid-1825 |

`apps/family_tree/domain/dates.py` holds the pure functions: `from_gedcom` reads `ABT 1931`,
`BET 1820 AND 1825`, `APR 1989` or `12 MAR 1989`, `to_gedcom` writes them back, `sort_date` derives the
sort key. A date GEDCOM can express but Zweigerl cannot read - a date phrase, `FROM … TO`, another
calendar, or a range whose two ends are not equally precise - raises `ValueError`, and the importer keeps
it raw rather than inventing a day or dropping one. Both dates of a range share one `precision`.

**Something that writes past `save()`** - `bulk_create()` in an import, a data migration - sets
`sort_date` itself, from the same function; a constraint refuses a date without one.

The form (#14) accepts German free text such as "um 1931" or "zwischen 1820 und 1825" and splits it into
these fields; that parser arrives with the form.

## The rules, and who holds them

All of them are constraints with a German message - see
[rules in the database](app-layout.md#rules-in-the-database).

| Constraint | Rule |
|---|---|
| `fact_one_owner` | A fact belongs to a Person or a Partnership, never both, never neither |
| `fact_kind_valid`, `fact_reliability_valid` | `kind` and `reliability` are one of their choices |
| `fact_kind_matches_owner` | `marriage` and `divorce` on a Partnership, every other kind on a Person, `custom` on either |
| `fact_date_kind_has_date` | A date kind has a date and no value |
| `fact_value_kind_has_value` | A value kind has a value and no date |
| `fact_custom_has_label` | `custom` has a `label` and a value or a date; nothing else has one |
| `fact_date_complete` | A date has its `date_kind` and its `precision`; no date has neither |
| `fact_sort_date_with_date` | A date has its `sort_date`, and only a date has one |
| `fact_date_2_only_between` | `date_2` exists for `between` only and is not before `date_1` |
| `source_has_title`, `source_kind_valid` | A source has a title and a known kind |
| `citation_once_per_fact_and_source` | A fact cites a source once; several places in it go into one `page` |

**`Fact.clean()` checks `fact_kind_matches_owner` again in Python.** An admin inline leaves out the
foreign key it hangs on, so a form never validates that constraint, and the mixin would only find it in
`save()` - as a 500. `clean()` also sets `sort_date`, which no form shows.

## Before #8

Until #8 a Partnership held its start and end as GEDCOM text in `start` and `end`. Migration `0003`
turned them into facts on the Partnership: `marriage` and `divorce` for a marriage, `custom` facts
"Beginn der Partnerschaft" and "Ende der Partnerschaft" for any other couple - the start of a
cohabitation is not a wedding. A text it could not read went into the Partnership's `gedcom_raw`.
Migrating back writes the dates into the two fields again. The migration carries its own copy of the date
reading, so it does the same on every database whatever `domain/dates.py` becomes.

## Later

Which PAF tags are mapped and which kept raw is added here by #22.

## See also

- [Persons and families](family.md) - Person and Partnership, which facts belong to
- [Where code goes](app-layout.md) - `domain/` for pure functions, rules in the database
