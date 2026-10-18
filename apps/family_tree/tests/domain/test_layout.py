import datetime
import zlib

from apps.family_tree.domain.layout import (
    BAR_STEP,
    CARD_HEIGHT,
    CARD_WIDTH,
    PARTNER_GAP,
    PARTNER_STEP,
    ROW_GAP,
    SIBLING_GAP,
    Card,
    LayoutPerson,
    Line,
    LineKind,
    ParentLink,
    PartnerLink,
    Placeholder,
    SiblingLink,
    TreeLayout,
    layout,
)
from apps.family_tree.domain.stroke import pen_stroke

ROW = CARD_HEIGHT + ROW_GAP


def test_layout_without_a_home_person_is_empty():
    result = layout(
        people=[LayoutPerson(id=1)], partnerships=[], parent_links=[], sibling_links=[], home_person_id=None
    )

    assert result == TreeLayout()


def test_layout_around_someone_not_among_the_people_is_empty():
    result = layout(people=[LayoutPerson(id=1)], partnerships=[], parent_links=[], sibling_links=[], home_person_id=9)

    assert result == TreeLayout()


def test_layout_of_one_person_is_one_card():
    result = layout(people=[LayoutPerson(id=1)], partnerships=[], parent_links=[], sibling_links=[], home_person_id=1)

    assert result == TreeLayout(
        cards=(Card(person_id=1, x=0, y=0, generation=0),), width=CARD_WIDTH, height=CARD_HEIGHT
    )


def test_layout_leaves_out_who_is_not_connected_to_the_home_person():
    lena, fremd, fremde = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=lena), LayoutPerson(id=fremd), LayoutPerson(id=fremde)],
        partnerships=[PartnerLink(person_a=fremd, person_b=fremde)],
        parent_links=[],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (Card(person_id=lena, x=0, y=0, generation=0),)


def test_layout_puts_parents_a_row_above_and_children_a_row_below():
    johann, lena, emma = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=johann), LayoutPerson(id=lena), LayoutPerson(id=emma)],
        partnerships=[],
        parent_links=[ParentLink(parent=johann, child=lena), ParentLink(parent=lena, child=emma)],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=johann, x=0, y=0, generation=-1),
        Card(person_id=lena, x=0, y=ROW, generation=0),
        Card(person_id=emma, x=0, y=2 * ROW, generation=1),
    )


def test_layout_puts_partners_and_siblings_without_known_parents_in_the_same_row():
    lena, markus, katharina = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=lena), LayoutPerson(id=markus), LayoutPerson(id=katharina)],
        partnerships=[PartnerLink(person_a=lena, person_b=markus)],
        parent_links=[],
        sibling_links=[SiblingLink(person_a=katharina, person_b=lena)],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=lena, x=0, y=ROW, generation=0),
        Card(person_id=markus, x=164, y=ROW, generation=0),
        Card(person_id=katharina, x=336, y=ROW, generation=0),
    )


