from datastar_py.consts import ElementPatchMode
from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.views.decorators.http import require_POST
from django_cotton import render_component

from apps.common.media import UploadRefusedError
from apps.common.toasts import toast_sse
from apps.family_tree.actions.photo import add_photos, describe_photo, set_portrait
from apps.family_tree.domain.layout import CARD_HEIGHT, CARD_WIDTH
from apps.family_tree.models import Person, Photo, PhotoPerson
from apps.family_tree.readers.person import person_entries, photos_tab
from apps.family_tree.readers.tree import tree_card
from apps.family_tree.views.person_search import search_events


@require_POST
@datastar_response
def photo_create_view(request: HttpRequest, pk: int):
    """
    Adds the photos chosen in the Fotos tab of the person card (#16) and patches the tab - and, when the first of
    them became the portrait, every frame that shows it. A refusal keeps the form as it was and says why.
    """
    files = request.FILES.getlist("files")
    if not files:
        yield toast_sse(request=request, text="Such zuerst ein Foto aus.", style="error")
        return

    try:
        photos = add_photos(person_id=pk, files=files)
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except UploadRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield from _patch_photos(request=request, pk=pk)
    yield toast_sse(
        request=request,
        text="Passt. Das Foto ist da." if len(photos) == 1 else f"Passt. {len(photos)} Fotos sind da.",
        style="success",
    )


@require_POST
@datastar_response
def photo_portrait_view(request: HttpRequest, pk: int, photo_pk: int):
    """
    Makes a photo the portrait of the person "pk" (#16) and patches the Fotos tab and every frame showing them.
    """
    try:
        set_portrait(person_id=pk, photo_id=photo_pk)
    except PhotoPerson.DoesNotExist:
        yield toast_sse(request=request, text="Dieses Foto ist nicht mehr da.", style="error")
        return

    yield from _patch_photos(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Das ist jetzt das Titelbild.", style="success")


@require_POST
@datastar_response
def photo_describe_view(request: HttpRequest, pk: int, photo_pk: int):
    """
    Saves what a photo on the card of the person "pk" shows and when it was taken (#16). A date that is none
    keeps the form open with what was entered, and says why.
    """
    try:
        describe_photo(
            person_id=pk,
            photo_id=photo_pk,
            description=request.POST.get("description", ""),
            date=request.POST.get("date", ""),
        )
    except Photo.DoesNotExist:
        yield toast_sse(request=request, text="Dieses Foto ist nicht mehr da.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield from _patch_photos(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Ist gespeichert.", style="success")


def _patch_photos(*, request: HttpRequest, pk: int):
    # The tab and its count rather than the whole card, which would morph its tabs back to the first. The list is
    # replaced rather than morphed, so the forms in it start empty again. The portrait - or the words describing
    # it - may have changed, so every frame of the person follows: the card's head, the sidebar's list under the
    # search still running, and their card in the tree.
    found = photos_tab(pk=pk)
    if found is None:
        return
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "photo.list", photos_tab=found), mode=ElementPatchMode.REPLACE
    )
    yield ServerSentEventGenerator.patch_elements(render_component(request, "photo.count", photos_tab=found))
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "person.portrait", entry=person_entries(person_ids=[pk])[pk])
    )
    yield from search_events(request, tree_id=found.person.tree_id, search=request.POST.get("search", "").strip())
    if (in_tree := tree_card(pk=pk)) is not None:
        yield ServerSentEventGenerator.patch_elements(
            render_component(request, "tree.card", card=in_tree, width=CARD_WIDTH, height=CARD_HEIGHT)
        )
