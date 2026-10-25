import factory

from apps.family_tree.models import Note
from apps.family_tree.tests.factories.person import PersonFactory


class NoteFactory(factory.django.DjangoModelFactory):
    person = factory.SubFactory(PersonFactory)
    text = "Laut Tante Resi war er zwei Jahre in Amerika - im Passagierregister suchen."

    class Meta:
        model = Note