def test_layout_centres_a_couple_over_their_child():
    johann, maria, lena = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=johann), LayoutPerson(id=maria), LayoutPerson(id=lena)],
        partnerships=[PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[ParentLink(parent=johann, child=lena), ParentLink(parent=maria, child=lena)],
        sibling_links=[],
        home_person_id=lena,
    )

    couple_middle = (2 * CARD_WIDTH + PARTNER_GAP) // 2
    assert result.cards == (
        Card(person_id=johann, x=0, y=0, generation=-1),
        Card(person_id=maria, x=CARD_WIDTH + PARTNER_GAP, y=0, generation=-1),
        Card(person_id=lena, x=couple_middle - CARD_WIDTH // 2, y=ROW, generation=0),
    )
    assert (result.width, result.height) == (2 * CARD_WIDTH + PARTNER_GAP, ROW + CARD_HEIGHT)


def test_layout_orders_siblings_by_birth_with_the_undated_last():
    johann, maria = 1, 2
    matthias, florian, lena, lukas = 3, 4, 5, 6

    result = layout(
        people=[
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=matthias, birth=datetime.date(1990, 5, 1)),
            LayoutPerson(id=florian),
            LayoutPerson(id=lena, birth=datetime.date(1987, 2, 3)),
            LayoutPerson(id=lukas),
        ],
        partnerships=[PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[
            ParentLink(parent=johann, child=matthias),
            ParentLink(parent=maria, child=matthias),
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=maria, child=florian),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
            ParentLink(parent=johann, child=lukas),
            ParentLink(parent=maria, child=lukas),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards[2:] == (
        Card(person_id=lena, x=0, y=ROW, generation=0),
        Card(person_id=matthias, x=172, y=ROW, generation=0),
        Card(person_id=florian, x=344, y=ROW, generation=0),
        Card(person_id=lukas, x=516, y=ROW, generation=0),
    )


def test_layout_keeps_a_half_sibling_beside_the_couples_children_not_among_them():
    johann, maria = 1, 2
    florian, lukas, lena = 3, 4, 5

    result = layout(
        people=[
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=florian),
            LayoutPerson(id=lukas),
            LayoutPerson(id=lena),
        ],
        partnerships=[PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=johann, child=lukas),
            ParentLink(parent=maria, child=lukas),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards[2:] == (
        Card(person_id=florian, x=0, y=ROW, generation=0),
        Card(person_id=lukas, x=204, y=ROW, generation=0),
        Card(person_id=lena, x=376, y=ROW, generation=0),
    )


def test_layout_puts_aunts_and_uncles_in_the_row_of_their_sibling():
    josef, theresia, johann, maria, franz, lena = 1, 2, 3, 4, 5, 6

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=theresia),
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=franz),
            LayoutPerson(id=lena),
        ],
        partnerships=[PartnerLink(person_a=josef, person_b=theresia), PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=theresia, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=theresia, child=franz),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards[2:5] == (
        Card(person_id=johann, x=0, y=ROW, generation=-1),
        Card(person_id=maria, x=164, y=ROW, generation=-1),
        Card(person_id=franz, x=336, y=ROW, generation=-1),
    )


def test_layout_hangs_siblings_without_known_parents_under_a_placeholder():
    katharina, stefan, vroni = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=katharina), LayoutPerson(id=stefan), LayoutPerson(id=vroni)],
        partnerships=[],
        parent_links=[],
        sibling_links=[
            SiblingLink(person_a=katharina, person_b=stefan),
            SiblingLink(person_a=stefan, person_b=vroni),
        ],
        home_person_id=katharina,
    )

    assert result.placeholders == (Placeholder(sibling_ids=(katharina, stefan, vroni), x=172, y=0, generation=-1),)
    assert result.cards[1] == Card(person_id=stefan, x=172, y=ROW, generation=0)


def test_layout_gives_one_sibling_without_known_parents_no_placeholder():
    franz, katharina, stefan = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=franz), LayoutPerson(id=katharina), LayoutPerson(id=stefan)],
        partnerships=[],
        parent_links=[ParentLink(parent=franz, child=katharina)],
        sibling_links=[SiblingLink(person_a=katharina, person_b=stefan)],
        home_person_id=katharina,
    )

    assert result.placeholders == ()


def test_layout_stands_two_parents_of_a_child_together_without_a_partner_line():
    johann, maria, lena = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=johann), LayoutPerson(id=maria), LayoutPerson(id=lena)],
        partnerships=[],
        parent_links=[ParentLink(parent=johann, child=lena), ParentLink(parent=maria, child=lena)],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards[:2] == (
        Card(person_id=johann, x=0, y=0, generation=-1),
        Card(person_id=maria, x=CARD_WIDTH + PARTNER_GAP, y=0, generation=-1),
    )
    assert len(result.lines) == 1
    assert result.lines[0].kind == LineKind.CHILDREN


def test_layout_stands_someone_with_two_partners_between_them():
    anton, lena, markus = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=anton), LayoutPerson(id=lena), LayoutPerson(id=markus)],
        partnerships=[PartnerLink(person_a=lena, person_b=anton), PartnerLink(person_a=lena, person_b=markus)],
        parent_links=[],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=anton, x=0, y=0, generation=0),
        Card(person_id=lena, x=164, y=0, generation=0),
        Card(person_id=markus, x=328, y=0, generation=0),
    )
    assert len(result.lines) == 2
    assert result.lines[1].kind == LineKind.PARTNERS


