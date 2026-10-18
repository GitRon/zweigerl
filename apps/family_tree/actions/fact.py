from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.family_tree.domain.dates import UncertainDate, from_german
from apps.family_tree.models import Citation, Fact, Partnership, Person, Source
from apps.family_tree.models.fact import COUPLE_KINDS, CUSTOM, DATE_KINDS, VALUE_KINDS


def create_fact(
    *,
    person_id: int,
    kind: str,
    label: str,
    value: str,
    date: str,
    partner_id: int | None,
    reliability: str,
    citations: dict[int, str],
) -> Fact:
    """
    Adds a fact from the form on the person card (#14), citing "citations" - source id to the place in it. A
    marriage or a divorce goes on the person's partnership with "partner_id", every other kind on the person.
    "date" is German free text such as "um 1931", read by "domain.dates.from_german".

    Raises "Person.DoesNotExist" for somebody no longer in the tree and "ValidationError" with a German message
    for a fact the rules refuse, a date that cannot be read, a partner who is none or a source that is gone -
    saving nothing then.
    """
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        fact = Fact()
        _fill(
            fact=fact,
            person=person,
            kind=kind,
            label=label,
            value=value,
            date=date,
            partner_id=partner_id,
            reliability=reliability,
        )
        _cite(fact=fact, citations=citations)
    return fact


def change_fact(
    *,
    person_id: int,
    fact_id: int,
    kind: str,
    label: str,
    value: str,
    date: str,
    partner_id: int | None,
    reliability: str,
    citations: dict[int, str],
) -> Fact:
    """
    Saves a fact of the person or of one of their partnerships as changed in the form on their card (#14), the
    same way "create_fact" adds one; a citation no longer chosen goes. Raises "Fact.DoesNotExist" for a fact
    that is not theirs or no longer there, and the "ValidationError" of "create_fact".
    """
    with transaction.atomic():
        fact = _facts_of(person_id=person_id).get(pk=fact_id)
        _fill(
            fact=fact,
            person=Person.objects.get(pk=person_id),
            kind=kind,
            label=label,
            value=value,
            date=date,
            partner_id=partner_id,
            reliability=reliability,
        )
        _cite(fact=fact, citations=citations)
    return fact


def delete_fact(*, person_id: int, fact_id: int) -> None:
    """
    Removes a fact of the person or of one of their partnerships, with its citations; the sources stay. Raises
    "Fact.DoesNotExist" for a fact that is not theirs or no longer there.
    """
    _facts_of(person_id=person_id).get(pk=fact_id).delete()


def _facts_of(*, person_id: int) -> QuerySet[Fact]:
    return Fact.objects.filter(
        Q(person_id=person_id) | Q(partnership__person_a_id=person_id) | Q(partnership__person_b_id=person_id)
    )


def _fill(
    *,
    fact: Fact,
    person: Person,
    kind: str,
    label: str,
    value: str,
    date: str,
    partner_id: int | None,
    reliability: str,
) -> None:
    fact.kind = kind
    fact.reliability = reliability
    if kind in COUPLE_KINDS:
        fact.person, fact.partnership = None, _partnership(person=person, partner_id=partner_id)
    else:
        fact.person, fact.partnership = person, None

    # Only what the kind carries: the form keeps the fields of every kind, and a hidden one may still hold text.
    fact.label = label.strip() if kind == CUSTOM else ""
    fact.value = value.strip() if kind in (*VALUE_KINDS, CUSTOM) else ""
    parsed = _date(text=date) if kind in (*DATE_KINDS, CUSTOM) else None
    fact.date_kind = parsed.kind if parsed else ""
    fact.date_1 = parsed.date_1 if parsed else None
    fact.date_2 = parsed.date_2 if parsed else None
    fact.precision = parsed.precision if parsed else ""

    # "full_clean" rather than only the constraints "save" checks: it also holds the length of label and value.
    fact.full_clean()
    fact.save()


def _partnership(*, person: Person, partner_id: int | None) -> Partnership:
    partnership = Partnership.objects.filter(
        Q(person_a=person, person_b_id=partner_id) | Q(person_b=person, person_a_id=partner_id)
    ).first()
    if partnership is None:
        raise ValidationError("Mit wem? Wähl aus, wer der Partner ist.")
    return partnership


def _date(*, text: str) -> UncertainDate | None:
    # No date at all is left to the constraints, which say whether this kind needs one.
    if not text.strip():
        return None
    try:
        return from_german(text=text)
    except ValueError as error:
        raise ValidationError(str(error)) from error


def _cite(*, fact: Fact, citations: dict[int, str]) -> None:
    if Source.objects.filter(pk__in=citations).count() != len(citations):
        raise ValidationError("Eine der Quellen ist nicht mehr da.")

    fact.citations.exclude(source_id__in=citations).delete()
    cited = {citation.source_id: citation for citation in fact.citations.all()}
    for source_id, page in citations.items():
        citation = cited.get(source_id) or Citation(fact=fact, source_id=source_id)
        citation.page = page.strip()
        citation.full_clean()
        citation.save()
