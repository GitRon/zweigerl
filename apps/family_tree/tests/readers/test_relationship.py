import pytest

from apps.family_tree.models import Partnership, Person
from apps.family_tree.readers.relationship import family_graph
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory


@pytest.mark.django_db
def test_family_graph_holds_every_link():
    link = ParentChildFactory(parent__sex=Person.Sex.MALE, child__sex=Person.Sex.FEMALE)
    marriage = PartnershipFactory(person_a=link.parent, kind=Partnership.Kind.MARRIAGE)
    cohabitation = PartnershipFactory(person_a=link.parent, kind=Partnership.Kind.COHABITATION)
    sibling_pair = SiblingPairFactory()
    stranger = PersonFactory()

    graph = family_graph()

    group = frozenset((sibling_pair.person_a_id, sibling_pair.person_b_id))
    assert graph.parents == {
        link.child_id: {link.parent_id},
        sibling_pair.person_a_id: {group},
        sibling_pair.person_b_id: {group},
    }
    assert graph.partners[link.parent_id] == {marriage.person_b_id, cohabitation.person_b_id}
    assert graph.marriages == {frozenset((link.parent_id, marriage.person_b_id))}
    assert graph.sex[link.child_id] == Person.Sex.FEMALE
    assert stranger.pk in graph.sex
