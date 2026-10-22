import datetime

import pytest

from apps.family_tree.models import Fact, Person
from apps.family_tree.readers.person import (
    CitationChoice,
    FactEntry,
    KindChoice,
    LinkPreview,
    PersonList,
    PersonListEntry,
    RelativeEntry,
    RelativeGroup,
    Relatives,
    deletion_preview,
    fact_entry,
    fact_form,
    link_preview,
    loose_people,
    person_card,
    person_entries,
    person_list,
    photos_tab,
    relative_groups,
    relatives,
    sources_tab,
)
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.gedcom_import import GedcomImportFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_relatives_finds_parents_partner_and_children():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    emma = PersonFactory(given_names="Emma")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    PartnershipFactory(person_a=markus, person_b=lena)
    ParentChildFactory(parent=lena, child=emma)

    result = relatives(person=lena)

    assert result == Relatives(parents=[johann, maria], partners=[markus], children=[emma], siblings=[])


@pytest.mark.django_db
def test_relatives_finds_partners_on_either_side_of_the_pair():
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    anton = PersonFactory(given_names="Anton")
    PartnershipFactory(person_a=lena, person_b=markus)
    PartnershipFactory(person_a=anton, person_b=lena)

    assert relatives(person=lena).partners == [anton, markus]


@pytest.mark.django_db
def test_relatives_derives_siblings_from_a_shared_parent_and_half_siblings_too():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    lukas = PersonFactory(given_names="Lukas")
    florian = PersonFactory(given_names="Florian")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    ParentChildFactory(parent=johann, child=lukas)
    ParentChildFactory(parent=maria, child=lukas)
    ParentChildFactory(parent=johann, child=florian)

    assert relatives(person=lena).siblings == [florian, lukas]


@pytest.mark.django_db
def test_relatives_adds_explicit_siblings_from_either_side():
    katharina = PersonFactory(given_names="Katharina")
    stefan = PersonFactory(given_names="Stefan")
    anna = PersonFactory(given_names="Anna")
    PersonFactory(given_names="Fremd")
    SiblingPairFactory(person_a=katharina, person_b=stefan)
    SiblingPairFactory(person_a=anna, person_b=katharina)

    assert relatives(person=katharina).siblings == [anna, stefan]


@pytest.mark.django_db
def test_person_list_sorts_by_family_name_and_counts_everybody():
    zach = PersonFactory(given_names="Anna", surname="Zach")
    oehler = PersonFactory(given_names="Anna", surname="Öhler")

    result = person_list(search="")

    assert (result.entries[0].person, result.entries[1].person, result.total) == (oehler, zach, 2)


@pytest.mark.django_db
def test_person_list_keeps_only_who_matches_the_search():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    PersonFactory(given_names="Markus", surname="Brandl")

    result = person_list(search="hub")

    assert result == PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="")], total=2
    )


@pytest.mark.django_db
def test_person_list_finds_the_call_name():
    gertrud = PersonFactory(given_names="Gertrud", surname="Huber", call_name="Gerti")
    PersonFactory(given_names="Gerhard", surname="Huber")

    result = person_list(search="gerti")

    assert result.entries == [PersonListEntry(person=gertrud, name="Gerti Huber", initials="GH", lifespan="")]


@pytest.mark.django_db
def test_person_list_shows_the_earliest_birth_and_death():
    josef = PersonFactory(given_names="Josef", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=josef, date_1=datetime.date(1931, 3, 12))
    FactFactory(person=josef, date_1=datetime.date(1932, 1, 1), reliability=Fact.Reliability.HANDED_DOWN)
    FactFactory(person=josef, kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 5, 1))
    FactFactory(person=josef, kind=Fact.Kind.BAPTISM, date_1=datetime.date(1930, 1, 1))

    assert person_list(search="").entries[0].lifespan == "* 1931 † 2009"


@pytest.mark.django_db
def test_person_list_shows_only_the_birth_of_somebody_not_known_to_be_dead():
    lena = PersonFactory(given_names="Lena", living_status=Person.LivingStatus.LIVING)
    FactFactory(person=lena, date_1=datetime.date(1989, 3, 12))

    assert person_list(search="").entries[0].lifespan == "* 1989"


