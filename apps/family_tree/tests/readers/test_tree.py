import datetime

import pytest

from apps.family_tree.domain.layout import CARD_HEIGHT, ROW_GAP, Card, TreeLayout
from apps.family_tree.models import Fact
from apps.family_tree.readers.tree import tree_layout
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory

ROW = CARD_HEIGHT + ROW_GAP


@pytest.mark.django_db
def test_tree_layout_of_an_empty_tree_is_empty():
    assert tree_layout() == TreeLayout()


@pytest.mark.django_db
def test_tree_layout_is_laid_out_around_the_home_person():
    PersonFactory(given_names="Fremd")
    lena = PersonFactory(given_names="Lena")
    TreeSettingsFactory(home_person=lena)

    assert tree_layout().cards == (Card(person_id=lena.pk, x=0, y=0, generation=0),)


@pytest.mark.django_db
def test_tree_layout_without_a_home_person_starts_from_who_was_entered_first():
    josef = PersonFactory(given_names="Josef")
    PersonFactory(given_names="Fremd")

    assert tree_layout().cards == (Card(person_id=josef.pk, x=0, y=0, generation=0),)


@pytest.mark.django_db
def test_tree_layout_brings_partners_parents_and_siblings_without_known_parents():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    katharina = PersonFactory(given_names="Katharina")
    stefan = PersonFactory(given_names="Stefan")
    PartnershipFactory(person_a=johann, person_b=maria)
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    SiblingPairFactory(person_a=katharina, person_b=stefan)
    PartnershipFactory(person_a=lena, person_b=katharina)
    TreeSettingsFactory(home_person=lena)

    result = tree_layout()

    assert result.cards == (
        Card(person_id=johann.pk, x=0, y=0, generation=-1),
        Card(person_id=maria.pk, x=164, y=0, generation=-1),
        Card(person_id=lena.pk, x=92, y=ROW, generation=0),
        Card(person_id=katharina.pk, x=256, y=ROW, generation=0),
        Card(person_id=stefan.pk, x=460, y=ROW, generation=0),
    )
    assert result.placeholders[0].sibling_ids == (katharina.pk, stefan.pk)


@pytest.mark.django_db
def test_tree_layout_orders_siblings_by_their_earliest_birth_fact():
    johann = PersonFactory(given_names="Johann")
    lukas = PersonFactory(given_names="Lukas")
    lena = PersonFactory(given_names="Lena")
    florian = PersonFactory(given_names="Florian")
    ParentChildFactory(parent=johann, child=lukas)
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=johann, child=florian)
    FactFactory(person=lukas, date_1=datetime.date(1990, 1, 1))
    FactFactory(person=lena, date_1=datetime.date(1995, 1, 1))
    FactFactory(person=lena, date_1=datetime.date(1987, 1, 1))
    FactFactory(person=florian, as_value=True)
    FactFactory(person=florian, kind=Fact.Kind.DEATH, date_1=datetime.date(1950, 1, 1))
    TreeSettingsFactory(home_person=lena)

    assert tree_layout().cards[1:] == (
        Card(person_id=lena.pk, x=0, y=ROW, generation=0),
        Card(person_id=lukas.pk, x=172, y=ROW, generation=0),
        Card(person_id=florian.pk, x=344, y=ROW, generation=0),
    )
