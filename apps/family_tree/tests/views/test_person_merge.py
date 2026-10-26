import json

import pytest
from django.urls import reverse

from apps.family_tree.models import Person
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory

DATASTAR = {"Datastar-Request": "true"}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_merge_dialog_view_appends_the_dialog(admin_client):
    josef = PersonFactory()

    response = admin_client.get(reverse("family_tree:merge-dialog-view", kwargs={"pk": josef.pk}), headers=DATASTAR)

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="merge-person-dialog"' in body


@pytest.mark.django_db
def test_merge_dialog_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(reverse("family_tree:merge-dialog-view", kwargs={"pk": 404}), headers=DATASTAR)

    assert response.status_code == 404


@pytest.mark.django_db
def test_merge_candidates_view_patches_whom_the_search_finds(admin_client):
    josef = PersonFactory(given_names="Josef")
    sepp = PersonFactory(given_names="Sepp")

    response = admin_client.get(
        reverse("family_tree:merge-candidates-view", kwargs={"pk": josef.pk}),
        {"datastar": json.dumps({"merge_search": " sepp "})},
        headers=DATASTAR,
    )

    body = _events(response)
    assert 'id="merge-candidates"' in body
    assert reverse("family_tree:merge-compare-view", kwargs={"pk": josef.pk, "other_pk": sepp.pk}) in body


@pytest.mark.django_db
def test_merge_compare_view_patches_the_two_side_by_side(admin_client):
    josef, sepp = PersonFactory(), PersonFactory()

    response = admin_client.get(
        reverse("family_tree:merge-compare-view", kwargs={"pk": josef.pk, "other_pk": sepp.pk}), headers=DATASTAR
    )

    assert 'id="merge-step"' in _events(response)


@pytest.mark.django_db
def test_merge_compare_view_of_the_person_and_themselves_is_not_found(admin_client):
    josef = PersonFactory()

    response = admin_client.get(
        reverse("family_tree:merge-compare-view", kwargs={"pk": josef.pk, "other_pk": josef.pk}), headers=DATASTAR
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_merge_view_merges_with_the_fields_chosen_and_opens_the_card(admin_client):
    josef = PersonFactory(given_names="Josef", call_name="")
    sepp = PersonFactory(given_names="Josef", call_name="Sepp")

    response = admin_client.post(
        reverse("family_tree:merge-view", kwargs={"pk": josef.pk, "other_pk": sepp.pk}),
        {"call_name": "other", "sex": "person"},
        headers=DATASTAR,
    )

    body = _events(response)
    assert list(Person.objects.values_list("pk", "call_name")) == [(josef.pk, "Sepp")]
    assert reverse("family_tree:person-view", kwargs={"pk": josef.pk}) in body
    assert admin_client.session["_toasts"] == [
        {"text": "Passt. Jetzt gibt's Sepp Huber nur noch einmal.", "style": "success"}
    ]


@pytest.mark.django_db
def test_merge_view_answers_a_refusal_with_its_reason(admin_client):
    partnership = PartnershipFactory()

    response = admin_client.post(
        reverse("family_tree:merge-view", kwargs={"pk": partnership.person_a_id, "other_pk": partnership.person_b_id}),
        headers=DATASTAR,
    )

    assert "Die beiden sind ein Paar, also zwei Personen." in _events(response)


@pytest.mark.django_db
def test_merge_view_answers_somebody_not_in_the_tree(admin_client):
    josef = PersonFactory()

    response = admin_client.post(
        reverse("family_tree:merge-view", kwargs={"pk": josef.pk, "other_pk": 404}), headers=DATASTAR
    )

    assert "Eine der beiden ist nicht mehr im Baum." in _events(response)
