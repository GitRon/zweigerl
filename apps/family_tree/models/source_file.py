from pathlib import PurePosixPath

from django.db import models


class SourceFile(models.Model):
    """
    A scan or a PDF of a source (#15) - a birth certificate, a page of a parish register. The file is written
    only through "apps.common.media.store_upload", at "sources/<source-id>/<file-id>.<ext>", so the row comes
    first and its id names the file; see docs/patterns/data-storage.md, "Photos and scans".
    """

    source = models.ForeignKey(
        "family_tree.Source", verbose_name="Quelle", on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField("Datei", max_length=200)

    class Meta:
        verbose_name = "Datei einer Quelle"
        verbose_name_plural = "Dateien einer Quelle"
        ordering = ("pk",)

    def __str__(self) -> str:
        return self.file.name

    @property
    def storage_name(self) -> str:
        """
        Where the file goes in the media directory, without its extension - from ids alone, never from a name.
        """
        return f"sources/{self.source_id}/{self.pk}"

    @property
    def format_name(self) -> str:
        """
        The kind of file, as a person recognises it from the extension: "PDF", "JPG", "TIF".
        """
        return PurePosixPath(self.file.name).suffix.lstrip(".").upper()
