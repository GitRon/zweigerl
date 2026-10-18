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

`is_datastar_request(request=...)` tells the two apart where a view needs to on its own.

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
