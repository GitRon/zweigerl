import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import ElternKind
from apps.stammbaum.tests.factories.eltern_kind import ElternKindFactory
from apps.stammbaum.tests.factories.geschwister import GeschwisterFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory


def test_eltern_kind_str_points_from_parent_to_child():
    eltern_kind = ElternKindFactory.build(
        elternteil=PersonFactory.build(vornamen="Johann"), kind=PersonFactory.build(vornamen="Lena")
    )

    assert str(eltern_kind) == "Johann Huber → Lena Huber"


def test_eltern_kind_clean_leaves_a_link_without_parent_to_the_field_validation():
    eltern_kind = ElternKind(kind=PersonFactory.build(pk=1))

    assert eltern_kind.clean() is None


@pytest.mark.django_db
def test_eltern_kind_clean_checks_the_partnership_before_the_child_is_saved():
    eltern_kind = ElternKind(
        elternteil=PersonFactory(), kind=PersonFactory.build(), partnerschaft=PartnerschaftFactory()
    )

    with pytest.raises(ValidationError, match="gehört nicht zu dieser Partnerschaft"):
        eltern_kind.clean()


@pytest.mark.django_db
def test_eltern_kind_clean_accepts_a_parent_of_a_child_not_saved_yet():
    eltern_kind = ElternKind(elternteil=PersonFactory(), kind=PersonFactory.build())

    assert eltern_kind.clean() is None


@pytest.mark.django_db
def test_eltern_kind_refuses_a_partnership_without_the_parent_on_save():
    with pytest.raises(ValidationError, match="gehört nicht zu dieser Partnerschaft"):
        ElternKindFactory(partnerschaft=PartnerschaftFactory())


@pytest.mark.django_db
def test_eltern_kind_saves_with_the_partnership_of_the_parent():
    partnerschaft = PartnerschaftFactory()

    eltern_kind = ElternKindFactory(elternteil=partnerschaft.person_a, partnerschaft=partnerschaft)

    assert ElternKind.objects.get().partnerschaft == eltern_kind.partnerschaft


@pytest.mark.django_db
def test_eltern_kind_refuses_a_shared_parent_of_explicit_siblings():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    GeschwisterFactory(person_a=stefan, person_b=katharina)
    ElternKindFactory(elternteil=franz, kind=stefan)

    with pytest.raises(ValidationError, match="Lösche erst diese Geschwister-Verbindung"):
        ElternKindFactory(elternteil=franz, kind=katharina)


@pytest.mark.django_db
def test_eltern_kind_refuses_a_shared_parent_of_explicit_siblings_stored_the_other_way_round():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    GeschwisterFactory(person_a=katharina, person_b=stefan)
    ElternKindFactory(elternteil=franz, kind=stefan)

    with pytest.raises(ValidationError, match="Lösche erst diese Geschwister-Verbindung"):
        ElternKindFactory(elternteil=franz, kind=katharina)


@pytest.mark.django_db
def test_eltern_kind_refuses_a_third_birth_parent():
    lena = PersonFactory()
    ElternKindFactory.create_batch(2, kind=lena)

    with pytest.raises(ValidationError, match="schon zwei leibliche Eltern"):
        ElternKindFactory(kind=lena, art=ElternKind.Art.LEIBLICH)


@pytest.mark.django_db
def test_eltern_kind_accepts_an_adoptive_parent_beside_two_birth_parents():
    lena = PersonFactory()
    ElternKindFactory.create_batch(2, kind=lena)

    ElternKindFactory(kind=lena, art=ElternKind.Art.ADOPTIERT)

    assert ElternKind.objects.filter(kind=lena).count() == 3


@pytest.mark.django_db
def test_eltern_kind_refuses_a_person_as_their_own_parent_on_save():
    johann = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Elternteil"):
        ElternKindFactory(elternteil=johann, kind=johann)


@pytest.mark.django_db
def test_eltern_kind_refuses_a_person_as_their_own_parent_in_the_database():
    johann = PersonFactory()

    with pytest.raises(IntegrityError, match="elternkind_nicht_selbst"):
        ElternKind.objects.bulk_create([ElternKind(elternteil=johann, kind=johann)])


@pytest.mark.django_db
def test_eltern_kind_refuses_the_same_link_twice_on_save():
    eltern_kind = ElternKindFactory(art=ElternKind.Art.ADOPTIERT)

    with pytest.raises(ValidationError, match="Diese Eltern-Kind-Verbindung gibt es schon"):
        ElternKindFactory(elternteil=eltern_kind.elternteil, kind=eltern_kind.kind, art=ElternKind.Art.ADOPTIERT)


@pytest.mark.django_db
def test_eltern_kind_refuses_the_same_link_twice_in_the_database():
    eltern_kind = ElternKindFactory()

    with pytest.raises(IntegrityError, match=r"stammbaum_elternkind\.elternteil_id, stammbaum_elternkind\.kind_id"):
        ElternKind.objects.bulk_create([ElternKind(elternteil=eltern_kind.elternteil, kind=eltern_kind.kind)])


@pytest.mark.django_db
def test_eltern_kind_refuses_an_unknown_kind_of_link_on_save():
    with pytest.raises(ValidationError, match="leiblich, adoptiert, Pflegekind oder unbekannt"):
        ElternKindFactory(art="geraten")


@pytest.mark.django_db
def test_eltern_kind_refuses_an_unknown_kind_of_link_in_the_database():
    johann, lena = PersonFactory.create_batch(2)

    with pytest.raises(IntegrityError, match="elternkind_art_gueltig"):
        ElternKind.objects.bulk_create([ElternKind(elternteil=johann, kind=lena, art="geraten")])