@pytest.mark.django_db
def test_person_list_marks_somebody_dead_without_a_death_date():
    theresia = PersonFactory(given_names="Theresia", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=theresia, date_1=datetime.date(1934, 1, 1))

    assert person_list(search="").entries[0].lifespan == "* 1934 †"


@pytest.mark.django_db
def test_person_entries_describes_only_the_people_asked_for():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    PersonFactory(given_names="Fremd")

    assert person_entries(person_ids=[lena.pk]) == {
        lena.pk: PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="")
    }


@pytest.mark.django_db
def test_person_entries_carry_the_portrait():
    portrait = PhotoPersonFactory(
        is_portrait=True, photo=PhotoFactory(file="photos/5/original.jpg", description="Am Hof")
    )
    PhotoPersonFactory(person=portrait.person)

    entry = person_entries(person_ids=[portrait.person.pk])[portrait.person.pk]

    assert (entry.portrait_url, entry.portrait_alt) == ("/media/photos/5/original.jpg", "Am Hof")


@pytest.mark.django_db
def test_person_entries_describe_a_portrait_without_a_description_as_such():
    portrait = PhotoPersonFactory(is_portrait=True)

    entry = person_entries(person_ids=[portrait.person.pk])[portrait.person.pk]

    assert entry.portrait_alt == "Foto ohne Beschreibung"


@pytest.mark.django_db
def test_person_entries_without_a_portrait_have_none():
    photo_only = PhotoPersonFactory()

    entry = person_entries(person_ids=[photo_only.person.pk])[photo_only.person.pk]

    assert (entry.portrait_url, entry.portrait_alt) == ("", "")


@pytest.mark.django_db
def test_person_card_describes_the_person():
    lena = PersonFactory(given_names="Lena", surname="Huber", living_status=Person.LivingStatus.LIVING)
    FactFactory(person=lena, date_1=datetime.date(1989, 3, 12))
    PersonFactory(given_names="Fremd")

    assert person_card(pk=lena.pk).entry == PersonListEntry(
        person=lena, name="Lena Huber", initials="LH", lifespan="* 1989"
    )


@pytest.mark.django_db
def test_person_card_names_the_relationship_to_the_home_person():
    johann = PersonFactory(given_names="Johann", sex=Person.Sex.MALE)
    lena = PersonFactory(given_names="Lena")
    ParentChildFactory(parent=johann, child=lena)
    TreeSettingsFactory(home_person=lena)

    assert person_card(pk=johann.pk).relationship == "Vater"


@pytest.mark.django_db
def test_person_card_names_no_relationship_while_nobody_is_the_home_person():
    lena = PersonFactory(given_names="Lena")

    assert person_card(pk=lena.pk).relationship is None


@pytest.mark.django_db
def test_person_card_shows_a_documented_fact_with_its_beleg():
    lena = PersonFactory(given_names="Lena")
    citation = CitationFactory(fact__person=lena, fact__date_1=datetime.date(1989, 3, 12))
    FactFactory(person=PersonFactory(given_names="Fremd"))

    assert person_card(pk=lena.pk).facts == [
        FactEntry(
            fact=citation.fact,
            label="Geboren",
            text="12. März 1989",
            reliability=None,
            citations=[citation],
            undocumented=False,
        )
    ]


@pytest.mark.django_db
def test_person_card_shows_a_documented_fact_without_a_citation_as_undocumented():
    occupation = FactFactory(as_value=True)

    assert person_card(pk=occupation.person.pk).facts == [
        FactEntry(fact=occupation, label="Beruf", text="Uhrmacher", reliability=None, citations=[], undocumented=True)
    ]


@pytest.mark.django_db
def test_person_card_labels_a_handed_down_fact():
    custom = FactFactory(
        as_value=True, kind=Fact.Kind.CUSTOM, label="Spitzname", value="Hias", reliability=Fact.Reliability.HANDED_DOWN
    )

    assert person_card(pk=custom.person.pk).facts == [
        FactEntry(
            fact=custom, label="Spitzname", text="Hias", reliability="Überliefert", citations=[], undocumented=False
        )
    ]


@pytest.mark.django_db
def test_person_card_shows_both_value_and_date_of_a_custom_fact():
    custom = FactFactory(kind=Fact.Kind.CUSTOM, label="Erstkommunion", value="Pfarrkirche Mariazell")

    assert person_card(pk=custom.person.pk).facts[0].text == "Pfarrkirche Mariazell, 12. März 1931"


