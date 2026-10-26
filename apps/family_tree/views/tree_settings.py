from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django_cotton import render_component

from apps.common.toasts import toast_sse
from apps.family_tree.actions.backup import BackupRefusedError, create_backup
from apps.family_tree.actions.installation_settings import set_backup_dir
from apps.family_tree.actions.trees import choose_home_person
from apps.family_tree.domain.backup import format_size
from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Person
from apps.family_tree.readers.backup import backup_folder, last_backup
from apps.family_tree.readers.gedcom import gedcom_exports
from apps.family_tree.readers.gedcom_import import tree_is_empty
from apps.family_tree.readers.trees import home_person, open_tree
from apps.family_tree.views.person_search import loose_events
from apps.family_tree.views.start import sidebar_context


def tree_settings_view(request: HttpRequest, tree_pk: int) -> HttpResponse:
    """
    The settings of the tree: its name and a new tree beside it (#34), who the home person is (#20), the GEDCOM export
    (#26) and import (#25) - and where backups of every tree go, with the button making one (#33).
    """
    opened = open_tree(pk=tree_pk)
    if opened is None:
        raise Http404

    return render(
        request,
        "family_tree/tree_settings.html",
        {
            **sidebar_context(opened=opened),
            "home_person": home_person(tree_id=tree_pk),
            "backup_folder": backup_folder(),
            "tree_empty": tree_is_empty(tree_id=tree_pk),
        },
    )


@require_POST
@datastar_response
def home_person_view(request: HttpRequest, tree_pk: int):
    """
    Saves the home person chosen on the settings page and confirms it with a toast. The form stays as it is:
    it already shows the choice. Who hangs loose follows the new home person, so the sidebar's "Lose Zweigerl"
    are patched anew (#76).
    """
    try:
        person = choose_home_person(tree_id=tree_pk, person_id=int(request.POST.get("home_person", ""))).home_person
    except ValueError, Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return

    yield from loose_events(request, tree_id=tree_pk)
    name = display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name)
    yield toast_sse(request=request, text=f"Passt. {name} ist jetzt die Ausgangsperson.", style="success")


@require_POST
@datastar_response
def backup_dir_view(request: HttpRequest, tree_pk: int):
    """
    Saves the backup folder entered on the settings page of a tree (#33) - one for all trees - and patches the
    section anew, with the space left
    in the folder now kept. A folder a backup would refuse is refused here with the same message, and the field
    keeps what was entered.
    """
    try:
        set_backup_dir(backup_dir=request.POST.get("backup_dir", ""))
    except BackupRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "settings.backup", backup_folder=backup_folder(), tree_id=tree_pk)
    )
    yield toast_sse(request=request, text="Passt. Der Sicherungsordner ist gespeichert.", style="success")


@require_POST
@datastar_response
def backup_view(request: HttpRequest, tree_pk: int):
    """
    "Jetzt sichern" (#33): writes a backup of every tree into the folder of the settings - the same "create_backup"
    as "manage.py backup", run within the request - and says where it went and how big it is. "Zuletzt gesichert"
    in the sidebar of the tree the button was pressed in and the space left in the folder are patched anew; folders
    an earlier run left half-written are named, since a backup deletes nothing.
    """
    try:
        backup = create_backup(gedcoms=gedcom_exports())
    except BackupRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "backup.status", last_backup=last_backup(), tree_id=tree_pk)
    )
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "settings.backup", backup_folder=backup_folder(), tree_id=tree_pk)
    )
    yield toast_sse(
        request=request, text=f"Gesichert in {backup.path} ({format_size(size=backup.size)}).", style="success"
    )
    for folder in backup.incomplete:
        yield toast_sse(request=request, text=f"Unvollständig liegen geblieben: {folder}")
