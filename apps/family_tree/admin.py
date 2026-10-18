from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair, TreeSettings

# Both pair models are found by either person's name.
PAIR_SEARCH_FIELDS = ("person_a__surname", "person_a__given_names", "person_b__surname", "person_b__given_names")


class ParentsFormSet(BaseInlineFormSet):
    """
    "ParentChild.clean" counts the birth parents already saved, so two new rows entered together with the
    saved ones would each pass on their own. Here the whole form is counted at once.
    """

    def clean(self):
        super().clean()
        birth_parents = [
            form
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("pedigree") == ParentChild.Pedigree.BIRTH
        ]
        if len(birth_parents) > ParentChild.MAX_BIRTH_PARENTS:
            raise ValidationError("Ein Kind hat höchstens zwei leibliche Eltern.")


class ParentsInline(admin.TabularInline):
    model = ParentChild
    formset = ParentsFormSet
    fk_name = "child"
    verbose_name = "Elternteil"
    verbose_name_plural = "Eltern"
    fields = ("parent", "partnership", "pedigree")
    autocomplete_fields = ("parent",)
    extra = 0


class ChildrenInline(admin.TabularInline):
    model = ParentChild
    fk_name = "parent"
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"
    fields = ("child", "partnership", "pedigree")
    autocomplete_fields = ("child",)
    extra = 0


class PartnershipAsAInline(admin.TabularInline):
    model = Partnership
    fk_name = "person_a"
    verbose_name_plural = "Partnerschaften"
    fields = ("person_b", "kind", "start", "end")
    autocomplete_fields = ("person_b",)
    extra = 0


class PartnershipAsBInline(PartnershipAsAInline):
    """
    The same partnerships seen from the other side: a pair is stored once, so a person is "person_b" in
    some of them.
    """

    fk_name = "person_b"
    verbose_name_plural = "Partnerschaften (als Partner eingetragen)"
    fields = ("person_a", "kind", "start", "end")
    autocomplete_fields = ("person_a",)
    extra = 0


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "call_name", "sex", "living_status")
    list_filter = ("sex", "living_status")
    search_fields = ("given_names", "surname", "call_name")
    fields = ("given_names", "surname", "call_name", "sex", "living_status", "gedcom_raw")
    inlines = (ParentsInline, ChildrenInline, PartnershipAsAInline, PartnershipAsBInline)


@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "start", "end")
    list_filter = ("kind",)
    search_fields = PAIR_SEARCH_FIELDS
    autocomplete_fields = ("person_a", "person_b")


@admin.register(ParentChild)
class ParentChildAdmin(admin.ModelAdmin):
    list_display = ("__str__", "pedigree", "partnership")
    list_filter = ("pedigree",)
    search_fields = ("child__surname", "child__given_names", "parent__surname", "parent__given_names")
    autocomplete_fields = ("parent", "child", "partnership")


@admin.register(SiblingPair)
class SiblingPairAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    search_fields = PAIR_SEARCH_FIELDS
    autocomplete_fields = ("person_a", "person_b")


@admin.register(TreeSettings)
class TreeSettingsAdmin(admin.ModelAdmin):
    """
    One row, primary key 1: it can be added while it does not exist and never deleted.
    """

    autocomplete_fields = ("home_person",)

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not TreeSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
