"""Email parser - EML and MSG files."""

import email
import email.policy
import logging
from datetime import date
from pathlib import Path

from .base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class EmailParser(DocumentParser):
    """Parse email files (EML and MSG formats)."""

    supported_mime_types = [
        "message/rfc822",  # .eml
        "application/vnd.ms-outlook",  # .msg
    ]

    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        if mime_type == "application/vnd.ms-outlook":
            return self._parse_msg(source_path)
        return self._parse_eml(source_path)

    def _parse_eml(self, source_path: Path) -> ParseResult:
        """Parse a standard .eml (RFC 822) email file."""
        with open(source_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)

        subject = msg.get("Subject", "")
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")
        msg_date = msg.get("Date", "")

        body = self._get_eml_body(msg)
        content = f"From: {from_addr}\nTo: {to_addr}\nSubject: {subject}\nDate: {msg_date}\n\n{body}"

        # Try to parse the date
        parsed_date = None
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(msg_date)
            parsed_date = dt.date()
        except Exception:
            pass

        return ParseResult(
            content=content,
            page_count=1,
            metadata={"from": from_addr, "to": to_addr, "subject": subject},
            date=parsed_date,
        )

    def _parse_msg(self, source_path: Path) -> ParseResult:
        """Parse a .msg (Outlook) email file."""
        try:
            import extract_msg
            msg = extract_msg.Message(str(source_path))

            subject = msg.subject or ""
            sender = msg.sender or ""
            to = msg.to or ""
            body = msg.body or ""
            msg_date_str = str(msg.date) if msg.date else ""

            content = f"From: {sender}\nTo: {to}\nSubject: {subject}\nDate: {msg_date_str}\n\n{body}"

            parsed_date = None
            if msg.date:
                try:
                    parsed_date = msg.date.date()
                except Exception:
                    pass

            msg.close()

            return ParseResult(
                content=content,
                page_count=1,
                metadata={"from": sender, "to": to, "subject": subject},
                date=parsed_date,
            )
        except ImportError:
            logger.warning("extract-msg not available for MSG parsing")
            return ParseResult(content="", page_count=1)
        except Exception:
            logger.warning("Failed to parse MSG file: %s", source_path, exc_info=True)
            return ParseResult(content="", page_count=1)

    @staticmethod
    def _get_eml_body(msg) -> str:
        """Extract the body text from an email message."""
        body = msg.get_body(preferencelist=("plain", "html"))
        if body is None:
            return ""

        content = body.get_content()
        if body.get_content_type() == "text/html":
            try:
                from bs4 import BeautifulSoup
                return BeautifulSoup(content, "html.parser").get_text(
                    separator="\n", strip=True,
                )
            except ImportError:
                import re
                return re.sub(r"<[^>]+>", " ", content).strip()
        return content
