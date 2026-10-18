from apps.stammbaum.models import Einstellung, Person


def ausgangsperson() -> Person | None:
    """
    The person the tree is laid out around, or None while nobody has been chosen.
    """
    einstellung = Einstellung.objects.select_related("ausgangsperson").filter(pk=Einstellung.EINZIGE_ZEILE).first()
    return einstellung.ausgangsperson if einstellung else None
