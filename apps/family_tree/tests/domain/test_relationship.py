import pytest

from apps.family_tree.domain.relationship import FamilyGraph, relationship_name

# An invented family around Lena, by id. Two people are a couple in PARTNERSHIPS, a child of the two in
# PARENT_CHILD, and Anna's sister Rosa is an explicit sibling whose parents nobody knows.
LENA = 1
THOMAS, MARIA = 2, 3  # Lena's parents
JOSEF, ANNA = 4, 5  # Thomas's parents
JOHANN, THERESIA = 6, 7  # Josef's parents
FRANZ = 8  # Johann's father
PAUL, EVA, KIM = 9, 10, 11  # Lena's siblings
FELIX, SOPHIE = 12, 13  # Paul's children
MIA = 14  # Sophie's daughter
NOAH = 15  # Mia's son
MAX, CLARA, ALEX = 16, 17, 18  # Lena's children
BEN = 19  # Max's son
EMIL = 20  # Ben's son
LEO = 21  # Emil's son
GEORG, HILDE = 22, 23  # Thomas's siblings
KARL = 24  # Josef's brother
ALOIS = 25  # Johann's brother
JONAS, LAURA = 26, 27  # Georg's children
TIM = 28  # Laura's son
WERNER = 29  # Karl's son
JULIA = 30  # Werner's daughter
ALOIS_SON, ALOIS_GRANDSON, ALOIS_GREAT_GRANDSON = 31, 32, 33
STEFAN = 40  # Lena's husband
RUDOLF, GERDA = 41, 42  # Stefan's parents
MARTIN = 43  # Stefan's brother
TOBIAS = 44  # Stefan's son from before
LUKAS = 45  # Martin's son
OTTO = 46  # Rudolf's father
SANDRA = 47  # Max's wife
JAN = 48  # Clara's partner
PETRA = 49  # Paul's wife
INGRID = 50  # Georg's wife
NINA = 51  # Felix's wife
WALTER = 52  # Maria's later partner
LISA = 53  # Ben's wife
CARINA = 54  # Jonas's wife
ROSA = 55  # Anna's sister, parents unknown
HANS = 56  # Rosa's son
MORITZ = 57  # Hans's son
VIKTOR = 60  # in the tree, related to nobody

MEN = (THOMAS, JOSEF, JOHANN, FRANZ, PAUL, FELIX, NOAH, MAX, BEN, EMIL, LEO, GEORG, KARL, ALOIS, JONAS, TIM)
MORE_MEN = (WERNER, ALOIS_SON, ALOIS_GRANDSON, ALOIS_GREAT_GRANDSON, STEFAN, RUDOLF, MARTIN, TOBIAS, LUKAS, OTTO)
WOMEN = (LENA, MARIA, ANNA, THERESIA, EVA, SOPHIE, MIA, CLARA, HILDE, LAURA, JULIA, GERDA, SANDRA, PETRA, INGRID)
MORE_WOMEN = (NINA, LISA, CARINA, ROSA)

FAMILY = FamilyGraph.from_links(
    sex=dict.fromkeys((*MEN, *MORE_MEN, JAN, WALTER, HANS, MORITZ), "M")
    | dict.fromkeys((*WOMEN, *MORE_WOMEN), "F")
    | {KIM: "X", ALEX: "U", VIKTOR: "U"},
    parent_child=[
        (THOMAS, LENA),
        (MARIA, LENA),
        (JOSEF, THOMAS),
        (ANNA, THOMAS),
        (JOHANN, JOSEF),
        (THERESIA, JOSEF),
        (FRANZ, JOHANN),
        (THOMAS, PAUL),
        (MARIA, PAUL),
        (THOMAS, EVA),
        (MARIA, KIM),
        (PAUL, FELIX),
        (PAUL, SOPHIE),
        (SOPHIE, MIA),
        (MIA, NOAH),
        (LENA, MAX),
        (STEFAN, MAX),
        (LENA, CLARA),
        (LENA, ALEX),
        (MAX, BEN),
        (BEN, EMIL),
        (EMIL, LEO),
        (JOSEF, GEORG),
        (ANNA, HILDE),
        (JOHANN, KARL),
        (FRANZ, ALOIS),
        (GEORG, JONAS),
        (GEORG, LAURA),
        (LAURA, TIM),
        (KARL, WERNER),
        (WERNER, JULIA),
        (ALOIS, ALOIS_SON),
        (ALOIS_SON, ALOIS_GRANDSON),
        (ALOIS_GRANDSON, ALOIS_GREAT_GRANDSON),
        (RUDOLF, STEFAN),
        (GERDA, STEFAN),
        (RUDOLF, MARTIN),
        (STEFAN, TOBIAS),
        (MARTIN, LUKAS),
        (OTTO, RUDOLF),
        (ROSA, HANS),
        (HANS, MORITZ),
    ],
    partnerships=[
        (THOMAS, MARIA, True),
        (LENA, STEFAN, True),
        (RUDOLF, GERDA, True),
        (MAX, SANDRA, True),
        (CLARA, JAN, False),
        (PAUL, PETRA, True),
        (INGRID, GEORG, True),
        (FELIX, NINA, True),
        (MARIA, WALTER, False),
        (BEN, LISA, True),
        (JONAS, CARINA, True),
    ],
    sibling_pairs=[(ROSA, ANNA)],
)


