"""Watch folder polling and file submission."""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from sources.constants import CONSUMED_ACTION_DELETE, CONSUMED_ACTION_MOVE

logger = logging.getLogger(__name__)

# Track files being processed to prevent duplicates
_processing_files = set()


def poll_watch_folder(watch_folder_source):
    """Poll a watch folder for new files and submit them for processing."""
    source = watch_folder_source.source
    if not source.enabled:
        return 0

    folder_path = Path(watch_folder_source.path)
    if not folder_path.is_dir():
        logger.warning("Watch folder does not exist: %s", folder_path)
        return 0

    submitted = 0
    for filepath in folder_path.iterdir():
        if not filepath.is_file():
            continue

        # Skip hidden files and lock files
        if filepath.name.startswith(".") or filepath.name.endswith(".lock"):
            continue

        # Skip files currently being processed
        file_key = str(filepath)
        if file_key in _processing_files:
            continue

        _processing_files.add(file_key)
        try:
            _submit_file(filepath, watch_folder_source)
            _handle_consumed_file(filepath, watch_folder_source)
            submitted += 1
        except Exception:
            logger.exception("Error processing watch folder file: %s", filepath)
        finally:
            _processing_files.discard(file_key)

    return submitted


def _submit_file(filepath, watch_folder_source):
    """Submit a file from a watch folder to the processing pipeline."""
    from processing.models import ProcessingTask
    from processing.tasks import consume_document

    source = watch_folder_source.source
    task_id = str(uuid.uuid4())
    staged_path = _stage_file(filepath, prefix="docvault_source_")

    ProcessingTask.objects.create(
        task_id=task_id,
        task_name="document_consumption",
        owner=source.owner,
        status_message="Queued watch-folder file for processing",
    )

    overrides = {}
    if source.document_type_id:
        overrides["override_document_type"] = source.document_type_id
    if source.owner_id:
        overrides["override_owner"] = source.owner_id

    # Get tag IDs for override
    tag_ids = list(source.tags.values_list("pk", flat=True))
    if tag_ids:
        overrides["override_tags"] = tag_ids

    consume_document.delay(
        str(staged_path),
        filepath.name,
        task_id,
        source.owner_id,
        cleanup_source_path=True,
        **overrides,
    )


def _handle_consumed_file(filepath, watch_folder_source):
    """Handle a file after it has been submitted for processing."""
    action = watch_folder_source.consumed_action

    if action == CONSUMED_ACTION_DELETE:
        filepath.unlink(missing_ok=True)
    elif action == CONSUMED_ACTION_MOVE:
        consumed_dir = watch_folder_source.consumed_directory
        if consumed_dir:
            dest = Path(consumed_dir)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(dest / filepath.name))
    # NOTHING: leave the file in place


def _stage_file(filepath: Path, prefix: str = "docvault_source_") -> Path:
    """Copy a source file to a stable temp path for async processing."""
    staging_dir = Path(tempfile.mkdtemp(prefix=prefix))
    staged_path = staging_dir / filepath.name
    shutil.copy2(filepath, staged_path)
    return staged_path
