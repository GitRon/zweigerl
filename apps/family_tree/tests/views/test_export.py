import datetime
from unittest import mock

import pytest
from django.urls import reverse

from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
@mock.patch("apps.family_tree.views.export.localdate", return_value=datetime.date(2026, 10, 19))
def test_gedcom_export_view_hands_out_the_tree_as_a_file(_localdate, admin_client):
    PersonFactory()

    response = admin_client.get(reverse("family_tree:gedcom-export-view"))

    assert response.status_code == 200
    assert response["Content-Disposition"] == 'attachment; filename="zweigerl-2026-10-19.ged"'
