import datetime

import pytest

from apps.family_tree.models import Fact, Person
from apps.family_tree.readers.person import (
    CitationChoice,
    FactEntry,
    PersonList,
    PersonListEntry,
    RelativeGroup,
    Relatives,
    fact_entry,
    fact_form,
    person_card,
    person_entries,
    person_list,
    relatives,
    sources_tab,
)
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
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
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—")], total=2
    )


@pytest.mark.django_db
def test_person_list_finds_the_call_name():
    gertrud = PersonFactory(given_names="Gertrud", surname="Huber", call_name="Gerti")
    PersonFactory(given_names="Gerhard", surname="Huber")

    result = person_list(search="gerti")

    assert result.entries == [PersonListEntry(person=gertrud, name="Gerti Huber", initials="GH", lifespan="—")]


@pytest.mark.django_db
def test_person_list_shows_the_earliest_birth_and_death():
    josef = PersonFactory(given_names="Josef", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=josef, date_1=datetime.date(1931, 3, 12))
    FactFactory(person=josef, date_1=datetime.date(1932, 1, 1), reliability=Fact.Reliability.HANDED_DOWN)
    FactFactory(person=josef, kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 5, 1))
    FactFactory(person=josef, kind=Fact.Kind.BAPTISM, date_1=datetime.date(1930, 1, 1))

    assert person_list(search="").entries[0].lifespan == "1931 – 2009"


@pytest.mark.django_db
def test_person_list_leaves_the_end_open_for_somebody_not_known_to_be_dead():
    lena = PersonFactory(given_names="Lena", living_status=Person.LivingStatus.LIVING)
    FactFactory(person=lena, date_1=datetime.date(1989, 3, 12))

    assert person_list(search="").entries[0].lifespan == "1989 –"


@pytest.mark.django_db
def test_person_list_asks_for_the_death_date_of_somebody_dead():
    theresia = PersonFactory(given_names="Theresia", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=theresia, date_1=datetime.date(1934, 1, 1))

    assert person_list(search="").entries[0].lifespan == "1934 – ?"


@pytest.mark.django_db
def test_person_entries_describes_only_the_people_asked_for():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    PersonFactory(given_names="Fremd")

    assert person_entries(person_ids=[lena.pk]) == {
        lena.pk: PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—")
    }


@pytest.mark.django_db
def test_person_card_describes_the_person():
    lena = PersonFactory(given_names="Lena", surname="Huber", living_status=Person.LivingStatus.LIVING)
    FactFactory(person=lena, date_1=datetime.date(1989, 3, 12))
    PersonFactory(given_names="Fremd")

    assert person_card(pk=lena.pk).entry == PersonListEntry(
        person=lena, name="Lena Huber", initials="LH", lifespan="1989 –"
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

    assert [(entry.label, entry.partner) for entry in person_card(pk=lena.pk).facts] == [
        ("Geheiratet", "Markus Gruber")
    ]


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
                entries=[PersonListEntry(person=johann, name="Johann Huber", initials="JH", lifespan="—")],
            ),
            RelativeGroup(
                title="Kinder", entries=[PersonListEntry(person=emma, name="Emma Huber", initials="EH", lifespan="—")]
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

    kinds = [kind.value for kind in fact_form(person_id=lena.pk).kinds]

    assert ("marriage" in kinds, "divorce" in kinds, "custom" in kinds) == (False, False, True)


@pytest.mark.django_db
def test_fact_form_shows_each_kind_with_its_fields_and_the_partners():
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus", surname="Gruber")
    PartnershipFactory(person_a=lena, person_b=markus)

    form = fact_form(person_id=lena.pk)

    assert (
        {kind.value: kind.fields for kind in form.kinds},
        [partner.name for partner in form.partners],
    ) == (
        {
            "birth": "date",
            "baptism": "date",
            "death": "date",
            "burial": "date",
            "birthplace": "value",
            "occupation": "value",
            "residence": "value",
            "education": "value",
            "nationality": "value",
            "marriage": "couple",
            "divorce": "couple",
            "custom": "custom",
        },
        ["Markus Gruber"],
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

    form = fact_form(person_id=partnership.person_b.pk, fact_id=marriage.pk)

    assert (form.key, form.fields, form.partner_id) == (str(marriage.pk), "couple", partnership.person_a.pk)


@pytest.mark.django_db
def test_fact_form_of_somebody_not_there_is_none():
    assert fact_form(person_id=404) is None


@pytest.mark.django_db
def test_fact_form_for_a_fact_of_somebody_else_is_none():
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    assert fact_form(person_id=stranger.pk, fact_id=birth.pk) is None
