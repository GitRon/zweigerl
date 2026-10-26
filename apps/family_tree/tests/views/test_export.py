import datetime
from unittest import mock

import pytest
from django.urls import reverse

from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
@mock.patch("apps.family_tree.views.export.localdate", return_value=datetime.date(2026, 10, 19))
def test_gedcom_export_view_hands_out_the_tree_as_a_file(_localdate, admin_client):
    tree = PersonFactory(tree__name="Familie Gößl").tree

    response = admin_client.get(reverse("family_tree:gedcom-export-view", kwargs={"tree_pk": tree.pk}))

    assert response.status_code == 200
    assert response["Content-Disposition"] == 'attachment; filename="zweigerl-familie-goessl-2026-10-19.ged"'


@pytest.mark.django_db
def test_gedcom_export_view_refuses_a_tree_that_is_not_there(admin_client):
    tree = TreeFactory()

    response = admin_client.get(reverse("family_tree:gedcom-export-view", kwargs={"tree_pk": tree.pk + 1}))

    assert response.status_code == 404
