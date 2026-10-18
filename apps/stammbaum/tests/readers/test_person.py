import pytest

from apps.stammbaum.readers.person import Verwandte, verwandte
from apps.stammbaum.tests.factories.eltern_kind import ElternKindFactory
from apps.stammbaum.tests.factories.geschwister import GeschwisterFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_verwandte_finds_parents_partner_and_children():
    johann = PersonFactory(vornamen="Johann")
    maria = PersonFactory(vornamen="Maria")
    lena = PersonFactory(vornamen="Lena")
    markus = PersonFactory(vornamen="Markus")
    emma = PersonFactory(vornamen="Emma")
    PersonFactory(vornamen="Fremd")
    ElternKindFactory(elternteil=johann, kind=lena)
    ElternKindFactory(elternteil=maria, kind=lena)
    PartnerschaftFactory(person_a=markus, person_b=lena)
    ElternKindFactory(elternteil=lena, kind=emma)

    result = verwandte(person=lena)

    assert result == Verwandte(eltern=[johann, maria], partner=[markus], kinder=[emma], geschwister=[])


@pytest.mark.django_db
def test_verwandte_finds_partners_on_either_side_of_the_pair():
    lena = PersonFactory(vornamen="Lena")
    markus = PersonFactory(vornamen="Markus")
    anton = PersonFactory(vornamen="Anton")
    PartnerschaftFactory(person_a=lena, person_b=markus)
    PartnerschaftFactory(person_a=anton, person_b=lena)

    assert verwandte(person=lena).partner == [anton, markus]


@pytest.mark.django_db
def test_verwandte_derives_siblings_from_a_shared_parent_and_half_siblings_too():
    johann = PersonFactory(vornamen="Johann")
    maria = PersonFactory(vornamen="Maria")
    lena = PersonFactory(vornamen="Lena")
    lukas = PersonFactory(vornamen="Lukas")
    florian = PersonFactory(vornamen="Florian")
    PersonFactory(vornamen="Fremd")
    ElternKindFactory(elternteil=johann, kind=lena)
    ElternKindFactory(elternteil=maria, kind=lena)
    ElternKindFactory(elternteil=johann, kind=lukas)
    ElternKindFactory(elternteil=maria, kind=lukas)
    ElternKindFactory(elternteil=johann, kind=florian)

    assert verwandte(person=lena).geschwister == [florian, lukas]


@pytest.mark.django_db
def test_verwandte_adds_explicit_siblings_from_either_side():
    katharina = PersonFactory(vornamen="Katharina")
    stefan = PersonFactory(vornamen="Stefan")
    anna = PersonFactory(vornamen="Anna")
    PersonFactory(vornamen="Fremd")
    GeschwisterFactory(person_a=katharina, person_b=stefan)
    GeschwisterFactory(person_a=anna, person_b=katharina)

    assert verwandte(person=katharina).geschwister == [anna, stefan]
