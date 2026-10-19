from collections.abc import Iterable

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import ProtectedError

from apps.common.media import delete_on_commit, store_upload
from apps.family_tree.models import Person, Source, SourceFile


def create_source(*, person_id: int, title: str, kind: str, description: str, files: Iterable[UploadedFile]) -> Source:
    """
    Creates a source filed with the person, with its scans and PDFs (#15). Raises "Person.DoesNotExist" for
    somebody no longer in the tree, "ValidationError" for a source without a title or of an unknown kind and
    "UploadRefusedError" for a file Zweigerl does not keep - each leaving nothing behind.
    """
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        source = Source(title=title.strip(), kind=kind, description=description.strip())
        source.save()
        source.people.add(person)
        _store_files(source=source, files=files)

    return source


def add_source_files(*, source_id: int, files: Iterable[UploadedFile]) -> list[SourceFile]:
    """
    Attaches more scans or PDFs to a source. Raises "Source.DoesNotExist" for a source deleted in the meantime
    and "UploadRefusedError" for a file Zweigerl does not keep, then attaching none of them.
    """
    with transaction.atomic():
        source = Source.objects.get(pk=source_id)
        return _store_files(source=source, files=files)


def delete_source(*, source_id: int) -> Source:
    """
    Deletes a source with its scans and PDFs (#72), the files once the deletion is committed. Raises
    "Source.DoesNotExist" for a source already gone and "ValidationError" for one a fact still cites - its
    facts would quietly turn unbelegt; see docs/patterns/evidence.md.
    """
    with transaction.atomic():
        source = Source.objects.get(pk=source_id)
        names = [source_file.file.name for source_file in source.files.all()]
        try:
            source.delete()
        except ProtectedError as error:
            raise ValidationError(f"„{source.title}“ wird noch zitiert und bleibt deshalb.") from error
        delete_on_commit(names=names)

    return source


def delete_source_file(*, source_id: int, file_id: int) -> SourceFile:
    """
    Removes one scan or PDF from a source (#72), the file once the removal is committed. Raises
    "SourceFile.DoesNotExist" for a file that is not the source's or already gone.
    """
    with transaction.atomic():
        source_file = SourceFile.objects.get(pk=file_id, source_id=source_id)
        source_file.delete()
        delete_on_commit(names=[source_file.file.name])

    return source_file


def _store_files(*, source: Source, files: Iterable[UploadedFile]) -> list[SourceFile]:
    # The row comes first, so its id can name the file; see docs/patterns/data-storage.md, "The layout". A file
    # refused halfway rolls the rows back with the transaction, and the files already written go with them.
    stored = []
    try:
        for uploaded_file in files:
            source_file = SourceFile.objects.create(source=source)
            source_file.file.name = store_upload(uploaded_file=uploaded_file, name=source_file.storage_name)
            source_file.save(update_fields=["file"])
            stored.append(source_file)
    except Exception:
        for source_file in stored:
            default_storage.delete(source_file.file.name)
        raise

    return stored
