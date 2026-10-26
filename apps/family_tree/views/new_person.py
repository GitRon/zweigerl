from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response, read_signals
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.person import Relation, add_relative, create_person, link_relative
from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Partnership, Person, Tree
from apps.family_tree.readers.person import RelativeDialog, person_entries, relative_candidates, relative_dialog


@require_GET
@datastar_response
def new_person_view(request: HttpRequest, tree_pk: int):
    """
    The dialog behind "Person hinzufügen" in the sidebar (#18): a person of the tree on their own, connected to
    nobody.
    """
    yield _dialog(
        request=request,
        title="Person hinzufügen",
        url=reverse("family_tree:create-person-view", kwargs={"tree_pk": tree_pk}),
    )


@require_POST
@datastar_response
def create_person_view(request: HttpRequest, tree_pk: int):
    """
    Adds the person entered in the dialog to the tree and opens their card, where everything else about them is
    entered.
    """
    try:
        person = create_person(tree_id=tree_pk, **_person_fields(request=request))
    except Tree.DoesNotExist:
        yield toast_sse(request=request, text="Diesen Stammbaum gibt es nicht mehr.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield _open_card(request=request, person=person)


@require_GET
def new_relative_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The dialog behind "Verwandte hinzufügen" on a person's card (#18), asking what the relative is to them, and
    who: somebody already in the tree (#89) or a new person.
    """
    dialog = relative_dialog(pk=pk)
    if dialog is None:
        raise Http404

    return DatastarResponse(
        _dialog(
            request=request,
            title=f"Verwandte von {dialog.entry.name} hinzufügen",
            url=reverse("family_tree:create-relative-view", kwargs={"pk": pk}),
            relations=Relation.choices,
            dialog=dialog,
            candidates_url=reverse("family_tree:relative-candidates-view", kwargs={"pk": pk}),
        )
    )


@require_GET
@datastar_response
def relative_candidates_view(request: HttpRequest, pk: int):
    """
    Who in the tree is offered as the relative chosen in the dialog (#89), for "$relation" and "$relative_search",
    patched into the dialog's list.
    """
    signals = read_signals(request) or {}
    search = str(signals.get("relative_search", "")).strip()
    yield ServerSentEventGenerator.patch_elements(
        render_component(
            request,
            "person.candidates",
            candidates=relative_candidates(pk=pk, relation=str(signals.get("relation", "")), search=search),
            search=search,
        )
    )


@require_POST
@datastar_response
def create_relative_view(request: HttpRequest, pk: int):
    """
    Connects the relative chosen in the dialog to the person whose card it was opened from: somebody already in
    the tree (#89), after which the person's card opens again with them among the relatives, or a new person, whose
    own card opens. A link the family's rules refuse leaves the dialog open with the reason as a toast.
    """
    relation = request.POST.get("relation", "")
    couple = {
        "partnership_id": _optional_id(value=request.POST.get("partnership", "")),
        "pair_with_parent": request.POST.get("pair_with_parent") == "on",
    }
    relative_id = _optional_id(value=request.POST.get("relative_id", ""))
    try:
        if relative_id is None:
            relative = add_relative(person_id=pk, relation=relation, **couple, **_person_fields(request=request))
        else:
            relative = link_relative(person_id=pk, relation=relation, relative_id=relative_id, **couple)
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except Partnership.DoesNotExist:
        yield toast_sse(request=request, text="Diese Partnerschaft gibt es nicht mehr.", style="error")
        return
    except ValueError:
        yield toast_sse(request=request, text="Wähl aus, wie die beiden verwandt sind.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    if relative_id is None:
        yield _open_card(request=request, person=relative)
    else:
        yield _open_linked(request=request, pk=pk, relative=relative, relation=relation)


def _optional_id(*, value: str) -> int | None:
    # A field the dialog leaves empty for "nobody": a new person rather than one in the tree, the person's child
    # alone rather than a couple's. Anything but a number counts as empty.
    return int(value) if value.isdecimal() else None


def _dialog(
    *,
    request: HttpRequest,
    title: str,
    url: str,
    relations: list | None = None,
    dialog: RelativeDialog | None = None,
    candidates_url: str = "",
):
    return ServerSentEventGenerator.patch_elements(
        render_component(
            request,
            "person.new-dialog",
            title=title,
            url=url,
            relations=relations or [],
            couples=dialog.couples if dialog else [],
            person_name=dialog.entry.name if dialog else "",
            parent_name=(dialog.parent or "") if dialog else "",
            candidates_url=candidates_url,
            sexes=Person.Sex.choices,
            living_statuses=Person.LivingStatus.choices,
        ),
        mode=ElementPatchMode.APPEND,
        selector="body",
    )


def _person_fields(*, request: HttpRequest) -> dict[str, str]:
    return {
        "given_names": request.POST.get("given_names", ""),
        "surname": request.POST.get("surname", ""),
        "sex": request.POST.get("sex", Person.Sex.UNKNOWN),
        "living_status": request.POST.get("living_status", Person.LivingStatus.UNKNOWN),
    }


def _open_linked(*, request: HttpRequest, pk: int, relative: Person, relation: str):
    # The person's own card again, as a whole page for the same reason as "_open_card": the link may change the
    # tree, the relatives on the card and who is loose in the sidebar.
    entries = person_entries(person_ids=[pk, relative.pk])
    toast_session(
        request=request,
        text=f"Passt. {entries[relative.pk].name} ist jetzt {Relation(relation).label} von {entries[pk].name}.",
        style="success",
    )
    return ServerSentEventGenerator.redirect(reverse("family_tree:person-view", kwargs={"pk": pk}))


def _open_card(*, request: HttpRequest, person: Person):
    # A whole page load rather than patches: the new person belongs in the sidebar's list and, connected, in the
    # tree as well as on the card, and the page at their address already draws all three.
    name = display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name)
    toast_session(request=request, text=f"Passt. {name} ist jetzt im Baum.", style="success")
    return ServerSentEventGenerator.redirect(reverse("family_tree:person-view", kwargs={"pk": person.pk}))
