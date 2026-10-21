from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django_cotton import render_component

from apps.common.toasts import toast_sse
from apps.family_tree.actions.backup import BackupRefusedError, create_backup
from apps.family_tree.actions.tree_settings import choose_home_person, set_backup_dir
from apps.family_tree.domain.backup import format_size
from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Person
from apps.family_tree.readers.backup import backup_folder, last_backup
from apps.family_tree.readers.gedcom import gedcom_export
from apps.family_tree.readers.person import loose_people, person_list
from apps.family_tree.readers.tree_settings import home_person
from apps.family_tree.views.person_search import loose_events


def tree_settings_view(request: HttpRequest) -> HttpResponse:
    """
    The settings of the tree: who the home person is (#20), where backups go and the button making one (#33),
    and the GEDCOM export (#26).
    """
    return render(
        request,
        "family_tree/tree_settings.html",
        {
            "person_list": person_list(search=""),
            "loose_people": loose_people(),
            "last_backup": last_backup(),
            "home_person": home_person(),
            "backup_folder": backup_folder(),
        },
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


@require_POST
@datastar_response
def backup_dir_view(request: HttpRequest):
    """
    Saves the backup folder entered on the settings page (#33) and patches the section anew, with the space left
    in the folder now kept. A folder a backup would refuse is refused here with the same message, and the field
    keeps what was entered.
    """
    try:
        set_backup_dir(backup_dir=request.POST.get("backup_dir", ""))
    except BackupRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "settings.backup", backup_folder=backup_folder())
    )
    yield toast_sse(request=request, text="Passt. Der Sicherungsordner ist gespeichert.", style="success")


@require_POST
@datastar_response
def backup_view(request: HttpRequest):
    """
    "Jetzt sichern" (#33): writes a backup into the folder of the settings - the same "create_backup" as
    "manage.py backup", run within the request - and says where it went and how big it is. "Zuletzt gesichert"
    in the sidebar and the space left in the folder are patched anew; folders an earlier run left half-written
    are named, since a backup deletes nothing.
    """
    try:
        backup = create_backup(gedcom=gedcom_export())
    except BackupRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "backup.status", last_backup=last_backup())
    )
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "settings.backup", backup_folder=backup_folder())
    )
    yield toast_sse(
        request=request, text=f"Gesichert in {backup.path} ({format_size(size=backup.size)}).", style="success"
    )
    for folder in backup.incomplete:
        yield toast_sse(request=request, text=f"Unvollständig liegen geblieben: {folder}")