def test_layout_hangs_the_children_of_each_marriage_under_their_own_couple():
    johann, hilde, maria = 1, 2, 3
    florian, lena, lukas = 4, 5, 6

    result = layout(
        people=[
            LayoutPerson(id=johann),
            LayoutPerson(id=hilde),
            LayoutPerson(id=maria),
            LayoutPerson(id=florian),
            LayoutPerson(id=lena),
            LayoutPerson(id=lukas),
        ],
        partnerships=[PartnerLink(person_a=johann, person_b=hilde), PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=hilde, child=florian),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
            ParentLink(parent=johann, child=lukas),
            ParentLink(parent=maria, child=lukas),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=hilde, x=29, y=0, generation=-1),
        Card(person_id=johann, x=193, y=0, generation=-1),
        Card(person_id=maria, x=357, y=0, generation=-1),
        Card(person_id=florian, x=0, y=ROW, generation=0),
        Card(person_id=lena, x=204, y=ROW, generation=0),
        Card(person_id=lukas, x=376, y=ROW, generation=0),
    )


def test_layout_draws_the_line_to_a_first_marriages_child_from_between_that_couple():
    johann, hilde, maria, florian, lena = 1, 2, 3, 4, 5

    result = layout(
        people=[
            LayoutPerson(id=johann),
            LayoutPerson(id=hilde),
            LayoutPerson(id=maria),
            LayoutPerson(id=florian),
            LayoutPerson(id=lena),
        ],
        partnerships=[PartnerLink(person_a=johann, person_b=hilde), PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=hilde, child=florian),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    hilde_card, johann_card, _, florian_card, _ = result.cards
    middle = (hilde_card.x + CARD_WIDTH + johann_card.x) / 2
    child = florian_card.x + CARD_WIDTH / 2
    bar = ROW - ROW_GAP / 2
    assert (
        Line(
            kind=LineKind.CHILDREN,
            path=pen_stroke(
                segments=[
                    ((middle, CARD_HEIGHT / 2), (middle, bar)),
                    ((child, bar), (middle, bar)),
                    ((child, bar), (child, ROW)),
                ],
                seed=zlib.crc32(b"children-1-2"),
            ),
        )
        in result.lines
    )


def test_layout_runs_the_line_to_a_third_partner_lower_behind_the_second():
    johann, hilde, maria, rosa = 1, 2, 3, 4

    result = layout(
        people=[LayoutPerson(id=johann), LayoutPerson(id=hilde), LayoutPerson(id=maria), LayoutPerson(id=rosa)],
        partnerships=[
            PartnerLink(person_a=johann, person_b=hilde),
            PartnerLink(person_a=johann, person_b=maria),
            PartnerLink(person_a=johann, person_b=rosa),
        ],
        parent_links=[],
        sibling_links=[],
        home_person_id=johann,
    )

    johann_right = 2 * CARD_WIDTH + PARTNER_GAP
    lower = CARD_HEIGHT / 2 + PARTNER_STEP
    assert result.lines[2] == Line(
        kind=LineKind.PARTNERS,
        path=pen_stroke(
            segments=[((johann_right, lower), (johann_right + 2 * PARTNER_GAP + CARD_WIDTH, lower))],
            seed=zlib.crc32(b"partners-1-4"),
        ),
    )


def test_layout_lines_up_a_chain_of_partners():
    anton, lena, markus, vroni = 1, 2, 3, 4

    result = layout(
        people=[LayoutPerson(id=anton), LayoutPerson(id=lena), LayoutPerson(id=markus), LayoutPerson(id=vroni)],
        partnerships=[
            PartnerLink(person_a=anton, person_b=lena),
            PartnerLink(person_a=lena, person_b=markus),
            PartnerLink(person_a=markus, person_b=vroni),
        ],
        parent_links=[],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=anton, x=0, y=0, generation=0),
        Card(person_id=lena, x=164, y=0, generation=0),
        Card(person_id=markus, x=328, y=0, generation=0),
        Card(person_id=vroni, x=492, y=0, generation=0),
    )


def test_layout_keeps_a_niece_who_married_her_uncle_a_row_below_her_father():
    josef, johann, franz, anna, emma = 1, 2, 3, 4, 5

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=johann),
            LayoutPerson(id=franz),
            LayoutPerson(id=anna),
            LayoutPerson(id=emma),
        ],
        partnerships=[PartnerLink(person_a=franz, person_b=anna)],
        parent_links=[
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=johann, child=anna),
            ParentLink(parent=franz, child=emma),
            ParentLink(parent=anna, child=emma),
        ],
        sibling_links=[],
        home_person_id=johann,
    )

    assert result.cards == (
        Card(person_id=josef, x=82, y=0, generation=-1),
        Card(person_id=johann, x=0, y=ROW, generation=0),
        Card(person_id=anna, x=0, y=2 * ROW, generation=1),
        Card(person_id=franz, x=164, y=2 * ROW, generation=1),
        Card(person_id=emma, x=82, y=3 * ROW, generation=2),
    )


