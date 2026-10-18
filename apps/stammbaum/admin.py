from django.contrib import admin

from apps.stammbaum.models import Einstellung, ElternKind, Geschwister, Partnerschaft, Person


class ElternInline(admin.TabularInline):
    model = ElternKind
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
    fields = ("person_b", "art", "beginn", "ende")
    autocomplete_fields = ("person_b",)
    extra = 0


class PartnerschaftAlsBInline(admin.TabularInline):
    """
    The same partnerships seen from the other side: a pair is stored once, so a person is "person_b" in
    half of them.
    """

    model = Partnerschaft
    fk_name = "person_b"
    verbose_name_plural = "Partnerschaften (weitere)"
    fields = ("person_a", "art", "beginn", "ende")
    autocomplete_fields = ("person_a",)
    extra = 0


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "rufname", "geschlecht", "lebensstatus")
    list_filter = ("geschlecht", "lebensstatus")
    search_fields = ("vornamen", "familienname", "rufname")
    fields = ("vornamen", "familienname", "rufname", "geschlecht", "lebensstatus", "gedcom_roh")
    inlines = (ElternInline, KinderInline, PartnerschaftAlsAInline, PartnerschaftAlsBInline)


@admin.register(Partnerschaft)
class PartnerschaftAdmin(admin.ModelAdmin):
    list_display = ("__str__", "art", "beginn", "ende")
    list_filter = ("art",)
    search_fields = ("person_a__familienname", "person_a__vornamen", "person_b__familienname", "person_b__vornamen")
    autocomplete_fields = ("person_a", "person_b")


@admin.register(ElternKind)
class ElternKindAdmin(admin.ModelAdmin):
    list_display = ("__str__", "art", "partnerschaft")
    list_filter = ("art",)
    search_fields = ("kind__familienname", "kind__vornamen", "elternteil__familienname", "elternteil__vornamen")
    autocomplete_fields = ("elternteil", "kind", "partnerschaft")


@admin.register(Geschwister)
class GeschwisterAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    search_fields = ("person_a__familienname", "person_a__vornamen", "person_b__familienname", "person_b__vornamen")
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
