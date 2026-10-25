import pytest

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_candidate_names_the_person_with_their_lebensdaten():
    entry = PersonListEntry(person=PersonFactory(), name="Josef Huber", initials="JH", lifespan="1921 – 1988")

    html = render_component(tag='<c-person.candidate :entry="entry" />', context={"entry": entry})

    label = parse(html).find("label")
    assert label.get_text(" ", strip=True) == "JH Josef Huber 1921 – 1988"
