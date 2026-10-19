import pytest
from django.urls import reverse
from django.utils import timezone

from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_gedcom_export_view_hands_out_the_tree_as_a_file(admin_client):
    PersonFactory()

    response = admin_client.get(reverse("family_tree:gedcom-export-view"))

    assert response.status_code == 200
    assert response["Content-Disposition"] == f'attachment; filename="zweigerl-{timezone.localdate().isoformat()}.ged"'