def test_layout_moves_a_child_below_both_parents_when_they_stand_in_two_rows():
    josef, johann, franz, anna, emma = 1, 2, 3, 4, 5

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=johann),
            LayoutPerson(id=franz),
            LayoutPerson(id=anna),
            LayoutPerson(id=emma),
        ],
        partnerships=[],
        parent_links=[
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=johann, child=anna),
            ParentLink(parent=franz, child=emma),
            ParentLink(parent=anna, child=emma),
        ],
        sibling_links=[],
        home_person_id=josef,
    )

    assert result.cards == (
        Card(person_id=josef, x=82, y=0, generation=0),
        Card(person_id=johann, x=164, y=ROW, generation=1),
        Card(person_id=franz, x=0, y=2 * ROW, generation=2),
        Card(person_id=anna, x=164, y=2 * ROW, generation=2),
        Card(person_id=emma, x=82, y=3 * ROW, generation=3),
    )


def test_layout_puts_an_ancestor_above_both_lines_of_different_length_that_meet_in_them():
    """
    Ahnenschwund over a different number of generations: Josef is Lena's grandfather through her mother and her
    great-grandfather through her father. He stands above his son Alois, and the line to his daughter Maria
    crosses Alois's row.
    """
    josef, theresia, alois, rosa, maria, johann, lena = 1, 2, 3, 4, 5, 6, 7

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=theresia),
            LayoutPerson(id=alois),
            LayoutPerson(id=rosa),
            LayoutPerson(id=maria),
            LayoutPerson(id=johann),
            LayoutPerson(id=lena),
        ],
        partnerships=[
            PartnerLink(person_a=josef, person_b=theresia),
            PartnerLink(person_a=alois, person_b=rosa),
            PartnerLink(person_a=johann, person_b=maria),
        ],
        parent_links=[
            ParentLink(parent=josef, child=maria),
            ParentLink(parent=theresia, child=maria),
            ParentLink(parent=josef, child=alois),
            ParentLink(parent=theresia, child=alois),
            ParentLink(parent=alois, child=johann),
            ParentLink(parent=rosa, child=johann),
            ParentLink(parent=maria, child=lena),
            ParentLink(parent=johann, child=lena),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=josef, x=0, y=0, generation=-3, pedigree_collapse=True),
        Card(person_id=theresia, x=164, y=0, generation=-3, pedigree_collapse=True),
        Card(person_id=alois, x=123, y=ROW, generation=-2),
        Card(person_id=rosa, x=287, y=ROW, generation=-2),
        Card(person_id=maria, x=41, y=2 * ROW, generation=-1),
        Card(person_id=johann, x=205, y=2 * ROW, generation=-1),
        Card(person_id=lena, x=123, y=3 * ROW, generation=0),
    )


def test_layout_draws_a_stepped_line_between_partners_who_cannot_share_a_row():
    franz, josef, johann, anna = 1, 2, 3, 4

    result = layout(
        people=[LayoutPerson(id=franz), LayoutPerson(id=josef), LayoutPerson(id=johann), LayoutPerson(id=anna)],
        partnerships=[PartnerLink(person_a=franz, person_b=anna)],
        parent_links=[
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=johann, child=anna),
        ],
        sibling_links=[],
        home_person_id=franz,
    )

    assert result.cards[1:] == (
        Card(person_id=franz, x=0, y=ROW, generation=0),
        Card(person_id=johann, x=172, y=ROW, generation=0),
        Card(person_id=anna, x=172, y=2 * ROW, generation=1),
    )
    out, across, into = CARD_WIDTH + PARTNER_GAP / 2, 2 * ROW - ROW_GAP / 4, 172 - PARTNER_GAP / 2
    upper, lower = ROW + CARD_HEIGHT / 2, 2 * ROW + CARD_HEIGHT / 2
    assert result.lines[0] == Line(
        kind=LineKind.PARTNERS,
        path=pen_stroke(
            segments=[
                ((CARD_WIDTH, upper), (out, upper)),
                ((out, upper), (out, across)),
                ((out, across), (into, across)),
                ((into, across), (into, lower)),
                ((into, lower), (172, lower)),
            ],
            seed=zlib.crc32(b"partners-1-4"),
        ),
    )