def test_relationship_name_of_the_home_person_is_ausgangsperson():
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=LENA) == "Ausgangsperson"


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (THOMAS, "Vater"),
        (MARIA, "Mutter"),
        (JOSEF, "Großvater"),
        (ANNA, "Großmutter"),
        (JOHANN, "Urgroßvater"),
        (THERESIA, "Urgroßmutter"),
        (FRANZ, "Ururgroßvater"),
    ],
)
def test_relationship_name_of_an_ancestor(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (MAX, "Sohn"),
        (CLARA, "Tochter"),
        (ALEX, "Kind"),
        (BEN, "Enkel"),
        (EMIL, "Urenkel"),
        (LEO, "Ururenkel"),
    ],
)
def test_relationship_name_of_a_descendant(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (PAUL, "Bruder"),
        (EVA, "Schwester"),  # through her father only
        (KIM, "Geschwister"),  # through their mother only
    ],
)
def test_relationship_name_of_a_sibling(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (FELIX, "Neffe"),
        (SOPHIE, "Nichte"),
        (MIA, "Großnichte"),
        (NOAH, "Urgroßneffe"),
    ],
)
def test_relationship_name_of_a_siblings_descendant(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (GEORG, "Onkel"),
        (HILDE, "Tante"),
        (KARL, "Großonkel"),
        (ROSA, "Großtante"),  # an explicit sibling of Anna, parents unknown
        (ALOIS, "Urgroßonkel"),
    ],
)
def test_relationship_name_of_an_ancestors_sibling(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (JONAS, "Cousin"),
        (LAURA, "Cousine"),
        (JULIA, "Cousine 2. Grades"),
        (MORITZ, "Cousin 2. Grades"),  # through Anna's explicit sister
        (ALOIS_GREAT_GRANDSON, "Cousin 3. Grades"),
    ],
)
def test_relationship_name_of_a_cousin(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize("person_id", [TIM, WERNER, HANS])
def test_relationship_name_of_a_cousin_of_another_generation_is_verwandt(person_id):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == "verwandt"


def test_relationship_name_of_the_husband():
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=STEFAN) == "Ehemann"


def test_relationship_name_of_the_wife():
    assert relationship_name(family=FAMILY, home_id=STEFAN, person_id=LENA) == "Ehefrau"


def test_relationship_name_of_an_unmarried_partner():
    assert relationship_name(family=FAMILY, home_id=CLARA, person_id=JAN) == "Partner"


def test_relationship_name_of_an_unmarried_partner_who_is_a_woman():
    assert relationship_name(family=FAMILY, home_id=JAN, person_id=CLARA) == "Partnerin"


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (SANDRA, "Schwiegertochter"),
        (JAN, "Schwiegersohn"),
        (WALTER, "Stiefvater"),
        (PETRA, "Schwägerin"),
        (INGRID, "Tante"),
        (NINA, "Nichte"),
    ],
)
def test_relationship_name_of_a_blood_relatives_partner(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (RUDOLF, "Schwiegervater"),
        (GERDA, "Schwiegermutter"),
        (TOBIAS, "Stiefsohn"),
        (MARTIN, "Schwager"),
        (LUKAS, "Neffe"),
    ],
)
def test_relationship_name_of_a_partners_blood_relative(person_id, expected):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == expected


@pytest.mark.parametrize("person_id", [LISA, CARINA, OTTO])
def test_relationship_name_by_marriage_without_a_word_is_verwandt(person_id):
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=person_id) == "verwandt"


def test_relationship_name_of_someone_not_connected_is_none():
    assert relationship_name(family=FAMILY, home_id=LENA, person_id=VIKTOR) is None


