import pytest

from apps.family_tree.readers.person import Relatives, relatives
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory


@pytest.mark.django_db
def test_relatives_finds_parents_partner_and_children():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    emma = PersonFactory(given_names="Emma")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    PartnershipFactory(person_a=markus, person_b=lena)
    ParentChildFactory(parent=lena, child=emma)

    result = relatives(person=lena)

    assert result == Relatives(parents=[johann, maria], partners=[markus], children=[emma], siblings=[])


@pytest.mark.django_db
def test_relatives_finds_partners_on_either_side_of_the_pair():
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    anton = PersonFactory(given_names="Anton")
    PartnershipFactory(person_a=lena, person_b=markus)
    PartnershipFactory(person_a=anton, person_b=lena)

    assert relatives(person=lena).partners == [anton, markus]


@pytest.mark.django_db
def test_relatives_derives_siblings_from_a_shared_parent_and_half_siblings_too():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    lukas = PersonFactory(given_names="Lukas")
    florian = PersonFactory(given_names="Florian")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    ParentChildFactory(parent=johann, child=lukas)
    ParentChildFactory(parent=maria, child=lukas)
    ParentChildFactory(parent=johann, child=florian)

    assert relatives(person=lena).siblings == [florian, lukas]


@pytest.mark.django_db
def test_relatives_adds_explicit_siblings_from_either_side():
    katharina = PersonFactory(given_names="Katharina")
    stefan = PersonFactory(given_names="Stefan")
    anna = PersonFactory(given_names="Anna")
    PersonFactory(given_names="Fremd")
    SiblingPairFactory(person_a=katharina, person_b=stefan)
    SiblingPairFactory(person_a=anna, person_b=katharina)

    assert relatives(person=katharina).siblings == [anna, stefan]
