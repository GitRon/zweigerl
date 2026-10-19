from datastar_py.django import datastar_response
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.common.toasts import toast_sse
from apps.family_tree.actions.tree_settings import choose_home_person
from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Person
from apps.family_tree.readers.person import loose_people, person_list
from apps.family_tree.readers.tree_settings import home_person
from apps.family_tree.views.person_search import loose_events


def tree_settings_view(request: HttpRequest) -> HttpResponse:
    """
    The settings of the tree: for now, who the home person is (#20).
    """
    return render(
        request,
        "family_tree/tree_settings.html",
        {"person_list": person_list(search=""), "loose_people": loose_people(), "home_person": home_person()},
    )


@require_POST
@datastar_response
def home_person_view(request: HttpRequest):
    """
    Saves the home person chosen on the settings page and confirms it with a toast. The form stays as it is:
    it already shows the choice. Who hangs loose follows the new home person, so the sidebar's "Lose Zweigerl"
    are patched anew (#76).
    """
    try:
        person = choose_home_person(person_id=int(request.POST.get("home_person", ""))).home_person
    except ValueError, Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return

    yield from loose_events(request)
    name = display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name)
    yield toast_sse(request=request, text=f"Passt. {name} ist jetzt die Ausgangsperson.", style="success")