# Everyone below is of unknown sex, so each takes the neutral word.
UNKNOWN_HOME, UNKNOWN_PARENT, UNKNOWN_GRANDPARENT, UNKNOWN_CHILD, UNKNOWN_GRANDCHILD = 1, 2, 3, 4, 5
UNKNOWN_SIBLING, UNKNOWN_NIBLING, UNKNOWN_PIBLING, UNKNOWN_COUSIN = 6, 7, 8, 9
UNKNOWN_SPOUSE, UNKNOWN_PARTNER, UNKNOWN_SPOUSES_PARENT, UNKNOWN_SPOUSES_CHILD = 10, 11, 12, 13
UNKNOWN_CHILDS_PARTNER, UNKNOWN_PARENTS_PARTNER, UNKNOWN_SIBLINGS_PARTNER = 14, 15, 16

NEUTRAL = FamilyGraph.from_links(
    sex={},
    parent_child=[
        (UNKNOWN_PARENT, UNKNOWN_HOME),
        (UNKNOWN_GRANDPARENT, UNKNOWN_PARENT),
        (UNKNOWN_HOME, UNKNOWN_CHILD),
        (UNKNOWN_CHILD, UNKNOWN_GRANDCHILD),
        (UNKNOWN_PARENT, UNKNOWN_SIBLING),
        (UNKNOWN_SIBLING, UNKNOWN_NIBLING),
        (UNKNOWN_GRANDPARENT, UNKNOWN_PIBLING),
        (UNKNOWN_PIBLING, UNKNOWN_COUSIN),
        (UNKNOWN_SPOUSES_PARENT, UNKNOWN_SPOUSE),
        (UNKNOWN_SPOUSE, UNKNOWN_SPOUSES_CHILD),
    ],
    partnerships=[
        (UNKNOWN_HOME, UNKNOWN_SPOUSE, True),
        (UNKNOWN_HOME, UNKNOWN_PARTNER, False),
        (UNKNOWN_CHILD, UNKNOWN_CHILDS_PARTNER, False),
        (UNKNOWN_PARENT, UNKNOWN_PARENTS_PARTNER, False),
        (UNKNOWN_SIBLING, UNKNOWN_SIBLINGS_PARTNER, False),
    ],
    sibling_pairs=[],
)


@pytest.mark.parametrize(
    ("person_id", "expected"),
    [
        (UNKNOWN_PARENT, "Elternteil"),
        (UNKNOWN_GRANDPARENT, "Großelternteil"),
        (UNKNOWN_CHILD, "Kind"),
        (UNKNOWN_GRANDCHILD, "Enkelkind"),
        (UNKNOWN_SIBLING, "Geschwister"),
        (UNKNOWN_NIBLING, "Neffe oder Nichte"),
        (UNKNOWN_PIBLING, "Onkel oder Tante"),
        (UNKNOWN_COUSIN, "Cousin oder Cousine"),
        (UNKNOWN_SPOUSE, "Ehepartner"),
        (UNKNOWN_PARTNER, "Partner oder Partnerin"),
        (UNKNOWN_SPOUSES_PARENT, "Schwiegerelternteil"),
        (UNKNOWN_SPOUSES_CHILD, "Stiefkind"),
        (UNKNOWN_CHILDS_PARTNER, "Schwiegerkind"),
        (UNKNOWN_PARENTS_PARTNER, "Stiefelternteil"),
        (UNKNOWN_SIBLINGS_PARTNER, "Schwager oder Schwägerin"),
    ],
)
def test_relationship_name_without_a_known_sex_is_neutral(person_id, expected):
    assert relationship_name(family=NEUTRAL, home_id=UNKNOWN_HOME, person_id=person_id) == expected


def test_relationship_name_counts_an_ancestor_reached_twice_once():
    """
    The parents are siblings, so the grandparent is an ancestor through both of them.
    """
    graph = FamilyGraph.from_links(
        sex={}, parent_child=[(1, 2), (1, 3), (2, 4), (3, 4)], partnerships=[], sibling_pairs=[]
    )

    assert relationship_name(family=graph, home_id=4, person_id=1) == "Großelternteil"


def test_from_links_joins_explicit_siblings_into_one_group():
    graph = FamilyGraph.from_links(sex={}, parent_child=[], partnerships=[], sibling_pairs=[(1, 2), (3, 4), (2, 3)])

    group = frozenset((1, 2, 3, 4))
    assert graph.parents == {1: {group}, 2: {group}, 3: {group}, 4: {group}}
