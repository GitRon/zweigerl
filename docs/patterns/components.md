# Template components

**A template that is reused across pages, or patched into a page by datastar, is a component, not an
include.** Components are [django-cotton](https://django-cotton.com): an HTML-like tag at the call site, a
template with its parameters declared at the top, and slots for markup the caller wraps.

```html
<c-common.layout title="Personen">…</c-common.layout>
<c-common.toast :text="toast.text" :style="toast.style" />
```

An include has no contract: what it expects is only visible by reading it, and a misspelt parameter
renders as nothing. A component declares its parameters.

The second reason is datastar: a fragment the server patches into the page is rendered with
`render_component(request, "<topic>.<name>", ...)`, so the same component draws the element in the full
page and in the update — see [datastar](datastar.md#fragments).

## Where a component lives

`<app>/templates/cotton/<topic>/<name>.html`, at the app root like every other template — see
[where code goes](app-layout.md). The tag is the path below `cotton/`: folders become dots and
underscores become hyphens, so `apps/family_tree/templates/cotton/person/card.html` is
`<c-person.card>`.

**Always one topic folder.** Both apps share the one `cotton/` namespace, and the template loader takes
the first app that has the file, so a second `cotton/card.html` in another app is shadowed without a
word. The folder keeps the names apart.

| Component | Lives in | For |
|---|---|---|
| `<c-common.layout>` | `apps.common` | The page around everything: stylesheet, datastar, the toast area; the page as the slot, `title` before "Zweigerl" in the tab |
| `<c-common.toast>` | `apps.common` | One toast, `info`, `success` or `error`, removing itself after five seconds |
| `<c-common.wordmark>` | `apps.common` | The word mark, sized by a text size in `class` |
| `<c-common.frame>` | `apps.common` | The 3:4 picture frame: the photo, else the initials, else the empty frame asking for one; `width` sizes it |
| `<c-common.label>` | `apps.common` | The Etikett: a short word on a paper tag, in the tone `ink`, `forest` or `brick` |
| `<c-common.button>` | `apps.common` | A button, `primary` or `secondary`, or with `href` a link drawn as one |
| `<c-person.sidebar>` | `apps.family_tree` | The sidebar beside the tree: word mark, "Person hinzufügen" (#18), the search field bound to `$search`, the list (#10) and the link to the settings |
| `<c-person.list>` | `apps.family_tree` | Every person `readers.person.person_list` found, with frame, name and Lebensdaten; `id="person-list"`, patched by the live search |
| `<c-person.card>` | `apps.family_tree` | The person card beside the tree (#12, #13): frame, name, Lebensdaten and the relationship to the home person, with the pencil that swaps the head for the form "Name & Status bearbeiten" (#30), then the tabs - every fact with its Beleg, and the relatives, each opening their own card; `id="person-card"`, patched when a card is clicked |
| `<c-person.new-dialog>` | `apps.family_tree` | The short form a new person starts with (#18): who they are to the person whose card it opens from - only there - names, sex and whether they are alive; a native `<dialog>` appended to the body, opening itself and removed when closed |
| `<c-tree.canvas>` | `apps.family_tree` | The tree from `readers.tree.tree`: the zoom buttons and the slot in its toolbar, the scrolling container, the lines, placeholders and cards |
| `<c-tree.card>` | `apps.family_tree` | One person in the tree at their position; a button that selects them and fetches their person card |
| `<c-settings.home-person>` | `apps.family_tree` | The choice of the home person on the settings page (#20): every person, the chosen one selected, posted as a form and confirmed with a toast |

What each of the last four looks like, and when a screen may use which, is
[visual identity](visual-identity.md#the-components).

A new component gets a row here.

## Parameters

Declared in `<c-vars>` on the component's first line:

```html
<c-vars text style="info" />
```

- **A name without a value is required.** Every call site has to pass it.
- **A name with a value is optional**, and the value is its default.
- **Every parameter is declared**, including the optional ones. A component sees its caller's context, the
  same as an include, so an undeclared name would quietly pick up whatever the caller has under it. A
  declared default shadows that.

At the call site, `:name="expression"` passes a value from the context, and `name="text"` passes the
text. A bare `name` passes `True`, which is how a flag reads.

### Attributes the component passes on

An attribute the component does not declare is not a parameter: cotton collects it into `{{ attrs }}`.
A component that wraps one element and is put to work by its caller - a button taking a datastar
`data-on:click`, an `id` or `disabled` - writes `{{ attrs }}` on that element, so the call site can say
what it does without the component knowing every datastar attribute there is.

```html
<c-common.button variant="primary" data-on:click="@post('/persons/')">Anlegen</c-common.button>
```

Only a component that writes `{{ attrs }}` passes anything on; everywhere else an undeclared attribute is
dropped. A `class` the caller adds is declared (`class=""`) and appended to the component's own classes,
so it never replaces them by accident.

## Slots

Markup between the tags arrives as `{{ slot }}`. A component that wraps the caller's content — the
layout, a card — takes it through the slot rather than through a parameter carrying markup. Named slots
(`<c-slot name="footer">`) are for a component with more than one place to fill.

## No logic in a component

A component places values; it does not compute them. A comparison, a threshold, a German relationship
name or the choice between "belegt" and "unbelegt" goes into a template filter, a model property or a
pure function, with an ordinary unit test there.

## An element datastar patches carries an `id`

datastar morphs a fragment into the element with the same `id`. A component that is ever patched on its
own therefore puts a stable `id` on its root element, derived from what it shows (`person-{{ person.pk }}`),
never from a loop counter.

## Configuration

`apps/config/settings.py` installs `django_cotton.apps.SimpleAppConfig` and writes the loaders and the
builtin out explicitly. The default app config rewrites `TEMPLATES` in its `ready()`, so the settings file
would not say what runs. Both configs patch Django's template lexer so a template tag inside a component
attribute survives; that is private Django API, and the render tests below are what notice a Django
upgrade breaking it.

## Tests

Every component is rendered in a test of its own — where it lives and what it may assert are in
[testing strategy](testing-strategy.md#components).

The render test passes every parameter, so with `FAIL_INVALID_TEMPLATE_VARS` on, a parameter renamed in
the component but not in the test fails. Once there are enough components that a test per component is no
longer checked by hand, this becomes an [architecture test](architecture-tests.md) over all of them.

## See also

- [Testing strategy](testing-strategy.md#components) — what a component test may assert on
- [datastar](datastar.md) — rendering a component as a fragment
