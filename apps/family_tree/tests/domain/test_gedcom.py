import io

import pytest
from ged4py.parser import ParserError

from apps.family_tree.domain.gedcom import Node, from_raw, raw_list, read, to_raw, write


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


def test_to_raw_keeps_the_tag_the_value_and_the_children():
    node = Node(tag="_UID", value="4F2A", children=(Node(tag="_SRC", value="PAF"),))

    assert to_raw(node=node) == {"tag": "_UID", "value": "4F2A", "children": [{"tag": "_SRC", "value": "PAF"}]}


def test_to_raw_leaves_out_an_empty_value_and_no_children():
    assert to_raw(node=Node(tag="_FLAG")) == {"tag": "_FLAG"}


def test_to_raw_leaves_out_a_child_pointing_at_a_record():
    node = Node(tag="OCCU", value="Uhrmacher", children=(Node(tag="SOUR", pointer="@S1@"),))

    assert to_raw(node=node) == {"tag": "OCCU", "value": "Uhrmacher"}


def test_raw_list_leaves_out_a_node_pointing_at_a_record():
    nodes = [Node(tag="SOUR", pointer="@S1@"), Node(tag="RELI", value="röm.-kath.")]

    assert raw_list(nodes=nodes) == [{"tag": "RELI", "value": "röm.-kath."}]


def test_read_puts_each_line_below_the_record_it_belongs_to():
    file = io.BytesIO(b"0 @I1@ INDI\r\n1 NAME Lena /Huber/\r\n2 GIVN Lena\r\n1 SEX F\r\n0 TRLR\r\n")

    records = read(file=file)

    assert records == [
        Node(
            xref="@I1@",
            tag="INDI",
            children=(
                Node(tag="NAME", value="Lena /Huber/", children=(Node(tag="GIVN", value="Lena"),)),
                Node(tag="SEX", value="F"),
            ),
        ),
        Node(tag="TRLR"),
    ]


def test_read_joins_conc_without_a_space_and_cont_on_a_new_line():
    file = io.BytesIO(b"0 NOTE Uhrma\n1 CONC cher in Graz\n1 CONT zweite Zeile\n")

    assert read(file=file) == [Node(tag="NOTE", value="Uhrmacher in Graz\nzweite Zeile")]


def test_read_joins_a_character_cut_in_two_by_conc():
    file = io.BytesIO(b"\xef\xbb\xbf0 HEAD\n1 CHAR UTF-8\n0 NOTE M\xc3\n1 CONC \xbcller\n")

    assert read(file=file)[1] == Node(tag="NOTE", value="Müller")


def test_read_decodes_utf_8_behind_a_byte_order_mark():
    file = io.BytesIO("﻿0 HEAD\r\n1 CHAR UTF-8\r\n0 NOTE Gößl ž\r\n".encode())

    assert read(file=file)[1] == Node(tag="NOTE", value="Gößl ž")


def test_read_tells_a_pointer_from_a_value():
    file = io.BytesIO(b"0 FAM\n1 HUSB @I1@\n1 NOTE anna@@huber.example\n1 DATE @#DJULIAN@ 1700\n")

    assert read(file=file)[0].children == (
        Node(tag="HUSB", pointer="@I1@"),
        Node(tag="NOTE", value="anna@huber.example"),
        Node(tag="DATE", value="@#DJULIAN@ 1700"),
    )


def test_read_skips_an_empty_line_and_a_stray_line_break():
    file = io.BytesIO(b"0 @I1@ INDI\r\n\r\n1 BIRT\r\n2 PLAC Graz \n\r\n0 TRLR\r\n")

    assert read(file=file) == [
        Node(
            tag="INDI",
            xref="@I1@",
            children=(Node(tag="BIRT", children=(Node(tag="PLAC", value="Graz "),)),),
        ),
        Node(tag="TRLR"),
    ]


def test_read_refuses_a_file_that_is_not_gedcom():
    with pytest.raises(ParserError, match="Invalid syntax"):
        read(file=io.BytesIO(b"0 HEAD\nLiebe Oma,\n0 TRLR\n"))
