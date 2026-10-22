from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.backup import BackupAge
from apps.family_tree.readers.person import PersonList, PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

NEVER = BackupAge(text="noch nie", overdue=True)


def test_sidebar_asks_the_server_for_the_list_as_one_types():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" :loose_people="loose_people" :last_backup="last_backup" />',
        context={"person_list": PersonList(entries=[], total=0), "loose_people": [], "last_backup": NEVER},
    )

    search_field = parse(html).find("input", attrs={"type": "search"})
    assert (search_field["data-bind"], search_field["data-on:input__debounce.300ms"]) == (
        "search",
        f"@get('{reverse('family_tree:person-search-view')}')",
    )


def test_sidebar_asks_for_a_new_person():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" :loose_people="loose_people" :last_backup="last_backup" />',
        context={"person_list": PersonList(entries=[], total=0), "loose_people": [], "last_backup": NEVER},
    )

    assert parse(html).find("button", string="Person hinzufügen")["data-on:click"] == (
        f"@get('{reverse('family_tree:new-person-view')}')"
    )


def test_sidebar_leads_to_the_settings():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" :loose_people="loose_people" :last_backup="last_backup" />',
        context={"person_list": PersonList(entries=[], total=0), "loose_people": [], "last_backup": NEVER},
    )

    assert parse(html).find("a", string="Einstellungen")["href"] == reverse("family_tree:tree-settings-view")


def test_sidebar_lists_the_loose_twigs():
    rosa = PersonListEntry(person=PersonFactory.build(pk=9), name="Rosa Auer", initials="RA", lifespan="")

    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" :loose_people="loose_people" :last_backup="last_backup" />',
        context={"person_list": PersonList(entries=[], total=0), "loose_people": [rosa], "last_backup": NEVER},
    )

    assert "Rosa Auer" in parse(html).find(id="loose-people").get_text()


def test_sidebar_says_when_the_last_backup_was():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" :loose_people="loose_people" :last_backup="last_backup" />',
        context={"person_list": PersonList(entries=[], total=0), "loose_people": [], "last_backup": NEVER},
    )

    assert parse(html).find(id="backup-status").get_text(" ", strip=True).startswith("Zuletzt gesichert: noch nie")
