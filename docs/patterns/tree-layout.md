# Tree layout

**Where every card and every line of the tree goes is one pure function, `domain.layout.layout()`: people and
how they are related in, positions and SVG paths out.** It has no database and no request behind it, so every
rule below is tested without a browser. `readers.tree.tree_layout()` loads the rows and calls it; drawing what
it returns - the cards, the canvas, scrolling and zoom - is #12's.

## Who is in the tree

Everyone connected to the home person through any chain of parents, children, partners and siblings. While
no home person is chosen, the person entered first stands in for them, see
[the home person](family.md#the-home-person). Who has no connection is left out: they are the "Lose
Zweigerl" of #19, listed in the sidebar rather than drawn.

**All generations are shown** (decided 18.10.2026). A limit comes as its own ticket once the drawing gets
too slow.

## Rows

A person's generation is their distance from the home person: a parent one row above, a child one below, a
partner and a sibling in the same row. `Card.generation` is 0 for the home person's row, -1 for their
parents', 1 for their children's. Where two paths disagree - a marriage across generations - the shorter
one wins; drawing such trees properly is #31's.

## What stands together

- **A couple** stands side by side: a `Partnership`, or two parents of one child without one. One partner
  per person; a second partner stands apart and their children still connect to both parents. Several
  marriages and pedigree collapse are #31's.
- **Siblings** stand side by side under the bar of their parents, ordered by the sort date of their earliest
  birth fact (#5, see [Belege](evidence.md)). Siblings without a birth date come last, ties in the order
  they were entered. A sibling's partner stands next to them, on the side of the partner's own parents
  when those are in the tree too.
- **A child with one known parent** hangs from that parent, and so do half-siblings, until #31 puts them
  under the right couple. Their bar runs `BAR_STEP` higher than a couple's, so a father's son from before
  the marriage does not look like the couple's.
- **Siblings without known parents** - those only a `SiblingPair` connects - hang from a `Placeholder`: a
  card-sized gap with a dashed frame, drawn where their parents would stand. It is not a person in the
  database; it shows where research is missing. A single person without parents gets none.
- **Aunts, uncles and great-uncles** stand in the row of their sibling, among their siblings.

Very wide rows of many children are not handled yet; they get their own ticket once real data shows them.

## Placement

The rows start out in the order people are reached from the home person. Then, `SWEEPS` times, every row is
reordered and placed twice: going down, each block of siblings under the middle of its parents; going back
up, each parent over the middle of their children. A block of siblings moves as one and keeps its order.
Within a row nothing overlaps: `SIBLING_GAP` between the units of one block, `BLOCK_GAP` between blocks.
Placing a row as close to where its cards want to be is a least-squares problem with order constraints,
solved exactly by pooling adjacent violators - so the same tree always comes out the same.

Positions are whole pixels, the top left corner of each card, with the leftmost card at 0 and the top row at
0. The sizes - `CARD_WIDTH`, `CARD_HEIGHT`, the gaps - are constants in `domain/layout.py`; #12 may change
them to fit its cards.

## Lines

Every line is a `Line` with its `kind` and an SVG `path`:

| Kind | From | To |
|---|---|---|
| `partners` | the right edge of one partner | the left edge of the other, at half the card's height |
| `children` | the middle of the partner line, or the bottom of a single parent's or a placeholder's card | a bar above the children, and from it down to each child |

**Lines are drawn as pen strokes** by `domain.stroke.pen_stroke()`: every straight segment bows a little,
by at most `WOBBLE` pixels, its ends left exactly where they are. The bow is random only in appearance - each
line has a fixed seed, the `crc32` of the people it joins (`partners-3-5`, `children-3-5`,
`placeholder-7-8`), so a line looks the same on every load and after every restart. Python's `hash()` is
salted per process and would change it each time. Tests need no patching, see [mocking](mocking.md).

## See also

- [Persons and families](family.md) - the models the layout reads
- [Belege](evidence.md) - the sort date siblings are ordered by
- [Where code goes](app-layout.md) - `domain/` and its import contract
