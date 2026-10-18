import datetime

from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate, sort_date


class Photo(ValidateConstraintsOnSaveMixin, models.Model):
    """
    A photo of one or more people (#16), with what it shows and when it was taken. The file is written only
    through "apps.common.media.store_upload", at "photos/<photo-id>/original.<ext>", and kept as it came: the
    picture frame shows a 3:4 section of it without cutting the file. See docs/patterns/data-storage.md.
    """

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

    file = models.FileField("Datei", max_length=200)
    description = models.TextField("Beschreibung", blank=True)
    # When it was taken, as the uncertain date of docs/patterns/evidence.md - "um 1950" is what most old
    # photos have. The date the camera wrote fills it in on upload.
    date_kind = models.CharField("Aufnahmedatum: Art", max_length=10, choices=DateKindChoice, blank=True)
    date_1 = models.DateField("Aufnahmedatum", null=True, blank=True)
    date_2 = models.DateField("Aufnahmedatum bis", null=True, blank=True, help_text="Nur bei „zwischen“")
    precision = models.CharField("Aufnahmedatum: Genauigkeit", max_length=5, choices=PrecisionChoice, blank=True)
    # Derived in "clean" and "save", like the sort date of a fact.
    sort_date = models.DateField("Sortierdatum", null=True, blank=True, editable=False)
    people = models.ManyToManyField(
        "family_tree.Person", verbose_name="Personen", through="family_tree.PhotoPerson", related_name="photos"
    )

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = (models.F("sort_date").asc(nulls_last=True), "pk")
        constraints = (
            models.CheckConstraint(
                condition=models.Q(date_1__isnull=True, date_2__isnull=True, date_kind="", precision="")
                | models.Q(
                    date_1__isnull=False,
                    date_kind__in=("exact", "about", "before", "after", "between"),
                    precision__in=("day", "month", "year"),
                ),
                name="photo_date_complete",
                violation_error_message="Ein Aufnahmedatum braucht seine Art und seine Genauigkeit.",
            ),
            models.CheckConstraint(
                condition=models.Q(date_1__isnull=True, sort_date__isnull=True)
                | models.Q(date_1__isnull=False, sort_date__isnull=False),
                name="photo_sort_date_with_date",
                violation_error_message="Ein Aufnahmedatum braucht sein Sortierdatum.",
            ),
            models.CheckConstraint(
                condition=models.Q(date_kind="between", date_2__isnull=False, date_2__gte=models.F("date_1"))
                | (~models.Q(date_kind="between") & models.Q(date_2__isnull=True)),
                name="photo_date_2_only_between",
                violation_error_message=(
                    "Ein zweites Datum gibt es nur bei „zwischen“, und es liegt nicht vor dem ersten."
                ),
            ),
        )

    def __str__(self) -> str:
        return self.file.name

    def save(self, *args, **kwargs) -> None:
        self.sort_date = self._sort_date()
        # A save limited to some fields would otherwise leave the old sort date behind a changed date.
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "sort_date"}
        super().save(*args, **kwargs)

    def clean(self) -> None:
        self.sort_date = self._sort_date()

    @property
    def storage_name(self) -> str:
        """
        Where the uploaded file goes in the media directory, without its extension - from the id alone, never
        from a name.
        """
        return f"photos/{self.pk}/original"

    @property
    def date(self) -> UncertainDate | None:
        """
        The structured date it was taken, or None while nobody knows - or for an incomplete one, which the
        constraints refuse on save.
        """
        if self.date_1 is None or not self.date_kind or not self.precision:
            return None
        if self.date_kind == DateKind.BETWEEN and self.date_2 is None:
            return None
        return UncertainDate(
            kind=DateKind(self.date_kind), date_1=self.date_1, date_2=self.date_2, precision=Precision(self.precision)
        )

    def set_date(self, *, date: UncertainDate | None) -> None:
        """
        Fills in the fields of the date it was taken, or empties them for None.
        """
        self.date_kind = date.kind if date else ""
        self.date_1 = date.date_1 if date else None
        self.date_2 = date.date_2 if date else None
        self.precision = date.precision if date else ""

    def _sort_date(self) -> datetime.date | None:
        date = self.date
        return sort_date(date=date) if date else None


class PhotoPerson(ValidateConstraintsOnSaveMixin, models.Model):
    """
    Somebody on a photo (#16). One of a person's photos may be their portrait - the Titelbild their picture
    frame shows everywhere.
    """

    photo = models.ForeignKey(Photo, verbose_name="Foto", on_delete=models.CASCADE, related_name="person_links")
    person = models.ForeignKey(
        "family_tree.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="photo_links"
    )
    is_portrait = models.BooleanField("Titelbild", default=False)

    class Meta:
        verbose_name = "Person auf einem Foto"
        verbose_name_plural = "Personen auf einem Foto"
        ordering = ("pk",)
        constraints = (
            models.UniqueConstraint(
                fields=("photo", "person"),
                name="photoperson_once",
                violation_error_message="Diese Person ist auf dem Foto schon eingetragen.",
            ),
            models.UniqueConstraint(
                fields=("person",),
                condition=models.Q(is_portrait=True),
                name="photoperson_one_portrait",
                violation_error_message="Eine Person hat höchstens ein Titelbild.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.person} auf {self.photo}"
