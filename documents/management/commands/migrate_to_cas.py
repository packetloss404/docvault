"""Management command to migrate DocumentFiles to content-addressed storage."""

import hashlib
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate DocumentFiles to content-addressed storage (CAS)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making any changes.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of DocumentFile records to process per batch (default: 100).",
        )

    def handle(self, *args, **options):
        from documents.models import DocumentFile
        from storage.models import ContentBlob

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved."))

        qs = DocumentFile.objects.filter(blob__isnull=True).select_related("document")
        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All DocumentFiles already have a CAS blob. Nothing to do."))
            return

        self.stdout.write(f"Found {total} DocumentFile(s) without a CAS blob.")

        migrated = 0
        skipped = 0
        errors = 0

        offset = 0
        while offset < total:
            batch = qs[offset : offset + batch_size]

            for doc_file in batch:
                # Determine the actual storage path of the file.
                # doc_file.file is a FieldFile; its name is the storage key.
                try:
                    storage_path = doc_file.file.name
                    if not storage_path:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  DocumentFile #{doc_file.pk} has no storage path — skipping."
                            )
                        )
                        skipped += 1
                        continue

                    # Compute SHA-256 by reading the file from storage.
                    sha256 = hashlib.sha256()
                    file_size = 0
                    with doc_file.file.open("rb") as fh:
                        for chunk in iter(lambda: fh.read(65536), b""):
                            sha256.update(chunk)
                            file_size += len(chunk)

                    digest = sha256.hexdigest()

                    self.stdout.write(
                        f"  DocumentFile #{doc_file.pk} ({doc_file.filename}): "
                        f"sha256={digest[:16]}... size={file_size}"
                    )

                    if not dry_run:
                        blob, created = ContentBlob.objects.get_or_create(
                            sha256_hash=digest,
                            defaults={
                                "size": file_size,
                                "storage_path": storage_path,
                            },
                        )

                        if not created:
                            # Increment the reference count for existing blobs.
                            ContentBlob.objects.filter(sha256_hash=digest).update(
                                reference_count=blob.reference_count + 1
                            )

                        doc_file.blob = blob
                        doc_file.save(update_fields=["blob"])
                        logger.debug(
                            "Linked DocumentFile #%s to ContentBlob %s (created=%s)",
                            doc_file.pk,
                            digest[:12],
                            created,
                        )

                    migrated += 1

                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Error processing DocumentFile #{doc_file.pk}: {exc}"
                        )
                    )
                    logger.exception("migrate_to_cas: error on DocumentFile #%s", doc_file.pk)
                    errors += 1

            offset += batch_size

        summary = (
            f"Migration {'(dry run) ' if dry_run else ''}complete: "
            f"{migrated} migrated, {skipped} skipped, {errors} errors."
        )
        style = self.style.SUCCESS if errors == 0 else self.style.WARNING
        self.stdout.write(style(summary))
