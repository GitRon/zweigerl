import pytest
from django.utils import timezone

from apps.family_tree.domain.dates import MONTHS
from apps.family_tree.models import Fact, ParentChild, Partnership, Person, Source
from apps.family_tree.readers.gedcom import gedcom_export
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory

RAW = [{"tag": "_UID", "value": "4F2A"}]


@pytest.mark.django_db
def test_gedcom_export_opens_with_the_header_and_ends_with_the_trailer():
    today = timezone.localdate()

    text = gedcom_export()

    assert text == (
        "0 HEAD\n"
        "1 SOUR ZWEIGERL\n"
        "2 NAME Zweigerl\n"
        f"1 DATE {today.day} {MONTHS[today.month - 1]} {today.year}\n"
        "1 SUBM @U1@\n"
        "1 GEDC\n"
        "2 VERS 5.5.1\n"
        "2 FORM LINEAGE-LINKED\n"
        "1 CHAR UTF-8\n"
        "0 @U1@ SUBM\n"
        "1 NAME Zweigerl\n"
        "0 TRLR\n"
    )


@pytest.mark.django_db
def test_gedcom_export_writes_the_name_with_its_parts():
    lena = PersonFactory(given_names="Lena Maria", surname="Huber", call_name="Leni", sex=Person.Sex.FEMALE)

    text = gedcom_export()

    assert (
        f"0 @I{lena.pk}@ INDI\n1 NAME Lena Maria /Huber/\n2 GIVN Lena Maria\n2 SURN Huber\n2 NICK Leni\n1 SEX F\n"
        in text
    )


@pytest.mark.django_db
def test_gedcom_export_writes_no_name_for_somebody_without_one():
    unknown_wife = PersonFactory(given_names="", surname="")

    text = gedcom_export()

    assert f"0 @I{unknown_wife.pk}@ INDI\n1 SEX U\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_puts_the_home_person_first():
    anna = PersonFactory(given_names="Anna")
    lena = TreeSettingsFactory(home_person__given_names="Lena").home_person

    text = gedcom_export()

    assert text.index(f"0 @I{lena.pk}@ INDI") < text.index(f"0 @I{anna.pk}@ INDI")


@pytest.mark.django_db
def test_gedcom_export_joins_birth_and_birthplace_into_one_birt():
    birth = FactFactory(person__given_names="", person__surname="")
    birthplace = FactFactory(
        person=birth.person, as_value=True, kind=Fact.Kind.BIRTHPLACE, value="Mariazell", reliability="probable"
    )
    birth_citation = CitationFactory(fact=birth, page="fol. 12")
    place_citation = CitationFactory(fact=birthplace, page="")

    text = gedcom_export()

    assert (
        "1 BIRT\n2 DATE 12 MAR 1931\n2 PLAC Mariazell\n3 _ZWG_RELIABILITY probable\n"
        f"2 SOUR @S{birth_citation.source_id}@\n3 PAGE fol. 12\n2 SOUR @S{place_citation.source_id}@\n"
    ) in text


@pytest.mark.django_db
def test_gedcom_export_gives_a_second_birthplace_its_own_birt():
    birth = FactFactory(person__given_names="", person__surname="")
    FactFactory(person=birth.person, as_value=True, kind=Fact.Kind.BIRTHPLACE, value="Mariazell")
    FactFactory(person=birth.person, as_value=True, kind=Fact.Kind.BIRTHPLACE, value="Gußwerk")

    text = gedcom_export()

    assert "1 BIRT\n2 DATE 12 MAR 1931\n2 PLAC Mariazell\n1 BIRT\n2 PLAC Gußwerk\n" in text


@pytest.mark.parametrize(
    ("kind", "lines"),
    [
        (Fact.Kind.BAPTISM, "1 CHR\n2 DATE 12 MAR 1931\n"),
        (Fact.Kind.DEATH, "1 DEAT\n2 DATE 12 MAR 1931\n"),
        (Fact.Kind.BURIAL, "1 BURI\n2 DATE 12 MAR 1931\n"),
    ],
)
@pytest.mark.django_db
def test_gedcom_export_writes_a_date_fact_as_its_event(kind, lines):
    FactFactory(kind=kind)

    text = gedcom_export()

    assert lines in text


@pytest.mark.parametrize(
    ("kind", "lines"),
    [
        (Fact.Kind.OCCUPATION, "1 OCCU Uhrmacher\n"),
        (Fact.Kind.EDUCATION, "1 EDUC Uhrmacher\n"),
        (Fact.Kind.NATIONALITY, "1 NATI Uhrmacher\n"),
        (Fact.Kind.RESIDENCE, "1 RESI\n2 PLAC Uhrmacher\n"),
    ],
)
@pytest.mark.django_db
def test_gedcom_export_writes_a_value_fact_as_its_attribute(kind, lines):
    FactFactory(as_value=True, kind=kind)

    text = gedcom_export()

    assert lines in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_custom_fact_as_even_with_its_type():
    FactFactory(kind=Fact.Kind.CUSTOM, label="Firmung", value="Mariazell", between=True)

    text = gedcom_export()

    assert "1 EVEN Mariazell\n2 TYPE Firmung\n2 DATE BET 1820 AND 1830\n" in text


