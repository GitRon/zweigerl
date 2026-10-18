from apps.family_tree.domain.stroke import WOBBLE, pen_stroke


def test_pen_stroke_draws_each_segment_as_one_curve_between_its_ends():
    result = pen_stroke(segments=[((0, 0), (100, 0)), ((100, 0), (100, 50))], seed=7)

    assert result.startswith("M 0 0 Q ")
    assert " 100 0 M 100 0 Q " in result
    assert result.endswith(" 100 50")


def test_pen_stroke_looks_the_same_for_the_same_seed():
    segments = [((0, 0), (100, 0))]

    assert pen_stroke(segments=segments, seed=7) == pen_stroke(segments=segments, seed=7)


def test_pen_stroke_bows_differently_for_another_seed():
    segments = [((0, 0), (100, 0))]

    assert pen_stroke(segments=segments, seed=7) != pen_stroke(segments=segments, seed=8)


def test_pen_stroke_bows_off_the_straight_line_by_at_most_the_wobble():
    result = pen_stroke(segments=[((0, 0), (100, 0))], seed=7)

    control_x, control_y = (float(value) for value in result.split()[4:6])
    assert control_x == 50
    assert 0 < abs(control_y) <= WOBBLE
