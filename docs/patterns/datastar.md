# datastar

Zweigerl's pages are server-rendered Django templates. What moves without a full page load moves with
[datastar](https://data-star.dev): attributes in the template declare state and actions, and the server
answers an action with a stream of events that patch the page. There is no htmx and no front-end build
beyond the stylesheet.

The patterns here are taken from Fabian's example repository
[fbinz/django-datastar](https://github.com/fbinz/django-datastar), which uses the same three pieces:
Django, the `datastar-py` SDK and django-cotton.

## The version

**The bundle and the SDK move together.** The browser half is vendored at
`static/vendor/datastar/<version>/datastar.js`, the Python half is `datastar-py`, pinned with `==` in
`pyproject.toml`. The SDK writes the events the bundle reads, so an upgrade changes both in the same
commit:

1. Copy `bundles/datastar.js`, `bundles/datastar.js.map` and `LICENSE.md` from the release tag of
   [starfederation/datastar](https://github.com/starfederation/datastar) into a new
   `static/vendor/datastar/<version>/` and delete the old folder.
2. Change the path in `apps/common/templates/cotton/common/layout.html`.
3. Pin the matching `datastar-py` and run `uv lock`.

**Never from a CDN.** Zweigerl runs on one machine with family data on it and has to work with the
network unplugged. The npm package `@starfederation/datastar` stopped at a beta, which is why the
bundle is vendored instead of installed with yarn.

## Signals

A signal is a piece of state in the page, written `$name` in an expression. Declare it where it is
used, with its starting value, and bind or read it from there:

```html
<div data-signals="{search: ''}">
    <input data-bind="search" data-on:input__debounce.300ms="@get('{% url 'family_tree:person-search-view' %}')">
    <span data-text="$search"></span>
</div>
```

- **Signals are view state, not data.** What a person has entered lives in the database; a signal
  holds what the screen currently shows: the search term, the zoom, the selected card.
- **Names are English and lower case**, like all code: `$search`, `$zoom`, `$selection`.
- The server reads them with `read_signals(request)` and sets them with
  `ServerSentEventGenerator.patch_signals({...})`.

## Fragments

An action (`@get`, `@post`, ...) is answered with events, never with a page. The usual one patches
elements: the server renders a component and datastar morphs it into the element with the same `id`.

```python
from datastar_py.django import ServerSentEventGenerator, datastar_response, read_signals
from django_cotton import render_component


@datastar_response
def person_search_view(request):
    signals = read_signals(request) or {}
    persons = search_persons(search=signals.get("search", ""))
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "person.list", persons=persons),
    )
```

- **What is patched is a component.** `render_component` renders it with the request, so a fragment
  and the full page come from the same template. The component's root element carries the `id` the
  morph matches on.
- **A dialog is appended**, not morphed: `mode=ElementPatchMode.APPEND, selector="body"`, as a native
  `<dialog>` that opens itself and removes itself when closed.
- A view still reads the request and calls actions and readers, and nothing else - see
  [where code goes](app-layout.md).

## Pages

A page that datastar navigates to answers both ways: the whole document to a browser that loads it,
the same document as one event to a page that asks for it, with the address bar moved along. That
keeps reload, back button and bookmarks working. `apps.common.datastar.render_page` does both:

```python
def person_view(request, pk):
    person = get_person(pk=pk)
    return render_page(
        request=request,
        template="family_tree/person.html",
        context={"person": person},
        url=reverse("family_tree:person-view", kwargs={"pk": pk}),
    )
```

`is_datastar_request(request=...)` tells the two apart where a view needs to on its own. The person
card (#13) is such a case: its address `/persons/<pk>/` loads the start page with the card open, but a
click in the tree only wants the card. The view patches the component and adds `push_url(url=...)`, the
same address-bar event `render_page` sends.

## The tree and its canvas

The tree (#12) is the one screen that is bigger than the window. Fabian's repository has no example of a
canvas, so its patterns are written down here: the signals follow his counter example, the selection of a
card his contacts example.

- **Moving is scrolling.** The tree sits in a container with `overflow: auto` (`<c-tree.canvas>`), so the
  trackpad, the mouse wheel, touch and - with `tabindex="0"` on the container - the arrow keys move it
  without a line of script. Dragging with the mouse held down would need one and is its own ticket.
- **Zoom is a signal and a transform.** `$zoom` starts at `1`, and the buttons change it in an inline
  expression clamped to 25 % - 200 %: `$zoom = Math.min(2, $zoom + 0.25)`. The drawing gets
  `data-style:transform="'scale(' + $zoom + ')'"` with its origin at the top left, and the element around
  it gets the scaled width and height through `data-style:width` and `data-style:height`, so the scroll
  range shrinks and grows with the tree. Nothing goes to the server: zoom is view state.
- **A card is a button that selects.** A click sets `$selection` to the person's id and fetches their person
  card in the same expression: `$selection = 7; @get('/persons/7/')`. The card reads the signal back
  for its frame (`data-class`) and for `aria-pressed` (`data-attr:aria-pressed`); the person card is
  patched into `#person-card` and shows itself with `data-show="$selection == 7"`, so closing it - the
  button or Escape - is setting `$selection = 0`. A `data-effect` on the card moves the address back to
  the start page when that happens, so a reload does not open it again. Loaded at its own address, the
  canvas starts with `$selection` already set to the person. The selected card is filled `forest` with
  `birch` text (#83), so it is found at a glance at any zoom - an edge alone gets lost among the others at 50 %.
- **Chosen from outside the tree, a person is brought into view.** The sidebar's list, a hit of the search
  and a relative on the person card set `$focus` along with `$selection`; a card in the tree does not, it is
  already visible. A `data-effect` in the person card's head sets `$focus` back to `0` and centres
  `#tree-card-<pk>` with `scrollIntoView` one `requestAnimationFrame` later, once the person card is shown and
  the canvas beside it has its final width - a layout change under a smooth scroll stops it halfway. The
  canvas starts with `$focus` set to the person too, so an address loads centred on them. The canvas scrolls
  smoothly unless the person asked for less motion (`motion-safe:scroll-smooth`), and below `lg` a scroll margin
  on each card keeps it clear of the person card lying over the tree. A loose person has no card in the tree,
  and nothing moves.
- **The search reaches the tree as signals.** Besides patching the list, the search answers with
  `patch_signals({"filtered": ..., "matches": [...]})`: the ids of the hits, and whether a search is running
  at all. Each card fades with `$filtered && !$matches.includes(7)` and is outlined with
  `$filtered && $matches.includes(7)`. The server decides who matches, once, for the list and the tree;
  the browser never filters by itself.
- **The line of ancestors is a computed signal.** `$ancestry` is the switch "Vorfahren hervorheben" in the
  toolbar, on from the start. `data-computed:ancestors` on the canvas holds while it is on, no search runs and
  the selected person is one the tree shows: `$ancestry && !$filtered && [3, 7, …].includes($selection)`.
  Every card, placeholder and stroke carries the ids of the people whose line it belongs to, written into its
  expression by the server, and fades with `$ancestors && ![7, 12].includes($selection)`; a stroke on the line
  is drawn heavier. Nothing goes to the server on a click, and the browser decides nothing about the family:
  [the layout](tree-layout.md#the-line-of-ancestors) worked out whose line is whose.
- **Positions are inline styles.** Where a card stands comes from [the layout](tree-layout.md) in whole
  pixels and is written as `style="left: …px; top: …px"`; the lines are one SVG under the cards. They are
  data, not design, so they are no exception to [visual identity](visual-identity.md).

`data-class` and `data-style` take the class or property name after the colon in lower case only, so a
class with a colon or a slash in it goes into the object form instead:
`data-class="{'outline-2 outline-ink': $filtered}"`. The object form is also what Tailwind's scanner sees.

## CSRF

Django's CSRF protection stays on. Two ways through it, depending on where the request starts:

- **A form** posts with `{% csrf_token %}` inside it, as any Django form:
  `<form data-on:submit="@post('...', {contentType: 'form'})">{% csrf_token %} ...</form>`.
- **A button** sends the token as a header:
  `data-on:click="@post('...', {headers: {'X-CSRFToken': '{{ csrf_token }}'}})"`.

## Toasts

A toast confirms what just happened, in the corner of the page. Two helpers in `apps.common.toasts`,
depending on whether the response stays on the page:

- **`toast_sse(request=..., text=..., style=...)`** returns an event to yield from a datastar response.
  It appends the toast to `#toasts`.
- **`toast_session(request=..., text=..., style=...)`** keeps the toast in the session when the response
  redirects. The layout shows it on the next page it renders, once.

`style` is `info`, `success` or `error`. A toast removes itself after five seconds.

## When JavaScript of our own is allowed

Hardly ever. Before writing a script, check whether an attribute does it: `data-show`, `data-class`,
`data-attr`, `data-on:*` with its modifiers, `data-computed`, `data-effect`, `data-init`. An inline
expression in an attribute is fine; a function longer than one line is not.

A script file of our own is allowed only for what datastar has no attribute for, such as dragging the
tree with the mouse. It then lives in `static/js/`, carries a comment saying why an attribute was not
enough, and talks to the page through signals and the DOM rather than through globals.