@pytest.mark.django_db
def test_gedcom_export_names_a_reliability_other_than_documented():
    FactFactory(as_value=True, reliability=Fact.Reliability.HANDED_DOWN)

    text = gedcom_export()

    assert "1 OCCU Uhrmacher\n2 _ZWG_RELIABILITY handed_down\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_citation_with_its_page():
    citation = CitationFactory(fact__as_value=True, page="Nr. 1989/3471")

    text = gedcom_export()

    assert f"1 OCCU Uhrmacher\n2 SOUR @S{citation.source_id}@\n3 PAGE Nr. 1989/3471\n" in text


@pytest.mark.django_db
def test_gedcom_export_marks_somebody_living():
    lena = PersonFactory(given_names="", surname="", living_status=Person.LivingStatus.LIVING)

    text = gedcom_export()

    assert f"0 @I{lena.pk}@ INDI\n1 SEX U\n1 _ZWG_STATUS living\n" in text


@pytest.mark.django_db
def test_gedcom_export_records_the_death_of_somebody_deceased_without_a_death_fact():
    josef = PersonFactory(given_names="", surname="", living_status=Person.LivingStatus.DECEASED)

    text = gedcom_export()

    assert f"0 @I{josef.pk}@ INDI\n1 SEX U\n1 DEAT Y\n" in text


@pytest.mark.django_db
def test_gedcom_export_adds_no_second_death_to_a_recorded_one():
    FactFactory(kind=Fact.Kind.DEATH, person__living_status=Person.LivingStatus.DECEASED)

    text = gedcom_export()

    assert "DEAT Y" not in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_couple_with_the_woman_as_wife():
    partnership = PartnershipFactory(person_a__sex=Person.Sex.FEMALE, person_b__sex=Person.Sex.MALE)
    FactFactory(person=None, partnership=partnership, kind=Fact.Kind.MARRIAGE)

    text = gedcom_export()

    assert (
        f"0 @F{partnership.pk}@ FAM\n1 HUSB @I{partnership.person_b_id}@\n1 WIFE @I{partnership.person_a_id}@\n"
        "1 MARR\n2 DATE 12 MAR 1931\n"
    ) in text


@pytest.mark.django_db
def test_gedcom_export_keeps_the_order_of_a_couple_of_two_women():
    partnership = PartnershipFactory(person_a__sex=Person.Sex.FEMALE, person_b__sex=Person.Sex.FEMALE)

    text = gedcom_export()

    assert f"1 HUSB @I{partnership.person_a_id}@\n1 WIFE @I{partnership.person_b_id}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_marriage_without_a_date_as_marr_y():
    partnership = PartnershipFactory()

    text = gedcom_export()

    assert f"1 WIFE @I{partnership.person_b_id}@\n1 MARR Y\n" in text


@pytest.mark.django_db
def test_gedcom_export_names_a_cohabitation():
    partnership = PartnershipFactory(kind=Partnership.Kind.COHABITATION)

    text = gedcom_export()

    assert f"1 WIFE @I{partnership.person_b_id}@\n1 _ZWG_KIND cohabitation\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_nothing_for_a_partnership_of_unknown_kind():
    partnership = PartnershipFactory(kind=Partnership.Kind.UNKNOWN)

    text = gedcom_export()

    assert f"1 WIFE @I{partnership.person_b_id}@\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_puts_a_child_into_the_family_of_its_partnership():
    partnership = PartnershipFactory()
    link = ParentChildFactory(parent=partnership.person_a, partnership=partnership)
    ParentChildFactory(parent=partnership.person_b, child=link.child, partnership=partnership)

    text = gedcom_export()

    assert f"1 CHIL @I{link.child_id}@\n" in text
    assert f"1 FAMC @F{partnership.pk}@\n2 PEDI birth\n" in text