def test_layout_steps_a_line_to_a_partner_to_the_left_out_of_the_left_side():
    josef, johann, franz, anna = 1, 2, 3, 4

    result = layout(
        people=[LayoutPerson(id=josef), LayoutPerson(id=johann), LayoutPerson(id=franz), LayoutPerson(id=anna)],
        partnerships=[PartnerLink(person_a=franz, person_b=anna)],
        parent_links=[
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=johann, child=anna),
        ],
        sibling_links=[],
        home_person_id=franz,
    )

    assert result.cards[2] == Card(person_id=franz, x=172, y=ROW, generation=0)
    assert result.lines[0].path.startswith("M 172 ")


def test_layout_hangs_the_children_of_partners_in_two_rows_from_their_stepped_line():
    josef, johann, franz, anna, emma, vroni = 1, 2, 3, 4, 5, 6

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=johann),
            LayoutPerson(id=franz),
            LayoutPerson(id=anna),
            LayoutPerson(id=emma),
            LayoutPerson(id=vroni),
        ],
        partnerships=[PartnerLink(person_a=franz, person_b=anna)],
        parent_links=[
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=johann, child=anna),
            ParentLink(parent=franz, child=emma),
            ParentLink(parent=anna, child=emma),
            ParentLink(parent=franz, child=vroni),
        ],
        sibling_links=[],
        home_person_id=johann,
    )

    _, _, _, anna_card, _, emma_card = result.cards
    hook = (anna_card.x + CARD_WIDTH + PARTNER_GAP / 2, anna_card.y + CARD_HEIGHT / 2)
    bar = emma_card.y - ROW_GAP / 2
    child = emma_card.x + CARD_WIDTH / 2
    assert (anna_card.person_id, emma_card.person_id) == (anna, emma)
    assert (
        Line(
            kind=LineKind.CHILDREN,
            path=pen_stroke(
                segments=[
                    (hook, (hook[0], bar)),
                    ((child, bar), (hook[0], bar)),
                    ((child, bar), (child, emma_card.y)),
                ],
                seed=zlib.crc32(b"children-3-4"),
            ),
        )
        in result.lines
    )


def test_layout_stops_on_a_cycle_of_parents():
    anton, berta = 1, 2

    result = layout(
        people=[LayoutPerson(id=anton), LayoutPerson(id=berta)],
        partnerships=[],
        parent_links=[ParentLink(parent=anton, child=berta), ParentLink(parent=berta, child=anton)],
        sibling_links=[],
        home_person_id=anton,
    )

    assert result.cards == (
        Card(person_id=berta, x=0, y=0, generation=-5),
        Card(person_id=anton, x=0, y=ROW, generation=-4),
    )


def test_layout_marks_the_ancestors_in_whom_two_lines_of_the_home_person_meet():
    """
    Anna and Bernd are cousins and married: their grandparents Josef and Theresia are Emma's great-grandparents
    twice. Josef's father Alois is reached the same two ways, but the lines meet in Josef.
    """
    alois, josef, theresia, johann, maria, franz, rosa, anna, bernd, emma = range(1, 11)

    result = layout(
        people=[
            LayoutPerson(id=alois),
            LayoutPerson(id=josef),
            LayoutPerson(id=theresia),
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=franz),
            LayoutPerson(id=rosa),
            LayoutPerson(id=anna),
            LayoutPerson(id=bernd),
            LayoutPerson(id=emma),
        ],
        partnerships=[
            PartnerLink(person_a=josef, person_b=theresia),
            PartnerLink(person_a=johann, person_b=maria),
            PartnerLink(person_a=franz, person_b=rosa),
            PartnerLink(person_a=anna, person_b=bernd),
        ],
        parent_links=[
            ParentLink(parent=alois, child=josef),
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=theresia, child=johann),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=theresia, child=franz),
            ParentLink(parent=johann, child=anna),
            ParentLink(parent=maria, child=anna),
            ParentLink(parent=franz, child=bernd),
            ParentLink(parent=rosa, child=bernd),
            ParentLink(parent=anna, child=emma),
            ParentLink(parent=bernd, child=emma),
        ],
        sibling_links=[],
        home_person_id=emma,
    )

    assert result.cards[:3] == (
        Card(person_id=alois, x=86, y=0, generation=-4),
        Card(person_id=josef, x=86, y=ROW, generation=-3, pedigree_collapse=True),
        Card(person_id=theresia, x=250, y=ROW, generation=-3, pedigree_collapse=True),
    )