@pytest.mark.django_db
def test_person_card_names_the_partner_of_a_marriage():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    markus = PersonFactory(given_names="Markus", surname="Gruber")
    FactFactory(person=None, partnership=PartnershipFactory(person_a=markus, person_b=lena), kind=Fact.Kind.MARRIAGE)

    found = person_card(pk=lena.pk).facts

    assert (len(found), found[0].label, found[0].partner) == (1, "Geheiratet", "Markus Gruber")


@pytest.mark.django_db
def test_person_card_groups_the_relatives_and_counts_them():
    johann = PersonFactory(given_names="Johann", surname="Huber")
    lena = PersonFactory(given_names="Lena", surname="Huber")
    emma = PersonFactory(given_names="Emma", surname="Huber")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=lena, child=emma)

    card = person_card(pk=lena.pk)

    assert (card.relatives, card.relative_count) == (
        [
            RelativeGroup(
                title="Eltern",
                relation="parent",
                entries=[
                    RelativeEntry(
                        entry=PersonListEntry(person=johann, name="Johann Huber", initials="JH", lifespan=""),
                        unlinkable=True,
                    )
                ],
            ),
            RelativeGroup(
                title="Kinder",
                relation="child",
                entries=[
                    RelativeEntry(
                        entry=PersonListEntry(person=emma, name="Emma Huber", initials="EH", lifespan=""),
                        unlinkable=True,
                    )
                ],
            ),
        ],
        2,
    )


@pytest.mark.django_db
def test_person_card_holds_the_sources_tab():
    lena = PersonFactory(given_names="Lena")
    source = SourceFactory(people=[lena])

    assert person_card(pk=lena.pk).sources_tab.sources == [source]


@pytest.mark.django_db
def test_person_card_knows_a_death_fact_is_recorded():
    death = FactFactory(kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 5, 2))

    assert person_card(pk=death.person.pk).death_recorded is True


@pytest.mark.django_db
def test_person_card_knows_no_death_fact_is_recorded():
    birth = FactFactory()
    FactFactory(kind=Fact.Kind.DEATH, person=PersonFactory(given_names="Fremd"))

    assert person_card(pk=birth.person.pk).death_recorded is False


@pytest.mark.django_db
def test_person_card_names_the_import_the_person_came_from():
    lena = PersonFactory(gedcom_import=GedcomImportFactory(name="PAF Huber"))

    assert person_card(pk=lena.pk).origin == "PAF Huber"


@pytest.mark.django_db
def test_person_card_names_no_import_for_somebody_entered_here():
    lena = PersonFactory()

    assert person_card(pk=lena.pk).origin is None


@pytest.mark.django_db
def test_person_card_names_the_import_of_a_fact_and_still_shows_it_as_undocumented():
    occupation = FactFactory(as_value=True, gedcom_import=GedcomImportFactory(name="PAF Huber"))

    assert person_card(pk=occupation.person.pk).facts == [
        FactEntry(
            fact=occupation,
            label="Beruf",
            text="Uhrmacher",
            reliability=None,
            citations=[],
            undocumented=True,
            origin="PAF Huber",
        )
    ]


@pytest.mark.django_db
def test_person_card_of_somebody_not_there_is_none():
    assert person_card(pk=404) is None


@pytest.mark.django_db
def test_fact_entry_describes_one_fact_of_the_person():
    occupation = FactFactory(as_value=True)
    FactFactory(person=occupation.person)

    assert fact_entry(person_id=occupation.person.pk, fact_id=occupation.pk) == FactEntry(
        fact=occupation, label="Beruf", text="Uhrmacher", reliability=None, citations=[], undocumented=True
    )


@pytest.mark.django_db
def test_fact_entry_of_somebody_else_is_none():
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    assert fact_entry(person_id=stranger.pk, fact_id=birth.pk) is None


@pytest.mark.django_db
def test_fact_entry_of_somebody_not_there_is_none():
    birth = FactFactory()

    assert fact_entry(person_id=404, fact_id=birth.pk) is None


