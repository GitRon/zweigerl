"""
Django's admin is not tested here (docs/patterns/testing-strategy.md, "Don't test"); what is, is the logic
of Zweigerl's own in "admin.py".
"""

import pytest
from django.forms import inlineformset_factory
from django.urls import reverse

from apps.family_tree.admin import FactInline, ParentsFormSet
from apps.family_tree.models import Fact, ParentChild, Person
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory

FactForms = inlineformset_factory(Person, Fact, fk_name="person", fields=FactInline.fields)
ParentsForms = inlineformset_factory(
    Person, ParentChild, formset=ParentsFormSet, fk_name="child", fields=("parent", "pedigree")
)


@pytest.mark.django_db
def test_parents_formset_refuses_three_birth_parents_entered_at_once():
    johann, maria, franz = PersonFactory.create_batch(3)

    formset = ParentsForms(
        data={
            "parent_links-TOTAL_FORMS": "3",
            "parent_links-INITIAL_FORMS": "0",
            "parent_links-0-parent": johann.pk,
            "parent_links-0-pedigree": "birth",
            "parent_links-1-parent": maria.pk,
            "parent_links-1-pedigree": "birth",
            "parent_links-2-parent": franz.pk,
            "parent_links-2-pedigree": "birth",
        },
        instance=PersonFactory(),
    )

    assert formset.non_form_errors() == ["Ein Kind hat höchstens zwei leibliche Eltern."]


@pytest.mark.django_db
def test_parents_formset_accepts_two_birth_parents_and_an_adoptive_one():
    johann, maria, franz = PersonFactory.create_batch(3)

    formset = ParentsForms(
        data={
            "parent_links-TOTAL_FORMS": "3",
            "parent_links-INITIAL_FORMS": "0",
            "parent_links-0-parent": johann.pk,
            "parent_links-0-pedigree": "birth",
            "parent_links-1-parent": maria.pk,
            "parent_links-1-pedigree": "birth",
            "parent_links-2-parent": franz.pk,
            "parent_links-2-pedigree": "adopted",
        },
        instance=PersonFactory(),
    )

    assert formset.is_valid() is True


@pytest.mark.django_db
def test_admin_offers_to_add_the_settings_while_there_are_none(admin_client):
    response = admin_client.get(reverse("admin:family_tree_treesettings_add"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_refuses_a_second_row_of_settings(admin_client):
    TreeSettingsFactory()

    response = admin_client.get(reverse("admin:family_tree_treesettings_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_never_deletes_the_settings(admin_client):
    tree_settings = TreeSettingsFactory()

    response = admin_client.get(reverse("admin:family_tree_treesettings_delete", args=[tree_settings.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_fact_inline_refuses_a_marriage_on_a_person_with_a_message():
    """
    The inline leaves "person" out of its form, so the constraint is not checked there; "Fact.clean" is what
    turns the save into a form error instead of a 500.
    """
    formset = FactForms(
        data={
            "facts-TOTAL_FORMS": "1",
            "facts-INITIAL_FORMS": "0",
            "facts-0-kind": "marriage",
            "facts-0-date_kind": "exact",
            "facts-0-date_1": "1985-06-01",
            "facts-0-precision": "day",
            "facts-0-reliability": "documented",
        },
        instance=PersonFactory(),
    )

    assert formset.errors == [{"kind": ["Heirat und Scheidung gehören zur Partnerschaft, nicht zur Person."]}]