def test_layout_turns_a_couple_towards_the_side_of_each_ones_parents():
    johann, maria, alois, rosa = 1, 2, 3, 4
    lena, markus, lukas, florian, matthias = 5, 6, 7, 8, 9

    result = layout(
        people=[
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=alois),
            LayoutPerson(id=rosa),
            LayoutPerson(id=lena, birth=datetime.date(1980, 1, 1)),
            LayoutPerson(id=markus),
            LayoutPerson(id=lukas, birth=datetime.date(1982, 1, 1)),
            LayoutPerson(id=florian, birth=datetime.date(1984, 1, 1)),
            LayoutPerson(id=matthias, birth=datetime.date(1986, 1, 1)),
        ],
        partnerships=[
            PartnerLink(person_a=johann, person_b=maria),
            PartnerLink(person_a=alois, person_b=rosa),
            PartnerLink(person_a=lena, person_b=markus),
        ],
        parent_links=[
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
            ParentLink(parent=johann, child=lukas),
            ParentLink(parent=maria, child=lukas),
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=maria, child=florian),
            ParentLink(parent=johann, child=matthias),
            ParentLink(parent=maria, child=matthias),
            ParentLink(parent=alois, child=markus),
            ParentLink(parent=rosa, child=markus),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=alois, x=0, y=0, generation=-1),
        Card(person_id=rosa, x=164, y=0, generation=-1),
        Card(person_id=johann, x=422, y=0, generation=-1),
        Card(person_id=maria, x=586, y=0, generation=-1),
        Card(person_id=markus, x=82, y=ROW, generation=0),
        Card(person_id=lena, x=246, y=ROW, generation=0),
        Card(person_id=lukas, x=418, y=ROW, generation=0),
        Card(person_id=florian, x=590, y=ROW, generation=0),
        Card(person_id=matthias, x=762, y=ROW, generation=0),
    )


def test_layout_keeps_a_couple_of_two_siblings_in_their_order():
    josef, johann, gertrud = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=josef), LayoutPerson(id=johann), LayoutPerson(id=gertrud)],
        partnerships=[PartnerLink(person_a=gertrud, person_b=johann)],
        parent_links=[ParentLink(parent=josef, child=johann), ParentLink(parent=josef, child=gertrud)],
        sibling_links=[],
        home_person_id=johann,
    )

    assert result.cards[1:] == (
        Card(person_id=johann, x=0, y=ROW, generation=0),
        Card(person_id=gertrud, x=164, y=ROW, generation=0),
    )


def test_layout_draws_the_partner_line_seeded_by_the_couple():
    lena, markus = 1, 2

    result = layout(
        people=[LayoutPerson(id=lena), LayoutPerson(id=markus)],
        partnerships=[PartnerLink(person_a=markus, person_b=lena)],
        parent_links=[],
        sibling_links=[],
        home_person_id=lena,
    )

    middle = CARD_HEIGHT / 2
    assert result.lines == (
        Line(
            kind=LineKind.PARTNERS,
            path=pen_stroke(
                segments=[((CARD_WIDTH, middle), (CARD_WIDTH + PARTNER_GAP, middle))],
                seed=zlib.crc32(b"partners-1-2"),
            ),
        ),
    )


def test_layout_draws_the_line_to_an_only_child_from_the_middle_of_the_couple():
    johann, maria, lena = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=johann), LayoutPerson(id=maria), LayoutPerson(id=lena)],
        partnerships=[PartnerLink(person_a=johann, person_b=maria)],
        parent_links=[ParentLink(parent=johann, child=lena), ParentLink(parent=maria, child=lena)],
        sibling_links=[],
        home_person_id=lena,
    )

    middle = CARD_WIDTH + PARTNER_GAP / 2
    bar = ROW - ROW_GAP / 2
    assert result.lines[1] == Line(
        kind=LineKind.CHILDREN,
        path=pen_stroke(
            segments=[((middle, CARD_HEIGHT / 2), (middle, bar)), ((middle, bar), (middle, ROW))],
            seed=zlib.crc32(b"children-1-2"),
        ),
    )


