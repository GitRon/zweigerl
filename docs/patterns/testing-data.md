# Test data

**Test data is always invented.** No real name, date, place or document of a living or dead relative goes
into a factory, a fixture, a test or an example — see [data storage](data-storage.md). Where a test needs
a recognisable family, it is the invented Familie Huber.

## Factories

- **Never create model instances directly in a test** — no `Person.objects.create()`, no
  `Person(...).save()`. Always go through a factory.
- Factories use [factory_boy](https://factoryboy.readthedocs.io) and live in
  `apps/family_tree/tests/factories/<model>.py`, one factory per model, subclassing
  `factory.django.DjangoModelFactory`.
- Use `build()` where the object never has to hit the database, `create()` only where it must.
- Create in batches (`create_batch()`) rather than in loops when you need several objects.
- Keep shared setup minimal and function-scoped. The more objects a fixture creates, the less isolated the
  tests using it become.

## One tree unless a test names another

`TreeFactory` finds its tree by name rather than making a new one each time, so every person, source, photo and
import a factory builds lands in the same tree, "Familie Huber", and a test of one family needs to say nothing about
trees. A test about a second tree names it - `PersonFactory(tree__name="Familie Berger")` - and
`TreeFactory(home_person=lena)` makes Lena the home person of the tree she is already in (#34).

## Mandatory relations belong in the factory

A factory has to produce a *valid* domain object. If every row of a model needs another row to make
sense, the factory creates it with a `SubFactory` or `RelatedFactory`, and a test reaches through it to
set up a case rather than building the related object separately:

```python
ParentChildFactory(child__given_names="Lena")  # a child with one parent, both made for it
ParentChildFactory(parent=johann, child=lena)  # or the two people the test already has
```

## Fixtures

The Familie Huber from the mockup is `apps/family_tree/fixtures/huber_family.json` - see
[persons and families](family.md#familie-huber) - for development and for the browser run of
[`/implement-story`](../../.claude/skills/implement-story/SKILL.md). **Tests do not load them.** A test that
asserts against the Hubers asserts against data it did not write down, and breaks when someone adds a
cousin. Build what the test needs with factories.

## The PAF and MyHeritage files

`apps/family_tree/tests/data/paf_export.ged` is a real PAF 5.2.18 export with every value about a person
replaced (#32) - the file the import (#22) is tested with. It keeps the real structure: line order, levels,
tags, xrefs, the BOM, CRLF, `CHAR UTF-8`, and the kind of every value, including the forms PAF really writes -
free-text dates, `CONC` cut mid-word, `//` and `/?/` surnames, `DIV` on a person, inline `OBJE` with `_PRIM`,
`_SCBK`, `_SSHOW` and `_TYPE`. `test_paf_export.py` beside it checks exactly that structure.

`myheritage_export.ged` beside it is a real export of MyHeritage Family Tree Builder, replaced the same way (#84):
GEDCOM 5.5.1 with a BOM, CRLF but none after the last line, a stray LF at the end of one place, dates as
`TT.MM.JJJJ` and `TO …`, `DEAT Y` with and without a date and with an `AGE` - also a range and "About" -
citations directly on the person with `PAGE`, `QUAY`, `EVEN` and `DATA`, `RESI` with an address and an `EMAIL`,
inline `OBJE` behind URLs with `_PRIM`, `_CUTOUT` and `_POSITION`, and `RIN`, `_UID` and `_UPD` on every record.
`test_myheritage_export.py` checks that structure.

**Only the result is in the repository; the real export never is.** `scripts/anonymise_gedcom.py` writes both:

```bash
uv run python -m scripts.anonymise_gedcom <real export> apps/family_tree/tests/data/paf_export.ged
uv run python -m scripts.anonymise_gedcom <real export> apps/family_tree/tests/data/myheritage_export.ged
```

- **Names** come from invented pools with the same kind of letters - plain, umlaut or ß, háček - and the
  same name maps to the same invented one throughout the file, so `NAME`, `GIVN`, `SURN` and a spouse's
  `_MARNM` still agree. **Places** keep their number of comma parts.
- **Dates** all move back by one random number of days, ten to thirty years, so order and lifespans stay;
  a year alone, a month and a year, and a day and a month move along. `ABT`, `oder`, `(?)` and a season stay.
- **Free text** - notes, descriptions, occupations, sources, addresses, file paths, the submitter - becomes
  letters of the same kind and length, word for word, so a `CONC` still cuts the same word in the same place. A
  path keeps its drive and its extension, a URL its scheme and host. `_UID`s and the numbers a program gives its
  records - `RIN`, `_PHOTO_RIN` - become new random hex in the same form. An `AGE` keeps its words, its numbers
  are replaced.
- **Titles in `NPFX`** ("Dr."), a citation's `QUAY` and what describes the file or a picture's role stay.
- **Nothing is written** when a tag carries a value the script has no rule for, or when a word it replaced
  is still in the result: a name or place from two letters, a free-text word from four. An invented
  name that happens to be a real one from the export is never chosen.
- **Every run is different.** The replacements and the date offset are drawn at random and kept only in
  memory, so nothing in the repository leads back to the real values - and a test must never pin an invented
  name or date, only a form.

ANSEL is not covered: the real export is UTF-8. An ANSEL import needs a second export of the same tree.

## Shared fixtures

- `request_with_session` and `datastar_request_with_session` in `apps/common/tests/conftest.py` — a
  request carrying an empty session, sent by the browser or by a datastar action.
