"""IMAP mail fetching and processing."""

import email
import imaplib
import logging
import tempfile
from email.header import decode_header
from pathlib import Path

from sources.constants import (
    MAIL_ACTION_DOWNLOAD_ATTACHMENT,
    MAIL_ACTION_PROCESS_EMAIL,
    MAIL_PROCESSED_DELETE,
    MAIL_PROCESSED_FLAG,
    MAIL_PROCESSED_MOVE,
    MAIL_PROCESSED_READ,
    MAIL_SECURITY_NONE,
    MAIL_SECURITY_SSL,
    MAIL_SECURITY_STARTTLS,
)

logger = logging.getLogger(__name__)


def connect_imap(account):
    """Connect to an IMAP server and return the connection."""
    if account.security == MAIL_SECURITY_SSL:
        conn = imaplib.IMAP4_SSL(account.imap_server, account.port)
    else:
        conn = imaplib.IMAP4(account.imap_server, account.port)
        if account.security == MAIL_SECURITY_STARTTLS:
            conn.starttls()

    conn.login(account.username, account.password)
    return conn


def test_connection(account):
    """Test IMAP connection. Returns (success, message)."""
    try:
        conn = connect_imap(account)
        conn.select("INBOX", readonly=True)
        conn.close()
        conn.logout()
        return True, "Connection successful."
    except Exception as e:
        return False, str(e)


def fetch_mail(account):
    """Fetch and process emails for all rules on an account."""
    if not account.enabled:
        return 0

    rules = account.rules.filter(enabled=True).order_by("order")
    if not rules.exists():
        return 0

    try:
        conn = connect_imap(account)
    except Exception:
        logger.exception("Failed to connect to mail account: %s", account.name)
        return 0

    total_processed = 0
    try:
        for rule in rules:
            processed = _process_rule(conn, rule)
            total_processed += processed
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

    return total_processed


def _process_rule(conn, rule):
    """Process a single mail rule."""
    try:
        status, _ = conn.select(rule.folder, readonly=False)
        if status != "OK":
            logger.warning(
                "Could not select folder %s for rule %s", rule.folder, rule.name
            )
            return 0
    except Exception:
        logger.exception("Error selecting folder %s", rule.folder)
        return 0

    # Build search criteria
    criteria = _build_search_criteria(rule)

    try:
        status, data = conn.search(None, *criteria)
        if status != "OK":
            return 0
    except Exception:
        logger.exception("Error searching mail for rule %s", rule.name)
        return 0

    message_ids = data[0].split()
    processed = 0

    for msg_id in message_ids:
        try:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            files = _extract_files(msg, rule)
            for filename, content in files:
                _submit_to_pipeline(filename, content, rule)
                processed += 1

            _post_process_email(conn, msg_id, rule)

        except Exception:
            logger.exception(
                "Error processing email %s for rule %s", msg_id, rule.name
            )

    return processed


def _build_search_criteria(rule):
    """Build IMAP search criteria from a mail rule."""
    criteria = ["UNSEEN"]

    if rule.filter_from:
        criteria.extend(["FROM", f'"{rule.filter_from}"'])
    if rule.filter_subject:
        criteria.extend(["SUBJECT", f'"{rule.filter_subject}"'])
    if rule.filter_body:
        criteria.extend(["BODY", f'"{rule.filter_body}"'])

    return criteria if len(criteria) > 1 else ["UNSEEN"]


def _decode_header_value(value):
    """Decode an email header value."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_files(msg, rule):
    """Extract files from an email message based on rule action."""
    import fnmatch

    files = []

    if rule.action == MAIL_ACTION_PROCESS_EMAIL:
        # Process the entire email as a document
        subject = _decode_header_value(msg["subject"]) or "Untitled Email"
        body_parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode("utf-8", errors="replace"))
        content = "\n".join(body_parts).encode("utf-8")
        files.append((f"{subject}.txt", content))

    elif rule.action == MAIL_ACTION_DOWNLOAD_ATTACHMENT:
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = _decode_header_value(part.get_filename()) or "attachment"
                if rule.filter_attachment_filename:
                    if not fnmatch.fnmatch(
                        filename.lower(), rule.filter_attachment_filename.lower()
                    ):
                        continue
                payload = part.get_payload(decode=True)
                if payload:
                    files.append((filename, payload))

    return files


def _submit_to_pipeline(filename, content, rule):
    """Submit a file to the document processing pipeline."""
    import uuid

    from processing.models import ProcessingTask
    from processing.tasks import consume_document

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
    tmp.write(content)
    tmp.close()

    task_id = str(uuid.uuid4())

    # Create processing task
    ProcessingTask.objects.create(
        task_id=task_id,
        filename=filename,
        user_id=rule.owner_id,
    )

    overrides = {}
    if rule.document_type_id:
        overrides["override_document_type"] = rule.document_type_id
    if rule.owner_id:
        overrides["override_owner"] = rule.owner_id

    consume_document.delay(
        tmp.name,
        filename,
        task_id,
        rule.owner_id,
        **overrides,
    )


def _post_process_email(conn, msg_id, rule):
    """Post-process an email after extracting files."""
    try:
        if rule.processed_action == MAIL_PROCESSED_READ:
            conn.store(msg_id, "+FLAGS", "\\Seen")
        elif rule.processed_action == MAIL_PROCESSED_FLAG:
            conn.store(msg_id, "+FLAGS", "\\Flagged")
        elif rule.processed_action == MAIL_PROCESSED_DELETE:
            conn.store(msg_id, "+FLAGS", "\\Deleted")
            conn.expunge()
        elif rule.processed_action == MAIL_PROCESSED_MOVE:
            if rule.processed_folder:
                conn.copy(msg_id, rule.processed_folder)
                conn.store(msg_id, "+FLAGS", "\\Deleted")
                conn.expunge()
    except Exception:
        logger.exception("Error post-processing email %s", msg_id)