@pytest.mark.django_db
def test_gedcom_export_tells_apart_two_parents_of_different_pedigree():
    partnership = PartnershipFactory()
    link = ParentChildFactory(parent=partnership.person_a, partnership=partnership, pedigree="adopted")
    ParentChildFactory(parent=partnership.person_b, child=link.child, partnership=partnership)

    text = gedcom_export()

    assert f"1 CHIL @I{link.child_id}@\n2 _FREL adopted\n2 _MREL birth\n" in text
    assert f"1 FAMC @F{partnership.pk}@\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_writes_no_pedi_for_an_unknown_pedigree():
    link = ParentChildFactory(pedigree=ParentChild.Pedigree.UNKNOWN)

    text = gedcom_export()

    assert f"1 FAMC @FP{link.parent_id}@\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_gives_a_mother_without_partnership_a_family_of_her_own():
    link = ParentChildFactory(parent__sex=Person.Sex.FEMALE)

    text = gedcom_export()

    assert f"0 @FP{link.parent_id}@ FAM\n1 WIFE @I{link.parent_id}@\n1 CHIL @I{link.child_id}@\n" in text
    assert f"1 FAMS @FP{link.parent_id}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_gives_a_father_without_partnership_a_family_of_his_own():
    link = ParentChildFactory(parent__sex=Person.Sex.MALE)

    text = gedcom_export()

    assert f"0 @FP{link.parent_id}@ FAM\n1 HUSB @I{link.parent_id}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_siblings_without_known_parents_as_a_family_without_parents():
    pair = SiblingPairFactory()

    text = gedcom_export()

    assert f"0 @FS{pair.pk}@ FAM\n1 CHIL @I{pair.person_a_id}@\n1 CHIL @I{pair.person_b_id}@\n" in text
    assert f"1 FAMC @FS{pair.pk}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_source_with_its_files():
    source = SourceFactory(title="Taufbuch Mariazell", description="Pfarramt Mariazell\nBand 3")
    source_file = SourceFileFactory(source=source, file=f"sources/{source.pk}/7.pdf")

    text = gedcom_export()

    assert (
        f"0 @S{source.pk}@ SOUR\n1 TITL Taufbuch Mariazell\n1 TEXT Pfarramt Mariazell\n2 CONT Band 3\n"
        f"1 _ZWG_KIND parish_register\n1 OBJE\n2 FILE {source_file.file.name}\n3 FORM pdf\n"
    ) in text


@pytest.mark.django_db
def test_gedcom_export_writes_nothing_for_a_source_of_other_kind():
    source = SourceFactory(title="Brief", kind=Source.Kind.OTHER)

    text = gedcom_export()

    assert f"0 @S{source.pk}@ SOUR\n1 TITL Brief\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_points_at_the_sources_filed_with_a_person():
    lena = PersonFactory(given_names="", surname="")
    source = SourceFactory(people=[lena])

    text = gedcom_export()

    assert f"0 @I{lena.pk}@ INDI\n1 SEX U\n1 SOUR @S{source.pk}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_photo_with_what_it_shows_and_when():
    photo = PhotoFactory(description="Hochzeit am Hof", about_1950=True)

    text = gedcom_export()

    assert (
        f"0 @O{photo.pk}@ OBJE\n1 FILE {photo.file.name}\n2 FORM jpg\n2 TITL Hochzeit am Hof\n1 _DATE ABT 1950\n"
    ) in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_photo_nobody_described():
    photo = PhotoFactory()

    text = gedcom_export()

    assert f"0 @O{photo.pk}@ OBJE\n1 FILE {photo.file.name}\n2 FORM jpg\n0 " in text


@pytest.mark.django_db
def test_gedcom_export_points_at_the_photos_of_a_person_and_their_portrait():
    portrait = PhotoPersonFactory(person__given_names="", person__surname="", is_portrait=True)
    group_photo = PhotoPersonFactory(person=portrait.person)

    text = gedcom_export()

    assert f"1 OBJE @O{portrait.photo_id}@\n2 _PRIM Y\n1 OBJE @O{group_photo.photo_id}@\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_person():
    lena = PersonFactory(given_names="", surname="", gedcom_raw=RAW)

    text = gedcom_export()

    assert f"0 @I{lena.pk}@ INDI\n1 SEX U\n1 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_fact_and_its_citation():
    citation = CitationFactory(
        fact__as_value=True, fact__gedcom_raw=RAW, page="", gedcom_raw=[{"tag": "QUAY", "value": "3"}]
    )

    text = gedcom_export()

    assert f"1 OCCU Uhrmacher\n2 SOUR @S{citation.source_id}@\n3 QUAY 3\n2 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_birth():
    FactFactory(gedcom_raw=RAW)

    text = gedcom_export()

    assert "1 BIRT\n2 DATE 12 MAR 1931\n2 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_family():
    partnership = PartnershipFactory(kind=Partnership.Kind.UNKNOWN, gedcom_raw=RAW)

    text = gedcom_export()

    assert f"1 WIFE @I{partnership.person_b_id}@\n1 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_parent_link():
    link = ParentChildFactory(gedcom_raw=RAW)

    text = gedcom_export()

    assert f"1 FAMC @FP{link.parent_id}@\n2 PEDI birth\n2 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_siblings():
    pair = SiblingPairFactory(gedcom_raw=RAW)

    text = gedcom_export()

    assert f"1 CHIL @I{pair.person_b_id}@\n1 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_back_what_an_import_kept_of_a_source():
    source = SourceFactory(title="Brief", kind=Source.Kind.OTHER, gedcom_raw=RAW)

    text = gedcom_export()

    assert f"0 @S{source.pk}@ SOUR\n1 TITL Brief\n1 _UID 4F2A\n" in text


@pytest.mark.django_db
def test_gedcom_export_writes_a_birthplace_without_a_birth_date():
    FactFactory(as_value=True, kind=Fact.Kind.BIRTHPLACE, value="Mariazell")

    text = gedcom_export()

    assert "1 BIRT\n2 PLAC Mariazell\n" in text
