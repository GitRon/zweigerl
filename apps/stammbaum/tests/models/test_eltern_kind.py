import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import ElternKind
from apps.stammbaum.tests.factories.eltern_kind import ElternKindFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory


def test_eltern_kind_str_points_from_parent_to_child():
    eltern_kind = ElternKindFactory.build(
        elternteil=PersonFactory.build(vornamen="Johann"), kind=PersonFactory.build(vornamen="Lena")
    )

    assert str(eltern_kind) == "Johann Huber → Lena Huber"


def test_eltern_kind_clean_leaves_an_incomplete_link_to_the_field_validation():
    eltern_kind = ElternKind(kind=PersonFactory.build(pk=1))

    assert eltern_kind.clean() is None


@pytest.mark.django_db
def test_eltern_kind_clean_refuses_a_person_as_their_own_parent():
    johann = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Elternteil"):
        ElternKind(elternteil=johann, kind=johann).clean()


@pytest.mark.django_db
def test_eltern_kind_clean_refuses_a_partnership_without_the_parent():
    eltern_kind = ElternKind(elternteil=PersonFactory(), kind=PersonFactory(), partnerschaft=PartnerschaftFactory())

    with pytest.raises(ValidationError, match="gehört nicht zu dieser Partnerschaft"):
        eltern_kind.clean()


@pytest.mark.django_db
def test_eltern_kind_clean_accepts_the_partnership_of_the_parent():
    partnerschaft = PartnerschaftFactory()
    eltern_kind = ElternKind(elternteil=partnerschaft.person_a, kind=PersonFactory(), partnerschaft=partnerschaft)

    assert eltern_kind.clean() is None


@pytest.mark.django_db
def test_eltern_kind_clean_refuses_a_third_birth_parent():
    lena = PersonFactory()
    ElternKindFactory.create_batch(2, kind=lena)

    with pytest.raises(ValidationError, match="schon zwei leibliche Eltern"):
        ElternKind(elternteil=PersonFactory(), kind=lena, art=ElternKind.Art.LEIBLICH).clean()


@pytest.mark.django_db
def test_eltern_kind_clean_accepts_an_adoptive_parent_beside_two_birth_parents():
    lena = PersonFactory()
    ElternKindFactory.create_batch(2, kind=lena)

    assert ElternKind(elternteil=PersonFactory(), kind=lena, art=ElternKind.Art.ADOPTIERT).clean() is None


@pytest.mark.django_db
def test_eltern_kind_is_stored_once_per_parent_and_child():
    eltern_kind = ElternKindFactory()

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: stammbaum_elternkind"):
        ElternKindFactory(elternteil=eltern_kind.elternteil, kind=eltern_kind.kind)
