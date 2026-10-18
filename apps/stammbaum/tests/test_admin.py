import pytest
from django.urls import reverse

from apps.stammbaum.tests.factories.einstellung import EinstellungFactory
from apps.stammbaum.tests.factories.eltern_kind import ElternKindFactory
from apps.stammbaum.tests.factories.geschwister import GeschwisterFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory


@pytest.mark.django_db
@pytest.mark.parametrize("model", ["person", "partnerschaft", "elternkind", "geschwister", "einstellung"])
def test_admin_lists_every_model(admin_client, model):
    response = admin_client.get(reverse(f"admin:stammbaum_{model}_changelist"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_shows_a_person_with_parents_children_and_partners(admin_client):
    eltern_kind = ElternKindFactory()
    PartnerschaftFactory(person_a=eltern_kind.kind)
    GeschwisterFactory(person_a=eltern_kind.kind)

    response = admin_client.get(reverse("admin:stammbaum_person_change", args=[eltern_kind.kind.pk]))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_offers_to_add_the_settings_while_there_are_none(admin_client):
    response = admin_client.get(reverse("admin:stammbaum_einstellung_add"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_refuses_a_second_row_of_settings(admin_client):
    EinstellungFactory()

    response = admin_client.get(reverse("admin:stammbaum_einstellung_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_never_deletes_the_settings(admin_client):
    einstellung = EinstellungFactory()

    response = admin_client.get(reverse("admin:stammbaum_einstellung_delete", args=[einstellung.pk]))

    assert response.status_code == 403
