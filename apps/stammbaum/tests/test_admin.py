"""
Django's admin is not tested here (docs/patterns/testing-strategy.md, "Don't test"); what is, is the logic
of Zweigerl's own in "admin.py".
"""

import pytest
from django.forms import inlineformset_factory
from django.urls import reverse

from apps.stammbaum.admin import ElternFormSet
from apps.stammbaum.models import ElternKind, Person
from apps.stammbaum.tests.factories.einstellung import EinstellungFactory
from apps.stammbaum.tests.factories.person import PersonFactory

ElternForms = inlineformset_factory(
    Person, ElternKind, formset=ElternFormSet, fk_name="kind", fields=("elternteil", "art")
)


@pytest.mark.django_db
def test_eltern_formset_refuses_three_birth_parents_entered_at_once():
    johann, maria, franz = PersonFactory.create_batch(3)

    formset = ElternForms(
        data={
            "eltern_verbindungen-TOTAL_FORMS": "3",
            "eltern_verbindungen-INITIAL_FORMS": "0",
            "eltern_verbindungen-0-elternteil": johann.pk,
            "eltern_verbindungen-0-art": "leiblich",
            "eltern_verbindungen-1-elternteil": maria.pk,
            "eltern_verbindungen-1-art": "leiblich",
            "eltern_verbindungen-2-elternteil": franz.pk,
            "eltern_verbindungen-2-art": "leiblich",
        },
        instance=PersonFactory(),
    )

    assert formset.non_form_errors() == ["Ein Kind hat höchstens zwei leibliche Eltern."]


@pytest.mark.django_db
def test_eltern_formset_accepts_two_birth_parents_and_an_adoptive_one():
    johann, maria, franz = PersonFactory.create_batch(3)

    formset = ElternForms(
        data={
            "eltern_verbindungen-TOTAL_FORMS": "3",
            "eltern_verbindungen-INITIAL_FORMS": "0",
            "eltern_verbindungen-0-elternteil": johann.pk,
            "eltern_verbindungen-0-art": "leiblich",
            "eltern_verbindungen-1-elternteil": maria.pk,
            "eltern_verbindungen-1-art": "leiblich",
            "eltern_verbindungen-2-elternteil": franz.pk,
            "eltern_verbindungen-2-art": "adoptiert",
        },
        instance=PersonFactory(),
    )

    assert formset.is_valid() is True


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
