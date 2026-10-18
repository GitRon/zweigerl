# Test data

**Test data is always invented.** No real name, date, place or document of a living or dead relative goes
into a factory, a fixture, a test or an example — see [data storage](data-storage.md). Where a test needs
a recognisable family, it is the invented Familie Huber.

## Factories

- **Never create model instances directly in a test** — no `Person.objects.create()`, no
  `Person(...).save()`. Always go through a factory.
- Factories use [factory_boy](https://factoryboy.readthedocs.io) and live in
  `apps/stammbaum/tests/factories/<model>.py`, one factory per model, subclassing
  `factory.django.DjangoModelFactory`. The first models arrive with #7, and the factories with them.
- Use `build()` where the object never has to hit the database, `create()` only where it must.
- Create in batches (`create_batch()`) rather than in loops when you need several objects.
- Keep shared setup minimal and function-scoped. The more objects a fixture creates, the less isolated the
  tests using it become.

## Mandatory relations belong in the factory

A factory has to produce a *valid* domain object. If every row of a model needs another row to make
sense, the factory creates it with a `SubFactory` or `RelatedFactory`, and a test reaches through it to
set up a case rather than building the related object separately:

```python
AngabeFactory(person__vorname="Anna")
AngabeFactory(zitat=None)  # an Angabe without a source, which shows as "unbelegt"
```

## Fixtures

The Familie Huber from the mockup arrives with #7 as fixtures under `apps/stammbaum/fixtures/`, for
development and for the browser run of `/implement-story` (#29). **Tests do not load them.** A test that
asserts against the Hubers asserts against data it did not write down, and breaks when someone adds a
cousin. Build what the test needs with factories.

## Shared fixtures

- `request_with_session` and `datastar_request_with_session` in `apps/common/tests/conftest.py` — a
  request carrying an empty session, sent by the browser or by a datastar action.
