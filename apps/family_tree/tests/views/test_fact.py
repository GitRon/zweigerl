import datetime

import pytest
from django.urls import reverse

from apps.family_tree.models import Citation, Fact
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.tree import TreeFactory

DATASTAR = {"Datastar-Request": "true"}
FIELDS = {"kind": "birth", "label": "", "value": "", "date": "12. März 1958", "reliability": "documented", "search": ""}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_new_fact_view_patches_the_form_in_place_of_the_button(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.get(reverse("family_tree:new-fact-view", kwargs={"pk": lena.pk}), headers=DATASTAR)

    assert (response.status_code, 'id="fact-new"' in _events(response)) == (200, True)


@pytest.mark.django_db
def test_new_fact_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(reverse("family_tree:new-fact-view", kwargs={"pk": 404}), headers=DATASTAR)

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_fact_view_saves_and_patches_card_list_and_tree(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    TreeFactory(home_person=lena)

    response = admin_client.post(
        reverse("family_tree:create-fact-view", kwargs={"pk": lena.pk}), FIELDS, headers=DATASTAR
    )

    body = _events(response)
    assert Fact.objects.values_list("person", "date_1").get() == (lena.pk, datetime.date(1958, 3, 12))
    assert all(
        part in body
        for part in (
            'id="person-card"',
            'id="person-list"',
            'id="loose-people"',
            f'id="tree-card-{lena.pk}"',
            "Passt. Die Angabe ist gespeichert.",
        )
    )


@pytest.mark.django_db
def test_create_fact_view_reads_the_partner_and_the_chosen_sources_with_their_place(admin_client):
    partnership = PartnershipFactory()
    certificate = SourceFactory(people=[partnership.person_a])
    SourceFactory(people=[partnership.person_a])

    response = admin_client.post(
        reverse("family_tree:create-fact-view", kwargs={"pk": partnership.person_a.pk}),
        {
            **FIELDS,
            "kind": "marriage",
            "partner": str(partnership.person_b.pk),
            "sources": [str(certificate.pk), "keine"],
            f"page_{certificate.pk}": "Nr. 1958/12",
        },
        headers=DATASTAR,
    )

    _events(response)
    assert list(Citation.objects.values_list("fact__partnership", "source", "page")) == [
        (partnership.pk, certificate.pk, "Nr. 1958/12")
    ]


@pytest.mark.django_db
def test_create_fact_view_does_not_patch_a_tree_card_the_tree_does_not_show(admin_client):
    TreeFactory(home_person=PersonFactory())
    stranger = PersonFactory(given_names="Fremd")

    response = admin_client.post(
        reverse("family_tree:create-fact-view", kwargs={"pk": stranger.pk}), FIELDS, headers=DATASTAR
    )

    assert f'id="tree-card-{stranger.pk}"' not in _events(response)


@pytest.mark.django_db
def test_create_fact_view_answers_a_refusal_with_its_message(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.post(
        reverse("family_tree:create-fact-view", kwargs={"pk": lena.pk}),
        {**FIELDS, "date": "irgendwann"},
        headers=DATASTAR,
    )

    body = _events(response)
    assert "kein Datum, das Zweigerl lesen kann" in body and 'id="person-card"' not in body


@pytest.mark.django_db
def test_create_fact_view_of_somebody_not_there_says_so(admin_client):
    response = admin_client.post(reverse("family_tree:create-fact-view", kwargs={"pk": 404}), FIELDS, headers=DATASTAR)

    assert "Diese Person ist nicht mehr im Baum." in _events(response)


@pytest.mark.django_db
def test_edit_fact_view_patches_the_form_in_place_of_the_fact(admin_client):
    birth = FactFactory()

    response = admin_client.get(
        reverse("family_tree:edit-fact-view", kwargs={"pk": birth.person.pk, "fact_pk": birth.pk}), headers=DATASTAR
    )

    assert (response.status_code, f'id="fact-{birth.pk}"' in _events(response)) == (200, True)


@pytest.mark.django_db
def test_edit_fact_view_of_a_fact_of_somebody_else_is_not_found(admin_client):
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    response = admin_client.get(
        reverse("family_tree:edit-fact-view", kwargs={"pk": stranger.pk, "fact_pk": birth.pk}), headers=DATASTAR
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_change_fact_view_saves_and_patches_the_card(admin_client):
    birth = FactFactory()

    response = admin_client.post(
        reverse("family_tree:change-fact-view", kwargs={"pk": birth.person.pk, "fact_pk": birth.pk}),
        {**FIELDS, "date": "um 1931"},
        headers=DATASTAR,
    )

    body = _events(response)
    birth.refresh_from_db()
    assert birth.date_kind == "about"
    assert 'id="person-card"' in body and "Passt. Die Angabe ist geändert." in body


@pytest.mark.django_db
def test_change_fact_view_answers_a_refusal_with_its_message(admin_client):
    birth = FactFactory()

    response = admin_client.post(
        reverse("family_tree:change-fact-view", kwargs={"pk": birth.person.pk, "fact_pk": birth.pk}),
        {**FIELDS, "kind": "marriage"},
        headers=DATASTAR,
    )

    assert "Wähl aus, wer der Partner ist." in _events(response)


@pytest.mark.django_db
def test_change_fact_view_of_a_fact_no_longer_there_says_so(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.post(
        reverse("family_tree:change-fact-view", kwargs={"pk": lena.pk, "fact_pk": 404}), FIELDS, headers=DATASTAR
    )

    assert "Diese Angabe ist nicht mehr da." in _events(response)


@pytest.mark.django_db
def test_delete_fact_view_asks_first_in_a_dialog(admin_client):
    birth = FactFactory()

    response = admin_client.get(
        reverse("family_tree:delete-fact-view", kwargs={"pk": birth.person.pk, "fact_pk": birth.pk}), headers=DATASTAR
    )

    body = _events(response)
    assert "selector body" in body and "mode append" in body and 'id="delete-fact-dialog"' in body


@pytest.mark.django_db
def test_delete_fact_view_asks_about_a_fact_of_somebody_else_not_at_all(admin_client):
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    response = admin_client.get(
        reverse("family_tree:delete-fact-view", kwargs={"pk": stranger.pk, "fact_pk": birth.pk}), headers=DATASTAR
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_fact_view_removes_the_fact_closes_the_dialog_and_patches_the_card(admin_client):
    birth = FactFactory()

    response = admin_client.post(
        reverse("family_tree:delete-fact-view", kwargs={"pk": birth.person.pk, "fact_pk": birth.pk}),
        {"search": ""},
        headers=DATASTAR,
    )

    body = _events(response)
    assert Fact.objects.exists() is False
    assert all(
        part in body
        for part in (
            "selector #delete-fact-dialog",
            "mode remove",
            'id="person-card"',
            "Passt. Die Angabe ist entfernt.",
        )
    )


@pytest.mark.django_db
def test_delete_fact_view_of_a_fact_no_longer_there_says_so(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.post(
        reverse("family_tree:delete-fact-view", kwargs={"pk": lena.pk, "fact_pk": 404}),
        {"search": ""},
        headers=DATASTAR,
    )

    assert "Diese Angabe ist nicht mehr da." in _events(response)