@pytest.mark.django_db
def test_sources_tab_holds_the_sources_with_their_files_and_every_kind():
    lena = PersonFactory(given_names="Lena")
    scan = SourceFileFactory(source__people=[lena])
    SourceFactory(people=[PersonFactory(given_names="Fremd")])

    found = sources_tab(pk=lena.pk)

    assert (found.person, found.sources, list(found.sources[0].files.all()), found.kinds[0]) == (
        lena,
        [scan.source],
        [scan],
        ("civil_registry", "Standesamt"),
    )


@pytest.mark.django_db
def test_sources_tab_of_somebody_not_there_is_none():
    assert sources_tab(pk=404) is None


@pytest.mark.django_db
def test_person_card_holds_the_photos_tab():
    link = PhotoPersonFactory()

    (entry,) = person_card(pk=link.person.pk).photos_tab.photos

    assert entry.link == link


@pytest.mark.django_db
def test_photos_tab_holds_the_persons_photos_oldest_first_and_undated_last():
    lena = PersonFactory()
    undated = PhotoPersonFactory(person=lena)
    later = PhotoPersonFactory(
        person=lena, photo=PhotoFactory(date_kind="exact", date_1=datetime.date(1975, 6, 1), precision="month")
    )
    earlier = PhotoPersonFactory(person=lena, photo=PhotoFactory(about_1950=True))
    PhotoPersonFactory()

    first, second, third = photos_tab(pk=lena.pk).photos

    assert (first.link, second.link, third.link) == (earlier, later, undated)


@pytest.mark.django_db
def test_photos_tab_describes_each_photo():
    link = PhotoPersonFactory(photo=PhotoFactory(file="photos/5/original.jpg", about_1950=True))

    (entry,) = photos_tab(pk=link.person.pk).photos

    assert (entry.url, entry.alt, entry.date) == ("/media/photos/5/original.jpg", "Foto ohne Beschreibung", "um 1950")


@pytest.mark.django_db
def test_photos_tab_leaves_the_date_of_an_undated_photo_empty():
    link = PhotoPersonFactory()

    (entry,) = photos_tab(pk=link.person.pk).photos

    assert entry.date == ""


@pytest.mark.django_db
def test_photos_tab_of_somebody_not_there_is_none():
    assert photos_tab(pk=404) is None


@pytest.mark.django_db
def test_fact_form_for_a_new_fact_asks_for_a_birth_date_and_offers_the_persons_sources():
    lena = PersonFactory(given_names="Lena")
    source = SourceFactory(people=[lena])
    SourceFactory(people=[PersonFactory(given_names="Fremd")])

    form = fact_form(person_id=lena.pk)

    assert (form.person, form.key, form.kind, form.fields, form.date, form.reliability, form.citations) == (
        lena,
        "new",
        "birth",
        "date",
        "",
        "documented",
        [CitationChoice(source=source, cited=False, page="")],
    )


@pytest.mark.django_db
def test_fact_form_offers_marriage_and_divorce_only_with_a_partner():
    lena = PersonFactory(given_names="Lena")

    kinds = fact_form(person_id=lena.pk).kinds

    assert (
        KindChoice(value="marriage", label="Geheiratet", fields="couple") in kinds,
        KindChoice(value="divorce", label="Geschieden", fields="couple") in kinds,
        KindChoice(value="custom", label="Eigene", fields="custom") in kinds,
    ) == (False, False, True)


@pytest.mark.django_db
def test_fact_form_shows_each_kind_with_its_fields_and_the_partners():
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus", surname="Gruber")
    PartnershipFactory(person_a=lena, person_b=markus)

    form = fact_form(person_id=lena.pk)

    assert (form.kinds, form.partners) == (
        [
            KindChoice(value="birth", label="Geboren", fields="date"),
            KindChoice(value="baptism", label="Getauft", fields="date"),
            KindChoice(value="death", label="Gestorben", fields="date"),
            KindChoice(value="burial", label="Begräbnis", fields="date"),
            KindChoice(value="birthplace", label="Geburtsort", fields="value"),
            KindChoice(value="occupation", label="Beruf", fields="value"),
            KindChoice(value="residence", label="Wohnort", fields="value"),
            KindChoice(value="education", label="Ausbildung", fields="value"),
            KindChoice(value="nationality", label="Staatsbürgerschaft", fields="value"),
            KindChoice(value="marriage", label="Geheiratet", fields="couple"),
            KindChoice(value="divorce", label="Geschieden", fields="couple"),
            KindChoice(value="custom", label="Eigene", fields="custom"),
        ],
        [person_entries(person_ids=[markus.pk])[markus.pk]],
    )


