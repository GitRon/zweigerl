"""
The pen strokes the tree's lines are drawn with (#11): each straight segment bows a little, the way a line drawn
by hand does. See docs/patterns/tree-layout.md.

Random only in appearance: every line brings its own seed, so it looks the same on every load.
"""

import math
import random
from collections.abc import Sequence

type Point = tuple[float, float]
type Segment = tuple[Point, Point]

# How far a segment bows away from the straight line at most, in pixels.
WOBBLE = 2.5


def pen_stroke(*, segments: Sequence[Segment], seed: int) -> str:
    """
    An SVG path drawing every segment as one slightly bowed stroke, see "pen_strokes".
    """
    return " ".join(pen_strokes(segments=segments, seed=seed))


def pen_strokes(*, segments: Sequence[Segment], seed: int) -> list[str]:
    """
    One SVG path per segment, each a slightly bowed stroke - a quadratic curve whose control point sits off the
    middle of the segment, by an amount the seed decides. The ends stay exactly where they are, so a stroke still
    meets the card it leads to. Every segment must have a length. Together they are exactly "pen_stroke".
    """
    rng = random.Random(seed)
    parts = []
    for (x1, y1), (x2, y2) in segments:
        length = math.hypot(x2 - x1, y2 - y1)
        bow = rng.uniform(-WOBBLE, WOBBLE)
        control_x = (x1 + x2) / 2 - (y2 - y1) / length * bow
        control_y = (y1 + y2) / 2 + (x2 - x1) / length * bow
        start, control, end = (_point(x=x, y=y) for x, y in ((x1, y1), (control_x, control_y), (x2, y2)))
        parts.append(f"M {start} Q {control} {end}")
    return parts


def _point(*, x: float, y: float) -> str:
    return f"{round(x, 1):g} {round(y, 1):g}"
