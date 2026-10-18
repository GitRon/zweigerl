# Belege

**Every fact about a person can say where it comes from and how sure it is. A fact marked *belegt* that
cites nothing shows as *unbelegt*, so what still needs a source stands out.** That is the point of the app,
and this page is the one normative description of how it works.

## Terms

| Term | Means |
|---|---|
| **Angabe** | One fact about a person or a couple: born, died, baptised, married, occupation, residence, … with its value or its date |
| **Quelle** | Where facts come from: a civil register, a parish register (Matriken), family tradition, … with title, kind, description and files (#15) |
| **Zitat** | The link between an Angabe and a Quelle, carrying the page or place in the source |
| **Verlässlichkeit** | How sure the Angabe is: *belegt*, *wahrscheinlich* or *überliefert* |
| **unbelegt** | Derived, never stored: an Angabe marked *belegt* that has no Zitat |
| **Herkunft** | Which import an Angabe came from, e.g. "PAF Ronny". Not a Beleg: an imported Angabe without its own Quelle is marked *belegt* and therefore shows as *unbelegt*, so it stands out (#22, #23) |

## The models

`apps/stammbaum/models/`, each inheriting `ValidateConstraintsOnSaveMixin` - see
[rules in the database](app-layout.md#rules-in-the-database).

| Model | Holds | GEDCOM |
|---|---|---|
| `Angabe` | A Person **or** a Partnerschaft, the Art, a value or an uncertain date, the Verlässlichkeit | an event or attribute: `BIRT`, `OCCU`, `MARR`, … |
| `Quelle` | Titel, Art, Beschreibung (what the source says and where it is kept), the people it is filed with | `SOUR` |
| `Zitat` | One Angabe citing one Quelle, with the Stelle | `SOUR` under a fact, with `PAGE` |

### One value per Angabe

**A birth date and a birthplace are two Angaben**, each with its own Verlässlichkeit and its own Zitate:
the date may come from the birth certificate while the place is only what grandmother said. GEDCOM puts
both into one `BIRT` with `DATE` and `PLAC`; the import (#22) splits it, the export (#26) joins it again.

| Art | Carries | Belongs to | GEDCOM |
|---|---|---|---|
| Geboren, Getauft, Gestorben, Begräbnis | a date | a Person | `BIRT`, `CHR`/`BAPM`, `DEAT`, `BURI` `DATE` |
| Geburtsort, Beruf, Wohnort, Ausbildung, Staatsbürgerschaft | a value (`wert`) | a Person | `BIRT PLAC`, `OCCU`, `RESI PLAC`, `EDUC`, `NATI` |
| Geheiratet, Geschieden | a date | a Partnerschaft | `MARR`, `DIV` on the `FAM` |
| Eigene | a `bezeichnung`, and a value or a date | either | `EVEN`/`FACT` with `TYPE` |

**A marriage belongs to the couple, not to each partner.** Written on both persons it would be two copies
to keep in step; on the Partnerschaft it is one fact with one set of Zitate, where GEDCOM keeps it too.

**Places are text**, for now. A place model with coordinates and historical names is a later ticket.

### Quellen stand on their own

A Quelle is cited by any number of Angaben - one parish register serves a whole family. `personen` are the
people it is filed with, so a scanned document can sit on a person's card before anything cites it (#15).
The sources of a person, which #14 offers to cite and #15 lists, are those filed with them and those their
Angaben cite: `readers.beleg.quellen(person=…)`.

A Quelle that is cited cannot be deleted (`on_delete=PROTECT` on the Zitat): its facts would quietly turn
*unbelegt*. A Zitat goes with its Angabe.

## Unbelegt

**An Angabe is *unbelegt* when its Verlässlichkeit is *belegt* and it has no Zitat.** It is never stored,
so it cannot fall out of step with the Zitate:

- `Angabe.ist_unbelegt` for one Angabe,
- the `unbelegt` annotation of `readers.beleg.angaben(person=…)` for a list, in one query.

*Belegt* is the default. A new Angabe nobody has found a source for yet shows as *unbelegt* until it cites
one - which is the point. *Wahrscheinlich* and *überliefert* are a statement about the fact, not a missing
source, so they are never *unbelegt*, with or without a Zitat.

## Uncertain dates

Decided in #5 (18.10.2026): a date is stored structured after GEDCOM, plus a derived date to sort by.

| Field | Is |
|---|---|
| `datum_art` | *genau*, *ungefähr* (`ABT`, also `EST`/`CAL`), *vor* (`BEF`), *nach* (`AFT`), *zwischen* (`BET … AND …`) |
| `datum_1` | the date; a month is stored as its first day, a year as 1 January |
| `datum_2` | the end of the range - for *zwischen* only, and never before `datum_1` |
| `genauigkeit` | *Tag*, *Monat* or *Jahr*: how much of `datum_1` is known |
| `sortierdatum` | derived in `clean()` and `save()`: `datum_1`, and the middle of the range for *zwischen*, the range running to the end of its last month or year - "between 1820 and 1830" sorts beside mid-1825 |

`apps/stammbaum/domain/datum.py` holds the pure functions: `aus_gedcom` reads `ABT 1931`,
`BET 1820 AND 1825`, `APR 1989` or `12 MAR 1989`, `als_gedcom` writes them back, `sortierdatum` derives the
sort key. A date GEDCOM can express but Zweigerl cannot read - a date phrase, `FROM … TO`, another
calendar, or a range whose two ends are not equally precise - raises `ValueError`, and the importer keeps
it raw rather than inventing a day or dropping one. Both dates of a range share one `genauigkeit`.

**Something that writes past `save()`** - `bulk_create()` in an import, a data migration - sets
`sortierdatum` itself, from the same function; a constraint refuses a date without one.

The form (#14) accepts German free text such as "um 1931" or "zwischen 1820 und 1825" and splits it into
these fields; that parser arrives with the form.

## The rules, and who holds them

All of them are constraints with a German message - see
[rules in the database](app-layout.md#rules-in-the-database).

| Constraint | Rule |
|---|---|
| `angabe_genau_ein_bezug` | An Angabe belongs to a Person or a Partnerschaft, never both, never neither |
| `angabe_art_gueltig`, `angabe_verlaesslichkeit_gueltig` | Art and Verlässlichkeit are one of their choices |
| `angabe_art_passt_zum_bezug` | Geheiratet and Geschieden on a Partnerschaft, every other Art on a Person, Eigene on either |
| `angabe_datumsart_hat_datum` | A date kind has a date and no value |
| `angabe_wertart_hat_wert` | A value kind has a value and no date |
| `angabe_eigene_hat_bezeichnung` | Eigene has a `bezeichnung` and a value or a date; nothing else has one |
| `angabe_datum_vollstaendig` | A date has its kind and its precision; no date has neither |
| `angabe_sortierdatum_mit_datum` | A date has its sort date, and only a date has one |
| `angabe_datum_bis_nur_bei_zwischen` | `datum_2` exists for *zwischen* only and is not before `datum_1` |
| `quelle_hat_titel`, `quelle_art_gueltig` | A Quelle has a title and a known kind |
| `zitat_einmal_pro_angabe_und_quelle` | An Angabe cites a Quelle once; several places in it go into one `stelle` |

**`Angabe.clean()` checks `angabe_art_passt_zum_bezug` again in Python.** An admin inline leaves out the
foreign key it hangs on, so a form never validates that constraint, and the mixin would only find it in
`save()` - as a 500. `clean()` also sets `sortierdatum`, which no form shows.

## Before #8

Until #8 a Partnerschaft held its start and end as GEDCOM text in `beginn` and `ende`. Migration `0003`
turned them into Angaben on the Partnerschaft: "Geheiratet" and "Geschieden" for an Ehe, own Angaben
"Beginn der Partnerschaft" and "Ende der Partnerschaft" for any other couple - the start of a
Lebensgemeinschaft is not a wedding. A text it could not read went into the Partnerschaft's `gedcom_roh`.
Migrating back writes the dates into the two fields again.

## Later

Which PAF tags are mapped and which kept raw is added here by #22.

## See also

- [Persons and families](familie.md) - Person and Partnerschaft, which Angaben belong to
- [Where code goes](app-layout.md) - `domain/` for pure functions, rules in the database
