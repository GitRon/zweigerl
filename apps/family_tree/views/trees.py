from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.trees import create_tree, rename_tree
from apps.family_tree.models import Tree


@require_POST
@datastar_response
def create_tree_view(request: HttpRequest):
    """
    Starts the tree named in the form - the first one of an installation, or another beside those there are (#34) -
    and opens it, empty and ready for its first person or an import. A name that is empty or taken is a toast, and
    the form keeps what was entered.
    """
    try:
        tree = create_tree(name=request.POST.get("name", ""))
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    toast_session(request=request, text=f"Passt. „{tree.name}“ ist angelegt.", style="success")
    yield ServerSentEventGenerator.redirect(reverse("family_tree:tree-view", kwargs={"tree_pk": tree.pk}))


@require_POST
@datastar_response
def rename_tree_view(request: HttpRequest, tree_pk: int):
    """
    Gives the tree the name entered on its settings page (#34). The page is loaded anew, since the name stands in
    the sidebar too and in the tab's title; a refusal is a toast, and the field keeps what was entered.
    """
    try:
        tree = rename_tree(tree_id=tree_pk, name=request.POST.get("name", ""))
    except Tree.DoesNotExist:
        yield toast_sse(request=request, text="Diesen Stammbaum gibt es nicht mehr.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    toast_session(request=request, text=f"Passt. Der Stammbaum heißt jetzt „{tree.name}“.", style="success")
    yield ServerSentEventGenerator.redirect(reverse("family_tree:tree-settings-view", kwargs={"tree_pk": tree.pk}))
