from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.person import Relation, add_relative, create_person
from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Person
from apps.family_tree.readers.person import person_entries


@require_GET
@datastar_response
def new_person_view(request: HttpRequest):
    """
    The dialog behind "Person hinzufügen" in the sidebar (#18): a person on their own, connected to nobody.
    """
    yield _dialog(request=request, title="Person hinzufügen", url=reverse("family_tree:create-person-view"))


@require_POST
@datastar_response
def create_person_view(request: HttpRequest):
    """
    Adds the person entered in the dialog and opens their card, where everything else about them is entered.
    """
    try:
        person = create_person(**_person_fields(request=request))
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield _open_card(request=request, person=person)


@require_GET
def new_relative_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The dialog behind "Verwandte hinzufügen" on a person's card (#18), asking what the new person is to them.
    """
    entry = person_entries(person_ids=[pk]).get(pk)
    if entry is None:
        raise Http404

    return DatastarResponse(
        _dialog(
            request=request,
            title=f"Verwandte von {entry.name} hinzufügen",
            url=reverse("family_tree:create-relative-view", kwargs={"pk": pk}),
            relations=Relation.choices,
        )
    )


@require_POST
@datastar_response
def create_relative_view(request: HttpRequest, pk: int):
    """
    Adds the relative entered in the dialog, connected to the person whose card it was opened from, and opens the
    new person's card. A link the family's rules refuse leaves the dialog open with the reason as a toast.
    """
    try:
        person = add_relative(
            person_id=pk, relation=request.POST.get("relation", ""), **_person_fields(request=request)
        )
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except ValueError:
        yield toast_sse(request=request, text="Wähl aus, wie die beiden verwandt sind.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield _open_card(request=request, person=person)


def _dialog(*, request: HttpRequest, title: str, url: str, relations: list | None = None):
    return ServerSentEventGenerator.patch_elements(
        render_component(
            request,
            "person.new-dialog",
            title=title,
            url=url,
            relations=relations or [],
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


def _open_card(*, request: HttpRequest, person: Person):
    # A whole page load rather than patches: the new person belongs in the sidebar's list and, connected, in the
    # tree as well as on the card, and the page at their address already draws all three.
    name = display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name)
    toast_session(request=request, text=f"Passt. {name} ist jetzt im Baum.", style="success")
    return ServerSentEventGenerator.redirect(reverse("family_tree:person-view", kwargs={"pk": person.pk}))
