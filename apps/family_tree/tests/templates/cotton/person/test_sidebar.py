from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.backup import BackupAge
from apps.family_tree.readers.person import PersonList, PersonListEntry
from apps.family_tree.readers.trees import OpenTree
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory

NEVER = BackupAge(text="noch nie", overdue=True)
TAG = (
    '<c-person.sidebar :open_tree="open_tree" :person_list="person_list" :loose_people="loose_people"'
    ' :last_backup="last_backup" />'
)
HUBER = OpenTree(tree=TreeFactory.build(pk=3, name="Familie Huber"), others=[])


def _context(**changes) -> dict:
    return {
        "open_tree": HUBER,
        "person_list": PersonList(entries=[], total=0),
        "loose_people": [],
        "last_backup": NEVER,
        **changes,
    }


def test_sidebar_names_the_open_tree():
    html = render_component(tag=TAG, context=_context())

    assert parse(html).find(id="tree-switcher").get_text(strip=True) == "Familie Huber"


def test_sidebar_asks_the_server_for_the_list_of_the_tree_as_one_types():
    html = render_component(tag=TAG, context=_context())

    search_field = parse(html).find("input", attrs={"type": "search"})
    assert (search_field["data-bind"], search_field["data-on:input__debounce.300ms"]) == (
        "search",
        f"@get('{reverse('family_tree:person-search-view', kwargs={'tree_pk': 3})}')",
    )


def test_sidebar_asks_for_a_new_person_of_the_tree():
    html = render_component(tag=TAG, context=_context())

    assert parse(html).find("button", string="Person hinzufügen")["data-on:click"] == (
        f"@get('{reverse('family_tree:new-person-view', kwargs={'tree_pk': 3})}')"
    )


def test_sidebar_leads_to_the_settings_of_the_tree():
    html = render_component(tag=TAG, context=_context())

    assert parse(html).find("a", string="Einstellungen")["href"] == reverse(
        "family_tree:tree-settings-view", kwargs={"tree_pk": 3}
    )


def test_sidebar_lists_the_loose_twigs():
    rosa = PersonListEntry(person=PersonFactory.build(pk=9), name="Rosa Auer", initials="RA", lifespan="")

    html = render_component(tag=TAG, context=_context(loose_people=[rosa]))

    assert "Rosa Auer" in parse(html).find(id="loose-people").get_text()


def test_sidebar_says_when_the_last_backup_was():
    html = render_component(tag=TAG, context=_context())

    assert parse(html).find(id="backup-status").get_text(" ", strip=True).startswith("Zuletzt gesichert: noch nie")
