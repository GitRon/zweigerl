# Responsive layout

**The desk is the default. Zweigerl is used at a desk, with a family tree that wants every pixel of a wide
screen, so unprefixed utilities describe the laptop and nothing narrower than a tablet is designed for.**

The phone is not a target before `v2` (#38). This page says what that means, so that "desktop first" does
not turn into "breaks on anything but the author's screen".

## The breakpoints

Tailwind's defaults, unchanged. Only two of them are used here:

| Prefix | From | What it is for |
|---|---|---|
| *(none)* | 0px | **The laptop**, 1280px and up as designed. Sidebar, tree and person card side by side. |
| `max-lg:` | below 1024px | **The narrow window**: a tablet, or a browser window beside a scan. The person card goes over the tree instead of beside it. |
| `2xl:` | 1536px | Only where a wide screen has room the laptop does not — a wider sidebar, a second column in a list. |

`sm:`, `md:` and `xl:` are available and deliberately unused. A layout that needs a fourth breakpoint is
usually a layout that needs a different shape.

## Writing a screen

Write the laptop layout unprefixed, and only add what a narrower window needs to stay usable:

```html
<div class="flex gap-6 max-lg:flex-col">
```

Three rules keep a narrow window usable without designing for it:

- **The page never scrolls sideways.** The tree is the one thing allowed to be wider than the screen, and
  it scrolls inside its own container (`overflow: auto`, #12), not the page.
- **No fixed width without a fallback.** A `w-96` beside the tree is right on a laptop; below `lg` it
  gets `max-lg:w-full`.
- **Nothing is hidden on a narrow window that a laptop shows.** Move it, stack it, put it behind a tab —
  never `max-lg:hidden` on information.

## The phone

Below `md` nothing is checked and nothing is promised. When #38 makes the phone a target, this page is
rewritten for it, and that ticket owns the decision of which screens get a phone form.

## Testing it

Nothing in the suite asserts on markup — see [testing strategy](testing-strategy.md). The only gate on
this convention is looking at the page at **1280px** and at **1024px**. `/implement-story` does that on
every page a story touched once its browser run exists (#29).

## See also

- [Local setup](../contributing/setup.md) — compiling the stylesheet
- [Visual identity](visual-identity.md) — what the classes are allowed to say about colour and type