@pytest.mark.django_db
def test_fact_form_for_a_fact_holds_its_date_as_text_and_its_citations():
    citation = CitationFactory(fact__reliability=Fact.Reliability.PROBABLE, page="fol. 12")
    other = SourceFactory(people=[citation.fact.person])

    form = fact_form(person_id=citation.fact.person.pk, fact_id=citation.fact.pk)

    assert (form.fact, form.date, form.reliability, form.citations) == (
        citation.fact,
        "12. März 1931",
        "probable",
        [
            CitationChoice(source=citation.source, cited=True, page="fol. 12"),
            CitationChoice(source=other, cited=False, page=""),
        ],
    )


@pytest.mark.django_db
def test_fact_form_for_a_marriage_chose_the_other_partner():
    partnership = PartnershipFactory()
    marriage = FactFactory(person=None, partnership=partnership, kind=Fact.Kind.MARRIAGE)

    form = fact_form(person_id=partnership.person_a.pk, fact_id=marriage.pk)

    assert (form.key, form.fields, form.partner_id) == (str(marriage.pk), "couple", partnership.person_b.pk)


@pytest.mark.django_db
def test_fact_form_of_somebody_not_there_is_none():
    assert fact_form(person_id=404) is None


@pytest.mark.django_db
def test_fact_form_for_a_fact_of_somebody_else_is_none():
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    assert fact_form(person_id=stranger.pk, fact_id=birth.pk) is None


def _names(entries: list[PersonListEntry]) -> list[str]:
    return [entry.person.given_names for entry in entries]


@pytest.mark.django_db
def test_relative_groups_offer_unlinking_an_explicit_sibling_but_not_one_through_a_parent():
    johann = PersonFactory(given_names="Johann")
    lena = PersonFactory(given_names="Lena")
    florian = PersonFactory(given_names="Florian")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=johann, child=florian)
    katharina = PersonFactory(given_names="Katharina")
    stefan = PersonFactory(given_names="Stefan")
    SiblingPairFactory(person_a=katharina, person_b=stefan)

    through_parent = relative_groups(person=lena)[-1].entries[0]
    explicit = relative_groups(person=stefan)[-1].entries[0]

    assert (through_parent.entry.person, through_parent.unlinkable, explicit.entry.person, explicit.unlinkable) == (
        florian,
        False,
        katharina,
        True,
    )


@pytest.mark.django_db
def test_deletion_preview_of_somebody_not_there_is_none():
    assert deletion_preview(pk=404) is None


@pytest.mark.django_db
def test_deletion_preview_counts_what_vanishes_and_the_sources_and_photos_that_stay():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    marriage = PartnershipFactory(person_a=johann, person_b=maria)
    birth = FactFactory(person=johann)
    CitationFactory(fact=birth)
    CitationFactory(fact=FactFactory(person=None, partnership=marriage, kind=Fact.Kind.MARRIAGE))
    FactFactory(person=maria)
    SourceFactory(people=[johann])
    PhotoPersonFactory(person=johann)
    PhotoPersonFactory(person=maria)

    preview = deletion_preview(pk=johann.pk)

    assert (preview.fact_count, preview.citation_count, preview.source_count, preview.photo_count) == (2, 2, 3, 1)


@pytest.mark.django_db
def test_deletion_preview_lists_every_link_that_goes():
    johann = PersonFactory(given_names="Johann")
    lena = PersonFactory(given_names="Lena")
    ParentChildFactory(parent=johann, child=lena)

    groups = deletion_preview(pk=johann.pk).relatives

    assert (len(groups), groups[0].title, groups[0].entries[0].entry.person) == (1, "Kinder", lena)


@pytest.mark.django_db
def test_deletion_preview_of_the_home_person_says_so_and_cuts_off_nobody():
    lena = PersonFactory(given_names="Lena")
    ParentChildFactory(parent=lena)
    TreeSettingsFactory(home_person=lena)

    preview = deletion_preview(pk=lena.pk)

    assert (preview.home, preview.cut_off) == (True, [])


