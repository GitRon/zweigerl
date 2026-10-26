# Tree layout

**Where every card and every line of the tree goes is one pure function, `domain.layout.layout()`: people and
how they are related in, positions and SVG paths out.** It has no database and no request behind it, so every
rule below is tested without a browser. `readers.tree.tree_layout()` loads the rows and calls it, and
`readers.tree.tree()` puts each person's name and Lebensdaten on their card. Drawing that - the cards, the
canvas, scrolling and zoom - is `<c-tree.canvas>`, see [datastar](datastar.md#the-tree-and-its-canvas).

## Who is in the tree

Everyone connected to the home person through any chain of parents, children, partners and siblings. While
no home person is chosen, the person entered first stands in for them, see
[the home person](family.md#the-home-person). Who has no connection is left out: they are the "Lose
Zweigerl" of #19, listed at the bottom of the sidebar rather than drawn, see
[deleting and unlinking](family.md#deleting-and-unlinking).

**All generations are shown** (decided 18.10.2026). A limit comes as its own ticket once the drawing gets
too slow.

## Rows

A person's generation is their distance from the home person: a parent one row above, a child one below, a
partner and a sibling in the same row. `Card.generation` is 0 for the home person's row, -1 for their
parents', 1 for their children's. Where two paths disagree, three rules settle it (#31):

1. **Blood before marriage.** The generation comes from the path with the fewest steps to a partner or a
   sibling, then from the shortest. A niece who married her uncle stays a row below her father.
2. **A parent stands above their child**, also where lines of different length meet - someone who is a
   grandfather through one line and a great-grandfather through the other. Above the home person's row the
   parent moves up, below it the child moves down, and the line between them crosses the rows in between.
3. **A couple shares a row** wherever rule 2 still holds: the one further from the home person moves, else
   the other; the home person stays. A couple that cannot - a marriage across generations - keeps its two
   rows and gets a stepped line, see [Lines](#lines).

Moving people up and down can leave a generation with nobody in it (#68). Its row stays empty rather than
closing up, so a card's row is always its generation, and the tree's height runs from the top of the highest
row to the bottom of the lowest.

## What stands together

- **A couple** stands side by side: a `Partnership`, or two parents of one child without one.
- **Several partners** (#31): everyone a chain of couples joins in a row stands as one unit. Whoever has
  the most partners stands in the middle, the first partner - by the order the Partnerships were entered -
  to the left, the others to the right; a partner with partners of their own takes them further out on
  their side. Of a single couple, the one with parents in the tree stands left.
- **Siblings** stand side by side under the bar of their parents, ordered by the sort date of their earliest
  birth fact (#5, see [Belege](evidence.md)). Siblings without a birth date come last, ties in the order
  they were entered. A sibling's partner stands next to them, on the side of the partner's own parents
  when those are in the tree too.
- **Half-siblings** hang under their own couple: the children of each marriage from the gap between that
  pair, so they stand apart from their half-siblings. The bar of each further couple of a unit runs a
  `BAR_STEP` lower - at most two - so where the children of two marriages stand close, their bars do not
  run together into one.
- **A child with one known parent** hangs from that parent. Their bar runs `BAR_STEP` higher than a
  couple's, so a father's son of an unknown mother does not look like the couple's.
- **Siblings without known parents** - those only a `SiblingPair` connects - hang from a `Placeholder`: a
  card-sized gap with a dashed frame, drawn where their parents would stand. It is not a person in the
  database; it shows where research is missing. A single person without parents gets none.
- **Aunts, uncles and great-uncles** stand in the row of their sibling, among their siblings.

Very wide rows of many children are not handled yet; they get their own ticket once real data shows them.

## Ahnenschwund

**A person is drawn once, however many ways they are related to the home person** (decided 18.10.2026):
where two lines of ancestors meet, both lines lead to the same card. That ancestor - the grandparents a
cousin and a cousin who married share - gets `Card.pedigree_collapse`, and the canvas pins the label
"Ahnenschwund" over the card. Only where the lines meet: two or more of their children are the home person
or among the home person's ancestors. Their own ancestors are reached the same ways but are not marked.

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
| `partners` | the right edge of one partner | the left edge of the other, at half the card's height, and `PARTNER_STEP` lower for every card it passes behind - the line to a third spouse does not lie on the line to the second |
| `partners`, across two rows | the side of the upper partner facing the lower | down the gap beside them, across a quarter of the row gap above the lower row, down the gap beside the lower partner and into their side - clear of the cards in between |
| `children` | the gap beside the outer of a couple, on their partner line - between the two when they stand side by side; the last bend of a stepped line; or the bottom of a single parent's, two unmarried parents' or a placeholder's card | a bar above the children, and from it down to each child |

A bar reaches from the line down from the parents to the outermost child, no further. **Two bars never lie on
each other** (#103): where the bars of two families above the same row overlap - the family of a partner who
stands among their spouse's siblings reaches across them - the later one, in the order of the families, runs
a `BAR_STEP` lower, or higher, whichever is nearest and free, at most two steps from halfway between the rows.
Each child hangs from exactly one bar that can be followed to their parents.

A line between rows that are not neighbours - Ahnenschwund over a different number of generations - runs
straight down through the rows in between.

**Lines are drawn as pen strokes** by `domain.stroke.pen_stroke()`: every straight segment bows a little,
by at most `WOBBLE` pixels, its ends left exactly where they are. The bow is random only in appearance - each
line has a fixed seed, the `crc32` of the people it joins (`partners-3-5`, `children-3-5`,
`placeholder-7-8`), so a line looks the same on every load and after every restart. Python's `hash()` is
salted per process and would change it each time. Tests need no patching, see [mocking](mocking.md).

## The line of ancestors

**Chosen, a person's line of ancestors stands out** (#103): they, their parents, grandparents and so on up,
and the lines joining them; everything else fades. The layout says, for each piece, whose line it is part of:

- `TreeLayout.lineages` gives every person themselves and their descendants in the tree - choosing any of
  them makes the person's card stand out. A `Placeholder` is part of the lines of its siblings.
- A `Line` is made of `Stroke`s, one per straight piece, drawn by `pen_strokes()` with the line's seed - put
  together they are exactly the line `pen_stroke()` draws. Each stroke's `lineage`: the drop from the parents
  belongs to all the children, a piece of the bar to the children beyond it, the drop to a child to that
  child. So of a family only the way down to the one child on the line stands out, not the bar to their
  siblings.
- A partner line belongs to the line of whoever both partners are ancestors of: it stands out between a
  person's parents, not between them and a spouse.

Where two lines of ancestors meet, the ancestor is part of both and stands out once. How it is shown is
[datastar](datastar.md#the-tree-and-its-canvas).

## See also

- [Persons and families](family.md) - the models the layout reads
- [Belege](evidence.md) - the sort date siblings are ordered by
- [Where code goes](app-layout.md) - `domain/` and its import contract
