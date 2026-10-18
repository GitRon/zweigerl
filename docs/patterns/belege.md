# Belege

> **Scaffold.** This page is written by #8, which introduces the model for facts and their sources. Until
> then it records the terms and the decisions already taken.

Every fact about a person in Zweigerl can say where it comes from and how reliable it is. That is the
point of the app, and this page will be the one normative description of how it works.

## Terms

| Term | Means |
|---|---|
| **Angabe** | One fact about a person: born, died, baptised, married, occupation, residence, … with its value |
| **Quelle** | Where facts come from: a civil register, a parish register (Matriken), family tradition, … with title, kind and files |
| **Zitat** | The link between an Angabe and a Quelle, carrying the page or place in the source |
| **Verlässlichkeit** | How sure the Angabe is: *belegt*, *wahrscheinlich* or *überliefert* |
| **unbelegt** | Derived, never stored: an Angabe marked *belegt* that has no Zitat |
| **Herkunft** | Which import an Angabe came from, e.g. "PAF Ronny". Not a Beleg: an imported Angabe without its own Quelle is marked *belegt* and therefore shows as *unbelegt*, so it stands out (#22, #23) |

## Decided

**Uncertain dates (#5, 18.10.2026).** A date is stored structured after GEDCOM: the kind (exact, about,
before, after, between — `ABT`, `BEF`, `AFT`, `BET … AND …`), date 1, date 2 (only for "between") and the
precision (day, month, year), plus a derived date to sort by. The form accepts free text such as
"um 1931" and splits it into these fields.

## What #8 adds here

- The models for Angabe, Quelle and Zitat and how they relate.
- The rule deriving *unbelegt*.
- Places as text, for now.

Later tickets add to this page: which PAF tags are mapped and which kept raw (#22).
