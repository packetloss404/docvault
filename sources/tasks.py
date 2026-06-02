"""Celery tasks for source polling."""

import logging
import os
import tempfile
import uuid
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def poll_watch_folders():
    """Poll all enabled watch folder sources for new files."""
    from sources.models import WatchFolderSource
    from sources.watch import poll_watch_folder

    sources = WatchFolderSource.objects.filter(
        source__enabled=True,
    ).select_related("source")

    total = 0
    for wf in sources:
        try:
            submitted = poll_watch_folder(wf)
            total += submitted
        except Exception:
            logger.exception("Error polling watch folder: %s", wf.path)

    return {"submitted": total}


@shared_task
def fetch_all_mail():
    """Fetch mail from all enabled mail accounts."""
    from sources.mail import fetch_mail
    from sources.models import MailAccount

    accounts = MailAccount.objects.filter(enabled=True)

    total = 0
    for account in accounts:
        try:
            processed = fetch_mail(account)
            total += processed
        except Exception:
            logger.exception("Error fetching mail for account: %s", account.name)

    return {"processed": total}


@shared_task
def poll_staging_sources():
    """Poll all enabled staging folder sources for new files.

    Each staging source has a ``configuration`` dict on the Source model with
    a ``path`` key pointing to a local directory.  Any file found in that
    directory is submitted to the processing pipeline via ``consume_document``.

    Files are left in place after submission; the processing pipeline is
    responsible for archiving / deleting originals.  To avoid re-processing
    the same files on subsequent polls, fully-qualified file paths that have
    already been submitted are stored in
    ``source.configuration['processed_paths']``.
    """
    from processing.models import ProcessingTask
    from processing.tasks import consume_document
    from sources.constants import SOURCE_STAGING
    from sources.models import Source

    sources = Source.objects.filter(source_type=SOURCE_STAGING, enabled=True)
    total = 0

    for source in sources:
        config = source.configuration if hasattr(source, "configuration") else {}
        if isinstance(config, str):
            import json
            try:
                config = json.loads(config)
            except Exception:
                config = {}

        folder_path_str = config.get("path", "")
        if not folder_path_str:
            logger.warning("Staging source %s has no path configured", source.label)
            continue

        folder_path = Path(folder_path_str)
        if not folder_path.is_dir():
            logger.warning(
                "Staging folder does not exist for source %s: %s",
                source.label, folder_path,
            )
            continue

        processed_paths = set(config.get("processed_paths", []))

        for filepath in folder_path.iterdir():
            if not filepath.is_file():
                continue
            if filepath.name.startswith(".") or filepath.name.endswith(".lock"):
                continue

            file_key = str(filepath.resolve())
            if file_key in processed_paths:
                continue

            task_id = str(uuid.uuid4())
            overrides = {}
            if source.document_type_id:
                overrides["override_document_type"] = source.document_type_id
            if source.owner_id:
                overrides["override_owner"] = source.owner_id

            tag_ids = list(source.tags.values_list("pk", flat=True))
            if tag_ids:
                overrides["override_tags"] = tag_ids

            try:
                ProcessingTask.objects.create(
                    task_id=task_id,
                    filename=filepath.name,
                    user_id=source.owner_id,
                )
                consume_document.delay(
                    str(filepath),
                    filepath.name,
                    task_id,
                    source.owner_id,
                    **overrides,
                )
                processed_paths.add(file_key)
                total += 1
                logger.info(
                    "Staging source %s: submitted %s (task %s)",
                    source.label, filepath.name, task_id,
                )
            except Exception:
                logger.exception(
                    "Error submitting staging file %s from source %s",
                    filepath, source.label,
                )

        # Persist the updated set of processed paths back to the source config
        config["processed_paths"] = list(processed_paths)
        source.configuration = config
        source.save(update_fields=["configuration"])

    return {"submitted": total}


@shared_task
def poll_s3_sources():
    """Poll all enabled S3 sources for new objects.

    Each S3 source has a ``configuration`` dict containing:
      - ``bucket``: S3 bucket name
      - ``prefix``: key prefix to list (default "")
      - ``aws_access_key_id``: optional explicit credentials
      - ``aws_secret_access_key``: optional explicit credentials
      - ``region_name``: optional region (default us-east-1)
      - ``processed_keys``: list of already-processed S3 keys (maintained by this task)

    For each new object the task downloads it to a temporary file, submits it
    to ``consume_document``, and records its key in ``processed_keys``.
    """
    import json

    import boto3

    from processing.models import ProcessingTask
    from processing.tasks import consume_document
    from sources.constants import SOURCE_S3
    from sources.models import Source

    sources = Source.objects.filter(source_type=SOURCE_S3, enabled=True)
    total = 0

    for source in sources:
        config = source.configuration if hasattr(source, "configuration") else {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                config = {}

        bucket = config.get("bucket", "")
        if not bucket:
            logger.warning("S3 source %s has no bucket configured", source.label)
            continue

        prefix = config.get("prefix", "")
        processed_keys = set(config.get("processed_keys", []))

        # Build boto3 session with optional explicit credentials
        session_kwargs = {}
        if config.get("aws_access_key_id"):
            session_kwargs["aws_access_key_id"] = config["aws_access_key_id"]
        if config.get("aws_secret_access_key"):
            session_kwargs["aws_secret_access_key"] = config["aws_secret_access_key"]
        if config.get("region_name"):
            session_kwargs["region_name"] = config["region_name"]

        try:
            session = boto3.Session(**session_kwargs)
            s3 = session.client("s3")
        except Exception:
            logger.exception("Failed to create boto3 S3 client for source %s", source.label)
            continue

        # List objects (handles pagination)
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Skip directory-like keys and already-processed ones
                if key.endswith("/"):
                    continue
                if key in processed_keys:
                    continue

                filename = os.path.basename(key) or key
                task_id = str(uuid.uuid4())

                # Download to a temporary file
                suffix = Path(filename).suffix or ""
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=suffix, delete=False,
                    ) as tmp:
                        tmp_path = tmp.name
                    s3.download_file(bucket, key, tmp_path)
                except Exception:
                    logger.exception(
                        "Failed to download S3 object %s/%s for source %s",
                        bucket, key, source.label,
                    )
                    continue

                overrides = {}
                if source.document_type_id:
                    overrides["override_document_type"] = source.document_type_id
                if source.owner_id:
                    overrides["override_owner"] = source.owner_id

                tag_ids = list(source.tags.values_list("pk", flat=True))
                if tag_ids:
                    overrides["override_tags"] = tag_ids

                try:
                    ProcessingTask.objects.create(
                        task_id=task_id,
                        filename=filename,
                        user_id=source.owner_id,
                    )
                    consume_document.delay(
                        tmp_path,
                        filename,
                        task_id,
                        source.owner_id,
                        **overrides,
                    )
                    processed_keys.add(key)
                    total += 1
                    logger.info(
                        "S3 source %s: submitted s3://%s/%s (task %s)",
                        source.label, bucket, key, task_id,
                    )
                except Exception:
                    logger.exception(
                        "Error submitting S3 object %s/%s from source %s",
                        bucket, key, source.label,
                    )

        # Persist updated processed keys
        config["processed_keys"] = list(processed_keys)
        source.configuration = config
        source.save(update_fields=["configuration"])

    return {"submitted": total}
