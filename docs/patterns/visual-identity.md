# Visual identity

**Zweigerl looks like a family album: a herbarium sheet in a farmhouse parlour. Five colours, three
typefaces, matt paper, ink lines and no shadow. A screen that needs a value not listed here is a
conversation rather than an edit.**

The source is the [moodboard](https://claude.ai/artifact/PGFYeKNXchtfE5Z5Hs6zjS). The whole identity lives
in the `@theme` block of `assets/css/tailwind.css`, and that block opens with `--color-*: initial`: it drops
Tailwind's own palette, so a stray `bg-stone-50` or `text-white` does not compile at all. That is the
enforcement. An element whose colour utility does not exist inherits its colour and still reads, where a
hue nobody chose looks fine and is wrong.

## The colours

The five from the moodboard come first, the four below them are the moodboard's own values for the album
page. The tokens are English like all code - see
[locale and language](../contributing/settings.md#locale-and-language) - and each keeps its moodboard name
beside it.

| Token | Moodboard | Value | What it is for | On `birch` |
|---|---|---|---|---|
| `birch` | Birkenpapier | `#F2EDE3` | The page. Also the text on a filled `forest`, `brick` or `ink` surface | — |
| `ink` | Tinte | `#2B2A28` | Text, and every line: a rule, a frame's edge, a tree line, an outlined control | 12.3:1 |
| `forest` | Loden | `#4A5D3F` | **Where you are and where you can go**: a link, the current entry, the focus ring, "this is you", a confirmation | 6.2:1 |
| `brick` | Ziegel | `#9E4430` | **Something wants you**: the one filled control, and what went wrong | 5.4:1 |
| `moss` | Moos | `#C9A83B` | **Decoration only**: the leaf on the app icon's `forest` ground | 2.0:1 |
| `card` | Karton | `#E7E0D2` | The card a picture sits on: an empty frame, a board behind a group | 1.1:1 |
| `card-edge` | Kartonrand | `#CFC6B4` | The edge of `card`, and a control that cannot be used | 1.4:1 |
| `ink-muted` | Tinte, matt | `#5E574B` | Quieter text: the initials in a frame, a hint, a disabled label | 6.1:1 |
| `sheet` | Blatt | `#FBF8F2` | A sheet lying on the page: a person's card, a label | 1.1:1 |

Every value that carries text clears WCAG AA on `birch`, on `card` and on `sheet`; the lowest is
`brick` on `card` at 4.8:1. `birch` on `forest` is 6.2:1 and on `brick` 5.4:1, which is why
those two may be filled behind text.

**`moss` never carries meaning and is never text.** At 2.0:1 on the page a reader who cannot make it out
has not been told anything. On `forest` it is 3.1:1, which is enough for the leaf on the icon and nothing
more.

**`brick` is a reservation, not a colour in a palette.** It is the control the screen exists for and
the thing that went wrong. It is never a heading, never a link, never decoration, and never the way a
screen says "this part matters". If two unrelated things on a screen are red, one of them is wrong.

**`forest` is the second reservation.** It says "here": the link you can follow, the section you are in,
the person in the tree who is you, a toast saying something was saved. A normal state is not news - a
person with a birth date is plain `ink`, not green.

**A screen never depends on colour alone.** The reliability of a fact (#13) and every other state is told
apart by its word first; a colour may underline the word, never replace it. That is what
[the label](#the-label) is for.

## The typefaces

| Token | Family | Its one job |
|---|---|---|
| `font-serif` | Young Serif 400 | The word mark and headings (`h1`-`h3`), and a person's name where it heads a card |
| `font-sans` | Atkinson Hyperlegible 400/700 | Everything else: prose, dates, places, labels, buttons. It is legible for anybody's grandmother, which is the point |
| `font-hand` | Reenie Beanie 400 | **Notes only** (#17): a remark in the margin, never an interface word |

**Young Serif has one weight.** The base layer sets `h1`-`h3` to 400; a heading never asks for `font-bold`,
which the browser would fake by smearing the outline.

**The handwriting is a note, not a style.** It says "somebody wrote this down": a remark on a person, a
reminder. A button, a heading or a label set in it would look playful and read badly. A note is written in
`ink`, not in the moodboard's `brick`: `brick` is reserved for what wants you, and a note is a remark, not an
alarm (#17).

The three are self-hosted from fontsource (`yarn`), never from a CDN, and only at the weights above.
`assets/css/tailwind.css` imports them, and `assets/copy-fonts.mjs` - run by `yarn build:css` - puts the
font files beside the compiled sheet in `static/dist/files/`. Without that step the page falls back to
Georgia and the system sans: it reads, but it is not Zweigerl.

## Surface

- **Matt, without a gradient and without a shadow.** The `--shadow-*` scales are dropped, so `shadow-md`
  does not exist. A page in an album lies flat.
- **Lines are ink: `ink`, 1.5px** (`border-[1.5px]`), drawn as if with a pen. A hairline that only
  separates is `card-edge` at 1px.
- **Paper corners.** The radius scale is `rounded-sm` (2px), `rounded-md` (3px) and `rounded-lg` (4px), and
  nothing else exists. A label is `sm`, a control `md`, a picture frame `lg`.
- **Pictures are real**: photos and scans, pressed plants from a herbarium. Nothing is illustrated, no
  stock icons standing in for people, no emoji.
- **Hover answers with the ground or the line**, never by moving: an outlined control gets `card` behind
  it, the filled one an `ink` edge.
- **The focus ring is `forest`, 2px**, on everything the keyboard reaches. It is set once in the base layer.

## The components

The building blocks a screen is made of. Each lives in `apps/common/templates/cotton/common/`, see
[template components](components.md).

### The word mark

`<c-common.wordmark class="text-7xl" />` - "zweigerl" in Young Serif, lower case, with the leaf growing
off the "l". It is sized by a text size in `class`; everything in it is in `em`. It is announced as
"Zweigerl". The word mark is the name and nothing else: no tagline welded to it, never in a colour other
than `ink` with a `forest` leaf.

### The picture frame

`<c-common.frame src="…" alt="…" initials="JH" width="w-18" />` - always 3:4, a portrait. The photo fills
it; without one the initials stand in it on `card`; without those it is the dashed frame with
"Foto" that asks for one. `width` is a width utility (72px by default); initials and the placeholder
scale with it. Only the photo is announced - the name beside the frame says who it is - so **a `src`
always comes with an `alt`** describing the picture, not repeating the name.

### The label

`<c-common.label text="belegt" tone="forest" />` - the Etikett: a short word on a small paper tag, like the
label on a herbarium sheet. `tone` is `ink` (a fact), `forest` (confirmed, yours) or `brick` (wants
attention). The word is the meaning and the tone only underlines it, so a label still says everything in
greyscale. On the person card (#13) a fact marked *wahrscheinlich* or *überliefert* gets an `ink` label
with that word, an *unbelegt* one a `brick` label "unbelegt, Quelle fehlt" - it wants a source - and a
*belegt* one no label at all, only its "Beleg: …" line: the normal state is not news.

### The buttons

`<c-common.button variant="primary" type="submit">Person hinzufügen</c-common.button>`

**At most one `primary` per screen**, filled `brick` with `birch` text, and it is the thing the
screen exists for. Everything else is `secondary`: an `ink` outline. With `href` the component draws a
link that looks the same. A link is never disabled: a control that may refuse is a button. A `disabled` button drops to `ink-muted` on a `card-edge` edge - quieter, still
readable. At least 44px tall, so a finger finds it too.

### The toast

Info is `ink`, success `forest`, an error `brick` - all with `birch` text, and the text says which
it is.

## Word mark and icon

The icon is the "l" alone, with its leaf - "nur das l, sonst nix". The "l" is Young Serif's own glyph
outlined into a path, so it renders without the font; the leaf is the moodboard's drawing. Both are in
`static/brand/`:

| File | What | Where |
|---|---|---|
| `favicon.svg` | `ink` "l", `forest` leaf, on `birch` with an `ink` edge | The browser tab |
| `favicon-32.png` | The same, for browsers without SVG favicons | The browser tab |
| `app-icon.svg` | `birch` "l", `moss` leaf, on `forest` | The source of the PNGs below |
| `apple-touch-icon.png`, `icon-192.png`, `icon-512.png` | Rendered from `app-icon.svg` | Home screen, `manifest.webmanifest` |

The small favicon is the light one on purpose: at 16px a dark tile with a pale letter reads as a blot.
The PNGs are rendered from the SVGs with Chromium; a change to an SVG renders them again in the same
commit. The moodboard marks the leaf "später mit Tusche" - an ink drawing replaces it later, in every
file at once.

## Tone

How Zweigerl talks is part of how it looks. From the moodboard:

- **Per du, warm, short.** "Servus! Wer g'hört noch dazu?", not "Willkommen bei deiner KI-gestützten
  Ahnenforschung!"
- **Dialect as seasoning: at most one word per sentence.** "Passt eh. Uroma Theres ist jetzt im Baum."
- **No exclamation-mark joy, no sparkle symbols.** An error says what happened: "Hoppala, da hat sich a
  Zweigerl verheddert. Probier's no amal.", not "Oops! Etwas ist schiefgelaufen."
- **An empty screen invites**: "Jeder Baum fangt mit an Zweigerl an. Mit dir." rather than "Noch keine Daten
  vorhanden."

## Where this does not reach

The phone (#38) and a dark mode are not designed. Error pages (`403`/`404`/`500`) do not exist yet; when
they do, they cannot rely on the layout and will carry the few values they use by hand.

## Design skills

A design skill brings its own defaults: palettes, type scales, motion, radius. This document overrides
them. `impeccable` is in the repository to review screens against these rules, not to choose new ones -
see [AGENTS.md](../../AGENTS.md) for which of its commands apply.

## See also

- [Template components](components.md) - where the components above live and how they take parameters
- [Responsive layout](responsive-layout.md) - the desk is the default
- [Local setup](../contributing/setup.md) - `yarn build:css`, and why it has to run again after a template
  gains a class
