from apps.family_tree.domain.html_text import plain_text


def test_plain_text_keeps_a_text_without_tags_as_it_is():
    result = plain_text(text="Pfarre St. Peter & Paul,  Band 3")

    assert result == "Pfarre St. Peter & Paul,  Band 3"


def test_plain_text_puts_each_block_on_a_line_of_its_own():
    result = plain_text(text="<p>Kirchenbuch</p><div>Taufen</div>Band 3<br>Seite 12<br/>Eintrag 4")

    assert result == "Kirchenbuch\nTaufen\nBand 3\nSeite 12\nEintrag 4"


def test_plain_text_drops_an_inline_tag_without_a_break():
    result = plain_text(text='<p><B>Sammlung:</B> <a href="https://example.org">Stammbaum</a></p>')

    assert result == "Sammlung: Stammbaum"


def test_plain_text_breaks_the_line_at_a_tag_it_does_not_know():
    result = plain_text(text="<x>Treffer</x><x>Sammlung: Stammbaum</x>Treffer: 1234")

    assert result == "Treffer\nSammlung: Stammbaum\nTreffer: 1234"


def test_plain_text_resolves_entities():
    result = plain_text(text="<p>Peter&nbsp;&amp;&nbsp;Paul &#8211; Band&nbsp;3</p>")

    assert result == "Peter & Paul – Band 3"


def test_plain_text_trims_the_lines_and_leaves_out_empty_ones():
    result = plain_text(text="<p>  Kirchenbuch </p>\n<p></p><p>Band   3\n</p>")

    assert result == "Kirchenbuch\nBand 3"
