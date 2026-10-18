# Visual identity

> **Scaffold.** This page is written by #4, which turns the moodboard into Tailwind theme tokens and
> components. Until then the screens use plain Tailwind and this page records what is already chosen.

Zweigerl should look like a family album, not like a generic app. The source is the
[moodboard](https://claude.ai/artifact/PGFYeKNXchtfE5Z5Hs6zjS).

## Already chosen

| Colour | Hex |
|---|---|
| Loden | `#4A5D3F` |
| Birkenpapier | `#F2EDE3` |
| Ziegel | `#9E4430` |
| Tinte | `#2B2A28` |
| Moos | `#C9A83B` |

| Typeface | For |
|---|---|
| Young Serif | Headings |
| Atkinson Hyperlegible | Text |
| Reenie Beanie | Notes only (#17) |

## Until #4

- Screens use Tailwind's default palette and system fonts. Keep the choices plain, they will be replaced.
- **A screen must not depend on colour alone.** The three reliability states of a fact (#13) have to be
  told apart by text as well, so they survive the switch to the CI colours.

## What #4 adds here

- The colours and typefaces as theme tokens in `assets/css/tailwind.css`, fonts served locally.
- The word mark, favicon and app icon.
- The components for the 3:4 picture frame, labels and buttons, and what each colour may be spent on.