@pytest.mark.django_db
def test_deletion_preview_names_whom_the_deletion_cuts_off_from_the_home_person():
    lena = PersonFactory(given_names="Lena")
    johann = PersonFactory(given_names="Johann")
    franz = PersonFactory(given_names="Franz")
    anna = PersonFactory(given_names="Anna")
    maria = PersonFactory(given_names="Maria")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=franz, child=johann)
    ParentChildFactory(parent=anna, child=johann)
    ParentChildFactory(parent=maria, child=lena)
    TreeSettingsFactory(home_person=lena)

    preview = deletion_preview(pk=johann.pk)

    assert (preview.home, _names(preview.cut_off)) == (False, ["Anna", "Franz"])


@pytest.mark.django_db
def test_deletion_preview_without_a_home_person_measures_from_the_person_entered_first():
    johann = PersonFactory(given_names="Johann")
    lena = PersonFactory(given_names="Lena")
    emma = PersonFactory(given_names="Emma")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=lena, child=emma)

    assert (_names(deletion_preview(pk=lena.pk).cut_off), _names(deletion_preview(pk=johann.pk).cut_off)) == (
        ["Emma"],
        [],
    )


@pytest.mark.django_db
def test_deletion_preview_of_the_only_person_cuts_off_nobody():
    lena = PersonFactory(given_names="Lena")

    assert deletion_preview(pk=lena.pk).cut_off == []


@pytest.mark.django_db
@pytest.mark.parametrize(("relation", "of_child", "name"), [("parent", True, "Elternteil"), ("child", False, "Kind")])
def test_link_preview_finds_a_parent_and_a_child_link(relation, of_child, name):
    link = ParentChildFactory()
    person, relative = (link.child, link.parent) if of_child else (link.parent, link.child)

    preview = link_preview(pk=person.pk, relation=relation, relative_pk=relative.pk)

    assert (preview.person.person, preview.relative.person, preview.relation_name) == (person, relative, name)


@pytest.mark.django_db
def test_link_preview_of_a_partner_counts_the_couple_facts_from_either_side():
    partnership = PartnershipFactory()
    FactFactory(person=None, partnership=partnership, kind=Fact.Kind.MARRIAGE)
    FactFactory(person=None, partnership=PartnershipFactory(person_a=partnership.person_a), kind=Fact.Kind.MARRIAGE)

    preview = link_preview(pk=partnership.person_b_id, relation="partner", relative_pk=partnership.person_a_id)

    assert (preview.relation_name, preview.couple_fact_count) == ("Partner", 1)


@pytest.mark.django_db
def test_link_preview_finds_an_explicit_sibling():
    pair = SiblingPairFactory()

    assert link_preview(pk=pair.person_b_id, relation="sibling", relative_pk=pair.person_a_id) == LinkPreview(
        person=person_entries(person_ids=[pair.person_b_id])[pair.person_b_id],
        relative=person_entries(person_ids=[pair.person_a_id])[pair.person_a_id],
        relation="sibling",
        relation_name="Geschwister",
        couple_fact_count=0,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("relation", ["sibling", "partner", "cousin"])
def test_link_preview_without_such_a_link_is_none(relation):
    # Siblings through a shared parent: no link of their own.
    link = ParentChildFactory()
    sibling = ParentChildFactory(parent=link.parent)

    assert link_preview(pk=link.child_id, relation=relation, relative_pk=sibling.child_id) is None


@pytest.mark.django_db
def test_loose_people_are_those_with_no_connection_to_the_home_person():
    lena = PersonFactory(given_names="Lena")
    ParentChildFactory(parent=PersonFactory(given_names="Johann"), child=lena)
    franz = PersonFactory(given_names="Franz", surname="Berger")
    anna = PersonFactory(given_names="Anna", surname="Berger")
    PartnershipFactory(person_a=franz, person_b=anna)
    PersonFactory(given_names="Rosa", surname="Auer")
    TreeSettingsFactory(home_person=lena)

    assert _names(loose_people()) == ["Rosa", "Anna", "Franz"]


@pytest.mark.django_db
def test_loose_people_without_a_home_person_are_measured_from_the_person_entered_first():
    johann = PersonFactory(given_names="Johann")
    ParentChildFactory(parent=johann)
    PersonFactory(given_names="Rosa", surname="Auer")

    assert _names(loose_people()) == ["Rosa"]


@pytest.mark.django_db
def test_loose_people_of_an_empty_tree_are_nobody():
    assert loose_people() == []
