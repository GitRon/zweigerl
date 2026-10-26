import factory

from apps.family_tree.models import Tree


class TreeFactory(factory.django.DjangoModelFactory):
    """
    A tree under an invented name. Found by its name rather than made anew, so every row a factory builds lands in
    the same tree unless a test names another one - "TreeFactory(name="Familie Berger")" - see
    docs/patterns/testing-data.md. What else is passed is set on the tree found too, so
    "TreeFactory(home_person=lena)" makes Lena the home person of the tree she is already in.
    """

    name = "Familie Huber"

    class Meta:
        model = Tree
        django_get_or_create = ("name",)

    @classmethod
    def _get_or_create(cls, model_class, *args, **kwargs) -> Tree:
        tree = super()._get_or_create(model_class, *args, **kwargs)
        changed = {field: value for field, value in kwargs.items() if getattr(tree, field) != value}
        if changed:
            for field, value in changed.items():
                setattr(tree, field, value)
            tree.save()
        return tree
