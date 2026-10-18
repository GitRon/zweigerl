import datetime

from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.core.exceptions import ValidationError
from django.db import models

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate, sort_date
from apps.family_tree.models.gedcom import GedcomRawMixin

# Which kinds carry a date, which a value, and which belong to a couple rather than a person - see
# docs/patterns/evidence.md, "One value per fact". Module-level so the constraints below can use them: a
# nested Meta cannot see the enclosing class.
DATE_KINDS = ("birth", "baptism", "death", "burial", "marriage", "divorce")
VALUE_KINDS = ("birthplace", "occupation", "residence", "education", "nationality")
COUPLE_KINDS = ("marriage", "divorce")
CUSTOM = "custom"
PERSON_KINDS = tuple(kind for kind in (*DATE_KINDS, *VALUE_KINDS) if kind not in COUPLE_KINDS)


class Fact(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    One fact about a person or a couple - an Angabe - with how sure it is. See docs/patterns/evidence.md. One
    value per fact: a birth date and a birthplace are two, each with its own reliability and its own citations.
    """

    class Kind(models.TextChoices):
        # GEDCOM: BIRT DATE, CHR/BAPM DATE, DEAT DATE, BURI DATE, BIRT PLAC, OCCU, RESI PLAC, EDUC, NATI,
        # MARR DATE and DIV DATE on the FAM, EVEN/FACT with TYPE for "custom"
        BIRTH = "birth", "Geboren"
        BAPTISM = "baptism", "Getauft"
        DEATH = "death", "Gestorben"
        BURIAL = "burial", "Begräbnis"
        BIRTHPLACE = "birthplace", "Geburtsort"
        OCCUPATION = "occupation", "Beruf"
        RESIDENCE = "residence", "Wohnort"
        EDUCATION = "education", "Ausbildung"
        NATIONALITY = "nationality", "Staatsbürgerschaft"
        MARRIAGE = "marriage", "Geheiratet"
        DIVORCE = "divorce", "Geschieden"
        CUSTOM = "custom", "Eigene"

    class Reliability(models.TextChoices):
        DOCUMENTED = "documented", "belegt"
        PROBABLE = "probable", "wahrscheinlich"
        HANDED_DOWN = "handed_down", "überliefert"

    class DateKindChoice(models.TextChoices):
        EXACT = DateKind.EXACT, "genau"
        ABOUT = DateKind.ABOUT, "ungefähr"
        BEFORE = DateKind.BEFORE, "vor"
        AFTER = DateKind.AFTER, "nach"
        BETWEEN = DateKind.BETWEEN, "zwischen"

    class PrecisionChoice(models.TextChoices):
        DAY = Precision.DAY, "Tag"
        MONTH = Precision.MONTH, "Monat"
        YEAR = Precision.YEAR, "Jahr"

    # Exactly one of the two - a constraint holds it.
    person = models.ForeignKey(
        "family_tree.Person",
        verbose_name="Person",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="facts",
    )
    partnership = models.ForeignKey(
        "family_tree.Partnership",
        verbose_name="Partnerschaft",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="facts",
    )
    kind = models.CharField("Art", max_length=30, choices=Kind)
    label = models.CharField(
        "Bezeichnung", max_length=100, blank=True, help_text="Nur bei „Eigene“: wie die Angabe heißt"
    )
    value = models.CharField("Wert", max_length=300, blank=True, help_text="Ort, Beruf, … - nicht bei Datumsangaben")
    # The uncertain date of docs/patterns/evidence.md: a month or a year is stored as its first day.
    date_kind = models.CharField("Datum: Art", max_length=10, choices=DateKindChoice, blank=True)
    date_1 = models.DateField("Datum", null=True, blank=True)
    date_2 = models.DateField("Datum bis", null=True, blank=True, help_text="Nur bei „zwischen“")
    precision = models.CharField("Datum: Genauigkeit", max_length=5, choices=PrecisionChoice, blank=True)
    # Derived in "clean" and "save" - see "domain.dates.sort_date". Something writing past both sets it itself.
    sort_date = models.DateField("Sortierdatum", null=True, blank=True, editable=False)
    reliability = models.CharField(
        "Verlässlichkeit", max_length=15, choices=Reliability, default=Reliability.DOCUMENTED
    )

    class Meta:
        verbose_name = "Angabe"
        verbose_name_plural = "Angaben"
        ordering = (models.F("sort_date").asc(nulls_last=True), "kind", "pk")
        constraints = (
            models.CheckConstraint(
                condition=models.Q(person__isnull=False, partnership__isnull=True)
                | models.Q(person__isnull=True, partnership__isnull=False),
                name="fact_one_owner",
                violation_error_message="Eine Angabe gehört entweder zu einer Person oder zu einer Partnerschaft.",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=(*DATE_KINDS, *VALUE_KINDS, CUSTOM)),
                name="fact_kind_valid",
                violation_error_message="Diese Art von Angabe kennt Zweigerl nicht.",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=COUPLE_KINDS, partnership__isnull=False)
                | models.Q(kind__in=PERSON_KINDS, person__isnull=False)
                | models.Q(kind=CUSTOM),
                name="fact_kind_matches_owner",
                violation_error_message=(
                    "Heirat und Scheidung gehören zur Partnerschaft, alle anderen Angaben zur Person."
                ),
            ),
            models.CheckConstraint(
                condition=~models.Q(kind__in=DATE_KINDS) | models.Q(date_1__isnull=False, value=""),
                name="fact_date_kind_has_date",
                violation_error_message="Diese Angabe ist ein Datum und braucht eines, aber keinen Wert.",
            ),
            models.CheckConstraint(
                condition=~models.Q(kind__in=VALUE_KINDS) | (models.Q(date_1__isnull=True) & ~models.Q(value="")),
                name="fact_value_kind_has_value",
                violation_error_message="Diese Angabe braucht einen Wert, aber kein Datum.",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind=CUSTOM) & ~models.Q(label="") & (~models.Q(value="") | models.Q(date_1__isnull=False))
                )
                | (~models.Q(kind=CUSTOM) & models.Q(label="")),
                name="fact_custom_has_label",
                violation_error_message="Eine eigene Angabe braucht eine Bezeichnung und einen Wert oder ein Datum.",
            ),
            models.CheckConstraint(
                condition=models.Q(date_1__isnull=True, date_2__isnull=True, date_kind="", precision="")
                | models.Q(
                    date_1__isnull=False,
                    date_kind__in=("exact", "about", "before", "after", "between"),
                    precision__in=("day", "month", "year"),
                ),
                name="fact_date_complete",
                violation_error_message="Ein Datum braucht seine Art und seine Genauigkeit.",
            ),
            # Derived, so no form shows it: "clean" and "save" set it, this holds whatever writes past both.
            models.CheckConstraint(
                condition=models.Q(date_1__isnull=True, sort_date__isnull=True)
                | models.Q(date_1__isnull=False, sort_date__isnull=False),
                name="fact_sort_date_with_date",
                violation_error_message="Ein Datum braucht sein Sortierdatum.",
            ),
            models.CheckConstraint(
                condition=models.Q(date_kind="between", date_2__isnull=False, date_2__gte=models.F("date_1"))
                | (~models.Q(date_kind="between") & models.Q(date_2__isnull=True)),
                name="fact_date_2_only_between",
                violation_error_message=(
                    "Ein zweites Datum gibt es nur bei „zwischen“, und es liegt nicht vor dem ersten."
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(reliability__in=("documented", "probable", "handed_down")),
                name="fact_reliability_valid",
                violation_error_message="Eine Angabe ist belegt, wahrscheinlich oder überliefert.",
            ),
        )

    def __str__(self) -> str:
        label = self.label or self.get_kind_display()
        return f"{label}: {self.value or self.date_1}"

    def clean(self) -> None:
        """
        Derives the sort date, and checks again in Python the one rule a form cannot: an admin inline leaves
        the foreign key it hangs on out of the form, so "fact_kind_matches_owner" would only surface in
        "save" - as a 500 instead of a message.
        """
        self.sort_date = self._sort_date()
        if self.kind in COUPLE_KINDS and not self._has_owner(field="partnership"):
            raise ValidationError({"kind": "Heirat und Scheidung gehören zur Partnerschaft, nicht zur Person."})
        if self.kind in PERSON_KINDS and not self._has_owner(field="person"):
            raise ValidationError({"kind": "Diese Angabe gehört zu einer Person, nicht zur Partnerschaft."})

    def save(self, *args, **kwargs) -> None:
        self.sort_date = self._sort_date()
        # A save limited to some fields would otherwise leave the old sort date behind a changed date.
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "sort_date"}
        super().save(*args, **kwargs)

    @property
    def date(self) -> UncertainDate | None:
        """
        The structured date, or None for a fact without one - or with an incomplete one, which the
        constraints refuse on save.
        """
        if self.date_1 is None or not self.date_kind or not self.precision:
            return None
        if self.date_kind == DateKind.BETWEEN and self.date_2 is None:
            return None
        return UncertainDate(
            kind=DateKind(self.date_kind), date_1=self.date_1, date_2=self.date_2, precision=Precision(self.precision)
        )

    @property
    def is_undocumented(self) -> bool:
        """
        Marked documented without a single citation - "unbelegt", derived and never stored. See
        docs/patterns/evidence.md.
        """
        # "all()" rather than "exists()", so a list loaded with its citations prefetched asks nothing more.
        return self.reliability == self.Reliability.DOCUMENTED and not self.citations.all()

    def _sort_date(self) -> datetime.date | None:
        date = self.date
        return sort_date(date=date) if date else None

    def _has_owner(self, *, field: str) -> bool:
        # The id while the row is saved, the cached object while an admin form still holds an unsaved parent.
        return (
            getattr(self, f"{field}_id") is not None
            or self._meta.get_field(field).get_cached_value(self, None) is not None
        )
