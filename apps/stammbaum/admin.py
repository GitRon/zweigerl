from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from apps.stammbaum.models import Angabe, Einstellung, ElternKind, Geschwister, Partnerschaft, Person, Quelle, Zitat

# Both pair models are found by either person's name.
PAAR_SUCHFELDER = ("person_a__familienname", "person_a__vornamen", "person_b__familienname", "person_b__vornamen")


class ElternFormSet(BaseInlineFormSet):
    """
    "ElternKind.clean" counts the birth parents already saved, so two new rows entered together with the
    saved ones would each pass on their own. Here the whole form is counted at once.
    """

    def clean(self):
        super().clean()
        leibliche = [
            form
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("art") == ElternKind.Art.LEIBLICH
        ]
        if len(leibliche) > ElternKind.MAX_LEIBLICHE_ELTERN:
            raise ValidationError("Ein Kind hat höchstens zwei leibliche Eltern.")


class ElternInline(admin.TabularInline):
    model = ElternKind
    formset = ElternFormSet
    fk_name = "kind"
    verbose_name = "Elternteil"
    verbose_name_plural = "Eltern"
    fields = ("elternteil", "partnerschaft", "art")
    autocomplete_fields = ("elternteil",)
    extra = 0


class KinderInline(admin.TabularInline):
    model = ElternKind
    fk_name = "elternteil"
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"
    fields = ("kind", "partnerschaft", "art")
    autocomplete_fields = ("kind",)
    extra = 0


class PartnerschaftAlsAInline(admin.TabularInline):
    model = Partnerschaft
    fk_name = "person_a"
    verbose_name_plural = "Partnerschaften"
    fields = ("person_b", "art")
    show_change_link = True
    autocomplete_fields = ("person_b",)
    extra = 0


class PartnerschaftAlsBInline(PartnerschaftAlsAInline):
    """
    The same partnerships seen from the other side: a pair is stored once, so a person is "person_b" in
    some of them.
    """

    fk_name = "person_b"
    verbose_name_plural = "Partnerschaften (als Partner eingetragen)"
    fields = ("person_a", "art")
    autocomplete_fields = ("person_a",)
    extra = 0


class AngabeInline(admin.TabularInline):
    """
    The Angaben of a person or a couple. Their Zitate are on the Angabe's own page, one click away.
    """

    model = Angabe
    fields = ("art", "bezeichnung", "wert", "datum_art", "datum_1", "datum_2", "genauigkeit", "verlaesslichkeit")
    show_change_link = True
    extra = 0


class ZitatInline(admin.TabularInline):
    model = Zitat
    fields = ("quelle", "stelle")
    autocomplete_fields = ("quelle",)
    extra = 0


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "rufname", "geschlecht", "lebensstatus")
    list_filter = ("geschlecht", "lebensstatus")
    search_fields = ("vornamen", "familienname", "rufname")
    fields = ("vornamen", "familienname", "rufname", "geschlecht", "lebensstatus", "gedcom_roh")
    inlines = (AngabeInline, ElternInline, KinderInline, PartnerschaftAlsAInline, PartnerschaftAlsBInline)


@admin.register(Partnerschaft)
class PartnerschaftAdmin(admin.ModelAdmin):
    list_display = ("__str__", "art")
    list_filter = ("art",)
    search_fields = PAAR_SUCHFELDER
    autocomplete_fields = ("person_a", "person_b")
    inlines = (AngabeInline,)


@admin.register(ElternKind)
class ElternKindAdmin(admin.ModelAdmin):
    list_display = ("__str__", "art", "partnerschaft")
    list_filter = ("art",)
    search_fields = ("kind__familienname", "kind__vornamen", "elternteil__familienname", "elternteil__vornamen")
    autocomplete_fields = ("elternteil", "kind", "partnerschaft")


@admin.register(Geschwister)
class GeschwisterAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    search_fields = PAAR_SUCHFELDER
    autocomplete_fields = ("person_a", "person_b")


@admin.register(Einstellung)
class EinstellungAdmin(admin.ModelAdmin):
    """
    One row, primary key 1: it can be added while it does not exist and never deleted.
    """

    autocomplete_fields = ("ausgangsperson",)

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not Einstellung.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Angabe)
class AngabeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "person", "partnerschaft", "verlaesslichkeit")
    list_filter = ("art", "verlaesslichkeit")
    search_fields = ("person__familienname", "person__vornamen", "wert", "bezeichnung")
    autocomplete_fields = ("person", "partnerschaft")
    fields = (
        "person",
        "partnerschaft",
        "art",
        "bezeichnung",
        "wert",
        "datum_art",
        "datum_1",
        "datum_2",
        "genauigkeit",
        "verlaesslichkeit",
        "gedcom_roh",
    )
    inlines = (ZitatInline,)


@admin.register(Quelle)
class QuelleAdmin(admin.ModelAdmin):
    list_display = ("titel", "art")
    list_filter = ("art",)
    search_fields = ("titel", "beschreibung")
    autocomplete_fields = ("personen",)


@admin.register(Zitat)
class ZitatAdmin(admin.ModelAdmin):
    list_display = ("__str__", "stelle")
    search_fields = ("quelle__titel", "stelle")
    autocomplete_fields = ("angabe", "quelle")
