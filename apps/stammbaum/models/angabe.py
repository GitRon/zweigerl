import datetime

from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.core.exceptions import ValidationError
from django.db import models

from apps.stammbaum.domain.datum import DatumArt, Genauigkeit, UnscharfesDatum, sortierdatum
from apps.stammbaum.models.gedcom import GedcomRohMixin

# Which kinds carry a date, which a value, and which belong to a couple rather than a person - see
# docs/patterns/belege.md, "Angabe". Module-level so the constraints below can use them: a nested Meta
# cannot see the enclosing class.
DATUMS_ARTEN = ("geboren", "getauft", "gestorben", "begraebnis", "geheiratet", "geschieden")
WERT_ARTEN = ("geburtsort", "beruf", "wohnort", "ausbildung", "staatsbuergerschaft")
PAAR_ARTEN = ("geheiratet", "geschieden")
EIGENE = "eigene"
PERSONEN_ARTEN = tuple(art for art in (*DATUMS_ARTEN, *WERT_ARTEN) if art not in PAAR_ARTEN)


class Angabe(ValidateConstraintsOnSaveMixin, GedcomRohMixin):
    """
    One fact about a person or a couple, with how sure it is - see docs/patterns/belege.md. One value per
    Angabe: a birth date and a birthplace are two, each with its own reliability and its own Zitate.
    """

    class Art(models.TextChoices):
        # GEDCOM: BIRT DATE, CHR/BAPM DATE, DEAT DATE, BURI DATE, BIRT PLAC, OCCU, RESI PLAC, EDUC, NATI,
        # MARR DATE and DIV DATE on the FAM, EVEN/FACT with TYPE for "eigene"
        GEBOREN = "geboren", "Geboren"
        GETAUFT = "getauft", "Getauft"
        GESTORBEN = "gestorben", "Gestorben"
        BEGRAEBNIS = "begraebnis", "Begräbnis"
        GEBURTSORT = "geburtsort", "Geburtsort"
        BERUF = "beruf", "Beruf"
        WOHNORT = "wohnort", "Wohnort"
        AUSBILDUNG = "ausbildung", "Ausbildung"
        STAATSBUERGERSCHAFT = "staatsbuergerschaft", "Staatsbürgerschaft"
        GEHEIRATET = "geheiratet", "Geheiratet"
        GESCHIEDEN = "geschieden", "Geschieden"
        EIGENE = "eigene", "Eigene"

    class Verlaesslichkeit(models.TextChoices):
        BELEGT = "belegt", "belegt"
        WAHRSCHEINLICH = "wahrscheinlich", "wahrscheinlich"
        UEBERLIEFERT = "ueberliefert", "überliefert"

    class DatumsArt(models.TextChoices):
        GENAU = DatumArt.GENAU, "genau"
        UNGEFAEHR = DatumArt.UNGEFAEHR, "ungefähr"
        VOR = DatumArt.VOR, "vor"
        NACH = DatumArt.NACH, "nach"
        ZWISCHEN = DatumArt.ZWISCHEN, "zwischen"

    class DatumsGenauigkeit(models.TextChoices):
        TAG = Genauigkeit.TAG, "Tag"
        MONAT = Genauigkeit.MONAT, "Monat"
        JAHR = Genauigkeit.JAHR, "Jahr"

    # Exactly one of the two - a constraint holds it.
    person = models.ForeignKey(
        "stammbaum.Person",
        verbose_name="Person",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="angaben",
    )
    partnerschaft = models.ForeignKey(
        "stammbaum.Partnerschaft",
        verbose_name="Partnerschaft",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="angaben",
    )
    art = models.CharField("Art", max_length=30, choices=Art)
    bezeichnung = models.CharField(
        "Bezeichnung", max_length=100, blank=True, help_text="Nur bei „Eigene“: wie die Angabe heißt"
    )
    wert = models.CharField("Wert", max_length=300, blank=True, help_text="Ort, Beruf, … - nicht bei Datumsangaben")
    # The uncertain date of docs/patterns/belege.md: a month or a year is stored as its first day.
    datum_art = models.CharField("Datum: Art", max_length=10, choices=DatumsArt, blank=True)
    datum_1 = models.DateField("Datum", null=True, blank=True)
    datum_2 = models.DateField("Datum bis", null=True, blank=True, help_text="Nur bei „zwischen“")
    genauigkeit = models.CharField("Datum: Genauigkeit", max_length=5, choices=DatumsGenauigkeit, blank=True)
    # Derived in "save" - see "domain.datum.sortierdatum". Something writing past "save" sets it itself.
    sortierdatum = models.DateField("Sortierdatum", null=True, blank=True, editable=False)
    verlaesslichkeit = models.CharField(
        "Verlässlichkeit", max_length=15, choices=Verlaesslichkeit, default=Verlaesslichkeit.BELEGT
    )

    class Meta:
        verbose_name = "Angabe"
        verbose_name_plural = "Angaben"
        ordering = (models.F("sortierdatum").asc(nulls_last=True), "art", "pk")
        constraints = (
            models.CheckConstraint(
                condition=models.Q(person__isnull=False, partnerschaft__isnull=True)
                | models.Q(person__isnull=True, partnerschaft__isnull=False),
                name="angabe_genau_ein_bezug",
                violation_error_message="Eine Angabe gehört entweder zu einer Person oder zu einer Partnerschaft.",
            ),
            models.CheckConstraint(
                condition=models.Q(art__in=(*DATUMS_ARTEN, *WERT_ARTEN, EIGENE)),
                name="angabe_art_gueltig",
                violation_error_message="Diese Art von Angabe kennt Zweigerl nicht.",
            ),
            models.CheckConstraint(
                condition=models.Q(art__in=PAAR_ARTEN, partnerschaft__isnull=False)
                | models.Q(art__in=PERSONEN_ARTEN, person__isnull=False)
                | models.Q(art=EIGENE),
                name="angabe_art_passt_zum_bezug",
                violation_error_message=(
                    "Heirat und Scheidung gehören zur Partnerschaft, alle anderen Angaben zur Person."
                ),
            ),
            models.CheckConstraint(
                condition=~models.Q(art__in=DATUMS_ARTEN) | models.Q(datum_1__isnull=False, wert=""),
                name="angabe_datumsart_hat_datum",
                violation_error_message="Diese Angabe ist ein Datum und braucht eines, aber keinen Wert.",
            ),
            models.CheckConstraint(
                condition=~models.Q(art__in=WERT_ARTEN) | (models.Q(datum_1__isnull=True) & ~models.Q(wert="")),
                name="angabe_wertart_hat_wert",
                violation_error_message="Diese Angabe braucht einen Wert, aber kein Datum.",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(art=EIGENE)
                    & ~models.Q(bezeichnung="")
                    & (~models.Q(wert="") | models.Q(datum_1__isnull=False))
                )
                | (~models.Q(art=EIGENE) & models.Q(bezeichnung="")),
                name="angabe_eigene_hat_bezeichnung",
                violation_error_message="Eine eigene Angabe braucht eine Bezeichnung und einen Wert oder ein Datum.",
            ),
            models.CheckConstraint(
                condition=models.Q(datum_1__isnull=True, datum_2__isnull=True, datum_art="", genauigkeit="")
                | models.Q(
                    datum_1__isnull=False,
                    datum_art__in=("genau", "ungefaehr", "vor", "nach", "zwischen"),
                    genauigkeit__in=("tag", "monat", "jahr"),
                ),
                name="angabe_datum_vollstaendig",
                violation_error_message="Ein Datum braucht seine Art und seine Genauigkeit.",
            ),
            # Derived, so no form shows it: "clean" and "save" set it, this holds whatever writes past both.
            models.CheckConstraint(
                condition=models.Q(datum_1__isnull=True, sortierdatum__isnull=True)
                | models.Q(datum_1__isnull=False, sortierdatum__isnull=False),
                name="angabe_sortierdatum_mit_datum",
                violation_error_message="Ein Datum braucht sein Sortierdatum.",
            ),
            models.CheckConstraint(
                condition=models.Q(datum_art="zwischen", datum_2__isnull=False, datum_2__gte=models.F("datum_1"))
                | (~models.Q(datum_art="zwischen") & models.Q(datum_2__isnull=True)),
                name="angabe_datum_bis_nur_bei_zwischen",
                violation_error_message=(
                    "Ein zweites Datum gibt es nur bei „zwischen“, und es liegt nicht vor dem ersten."
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(verlaesslichkeit__in=("belegt", "wahrscheinlich", "ueberliefert")),
                name="angabe_verlaesslichkeit_gueltig",
                violation_error_message="Eine Angabe ist belegt, wahrscheinlich oder überliefert.",
            ),
        )

    def __str__(self) -> str:
        bezeichnung = self.bezeichnung or self.get_art_display()
        return f"{bezeichnung}: {self.wert or self.datum_1}"

    def clean(self) -> None:
        """
        Derives the sort date, and checks again in Python the one rule a form cannot: an admin inline leaves
        the foreign key it hangs on out of the form, so "angabe_art_passt_zum_bezug" would only surface in
        "save" - as a 500 instead of a message.
        """
        self.sortierdatum = self._sortierdatum()
        if self.art in PAAR_ARTEN and not self._hat_bezug(feld="partnerschaft"):
            raise ValidationError({"art": "Heirat und Scheidung gehören zur Partnerschaft, nicht zur Person."})
        if self.art in PERSONEN_ARTEN and not self._hat_bezug(feld="person"):
            raise ValidationError({"art": "Diese Angabe gehört zu einer Person, nicht zur Partnerschaft."})

    def save(self, *args, **kwargs) -> None:
        self.sortierdatum = self._sortierdatum()
        # A save limited to some fields would otherwise leave the old sort date behind a changed date.
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "sortierdatum"}
        super().save(*args, **kwargs)

    def _sortierdatum(self) -> datetime.date | None:
        datum = self.datum
        return sortierdatum(datum=datum) if datum else None

    def _hat_bezug(self, *, feld: str) -> bool:
        # The id while the row is saved, the cached object while an admin form still holds an unsaved parent.
        return (
            getattr(self, f"{feld}_id") is not None
            or self._meta.get_field(feld).get_cached_value(self, None) is not None
        )

    @property
    def datum(self) -> UnscharfesDatum | None:
        """
        The structured date, or None for an Angabe without one - or with an incomplete one, which the
        constraints refuse on save.
        """
        if self.datum_1 is None or not self.datum_art or not self.genauigkeit:
            return None
        if self.datum_art == DatumArt.ZWISCHEN and self.datum_2 is None:
            return None
        return UnscharfesDatum(
            art=DatumArt(self.datum_art),
            datum_1=self.datum_1,
            datum_2=self.datum_2,
            genauigkeit=Genauigkeit(self.genauigkeit),
        )

    @property
    def ist_unbelegt(self) -> bool:
        """
        Marked "belegt" without a single Zitat - derived, never stored. See docs/patterns/belege.md.
        """
        # "all()" rather than "exists()", so a list loaded with its Zitate prefetched asks nothing more.
        return self.verlaesslichkeit == self.Verlaesslichkeit.BELEGT and not self.zitate.all()
