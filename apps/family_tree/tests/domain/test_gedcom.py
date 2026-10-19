from apps.family_tree.domain.gedcom import Node, from_raw, write


def test_from_raw_reads_a_structure_with_its_children():
    records = [{"tag": "_UID", "value": "4F2A", "children": [{"tag": "_SRC", "value": "PAF"}]}]

    nodes = from_raw(records=records)

    assert nodes == (Node(tag="_UID", value="4F2A", children=(Node(tag="_SRC", value="PAF"),)),)


def test_from_raw_reads_a_structure_without_value_or_children():
    nodes = from_raw(records=[{"tag": "_FLAG"}])

    assert nodes == (Node(tag="_FLAG"),)


def test_write_puts_children_one_level_below_their_record():
    record = Node(xref="@I1@", tag="INDI", children=(Node(tag="NAME", value="Lena /Huber/"),))

    text = write(records=[record, Node(tag="TRLR")])

    assert text == "0 @I1@ INDI\n1 NAME Lena /Huber/\n0 TRLR\n"


def test_write_leaves_a_pointer_as_it_is():
    text = write(records=[Node(tag="FAM", children=(Node(tag="HUSB", pointer="@I1@"),))])

    assert text == "0 FAM\n1 HUSB @I1@\n"


def test_write_doubles_an_at_sign_in_a_value():
    text = write(records=[Node(tag="NOTE", value="anna@huber.example")])

    assert text == "0 NOTE anna@@huber.example\n"


def test_write_continues_a_line_break_on_cont_lines():
    text = write(records=[Node(tag="TEXT", value="Taufbuch Mariazell\r\nBand 3\n\nfol. 12")])

    assert text == "0 TEXT Taufbuch Mariazell\n1 CONT Band 3\n1 CONT\n1 CONT fol. 12\n"


def test_write_cuts_a_long_value_into_conc_lines_beside_a_space():
    value = "a" * 199 + " " + "b" * 10

    text = write(records=[Node(tag="TEXT", value=value)])

    assert text == f"0 TEXT {'a' * 198}\n1 CONC a b{'b' * 9}\n"


def test_write_cuts_a_value_of_nothing_but_spaces_where_it_must():
    text = write(records=[Node(tag="TEXT", value=" " * 201)])

    assert text == f"0 TEXT {' ' * 200}\n1 CONC  \n"