def test_layout_draws_a_single_parents_line_from_their_card_with_the_bar_a_step_higher():
    franz, katharina, stefan = 1, 2, 3

    result = layout(
        people=[LayoutPerson(id=franz), LayoutPerson(id=katharina), LayoutPerson(id=stefan)],
        partnerships=[],
        parent_links=[ParentLink(parent=franz, child=katharina), ParentLink(parent=franz, child=stefan)],
        sibling_links=[],
        home_person_id=katharina,
    )

    left, right = CARD_WIDTH / 2, CARD_WIDTH * 1.5 + SIBLING_GAP
    middle = (left + right) / 2
    bar = ROW - ROW_GAP / 2 - BAR_STEP
    assert result.lines == (
        Line(
            kind=LineKind.CHILDREN,
            path=pen_stroke(
                segments=[
                    ((middle, CARD_HEIGHT), (middle, bar)),
                    ((left, bar), (right, bar)),
                    ((left, bar), (left, ROW)),
                    ((right, bar), (right, ROW)),
                ],
                seed=zlib.crc32(b"children-1"),
            ),
        ),
    )


def test_layout_of_four_generations_places_every_card_clear_of_its_neighbours():
    josef, theresia, gertrud, franz, johann, maria = 1, 2, 3, 4, 5, 6
    florian, lukas, katharina, stefan, lena, markus, emma, jakob = 7, 8, 9, 10, 11, 12, 13, 14

    result = layout(
        people=[
            LayoutPerson(id=josef),
            LayoutPerson(id=theresia),
            LayoutPerson(id=gertrud),
            LayoutPerson(id=franz),
            LayoutPerson(id=johann),
            LayoutPerson(id=maria),
            LayoutPerson(id=florian),
            LayoutPerson(id=lukas),
            LayoutPerson(id=katharina),
            LayoutPerson(id=stefan),
            LayoutPerson(id=lena),
            LayoutPerson(id=markus),
            LayoutPerson(id=emma),
            LayoutPerson(id=jakob),
        ],
        partnerships=[
            PartnerLink(person_a=josef, person_b=theresia),
            PartnerLink(person_a=johann, person_b=maria),
            PartnerLink(person_a=lena, person_b=markus),
        ],
        parent_links=[
            ParentLink(parent=josef, child=gertrud),
            ParentLink(parent=theresia, child=gertrud),
            ParentLink(parent=josef, child=franz),
            ParentLink(parent=theresia, child=franz),
            ParentLink(parent=josef, child=johann),
            ParentLink(parent=theresia, child=johann),
            ParentLink(parent=johann, child=lukas),
            ParentLink(parent=maria, child=lukas),
            ParentLink(parent=johann, child=lena),
            ParentLink(parent=maria, child=lena),
            ParentLink(parent=johann, child=florian),
            ParentLink(parent=franz, child=katharina),
            ParentLink(parent=franz, child=stefan),
            ParentLink(parent=lena, child=emma),
            ParentLink(parent=markus, child=emma),
            ParentLink(parent=lena, child=jakob),
            ParentLink(parent=markus, child=jakob),
        ],
        sibling_links=[],
        home_person_id=lena,
    )

    assert result.cards == (
        Card(person_id=josef, x=156, y=0, generation=-2),
        Card(person_id=theresia, x=320, y=0, generation=-2),
        Card(person_id=gertrud, x=7, y=ROW, generation=-1),
        Card(person_id=franz, x=179, y=ROW, generation=-1),
        Card(person_id=johann, x=526, y=ROW, generation=-1),
        Card(person_id=maria, x=690, y=ROW, generation=-1),
        Card(person_id=katharina, x=0, y=2 * ROW, generation=0),
        Card(person_id=stefan, x=172, y=2 * ROW, generation=0),
        Card(person_id=florian, x=376, y=2 * ROW, generation=0),
        Card(person_id=lukas, x=580, y=2 * ROW, generation=0),
        Card(person_id=lena, x=752, y=2 * ROW, generation=0),
        Card(person_id=markus, x=916, y=2 * ROW, generation=0),
        Card(person_id=emma, x=748, y=3 * ROW, generation=1),
        Card(person_id=jakob, x=920, y=3 * ROW, generation=1),
    )
