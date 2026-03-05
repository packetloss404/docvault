"""Date extraction plugin - extracts document date from content."""

import logging
import re
from datetime import date

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)

# Common date patterns to try before full dateparser
_DATE_PATTERNS = [
    r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b",  # DD/MM/YYYY or MM/DD/YYYY
    r"\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b",  # YYYY-MM-DD
    r"\b(\w+ \d{1,2},?\s*\d{4})\b",  # January 15, 2025
    r"\b(\d{1,2}\s+\w+\s+\d{4})\b",  # 15 January 2025
]


class DateExtractionPlugin(ProcessingPlugin):
    """Extract document date from content text."""

    name = "DateExtraction"
    order = 70

    def can_run(self, context: ProcessingContext) -> bool:
        return bool(context.content) and context.date_created is None

    def process(self, context: ProcessingContext) -> PluginResult:
        # Search the first 2000 chars for date patterns
        text = context.content[:2000]
        extracted_date = self._extract_date(text)

        if extracted_date:
            context.date_created = extracted_date
        else:
            context.date_created = date.today()

        self.update_progress(
            context, 0.70,
            f"Document date: {context.date_created}",
        )
        return PluginResult(success=True)

    def _extract_date(self, text: str) -> date | None:
        """Try to extract a date from text."""
        # First, find candidate date strings with regex
        candidates = []
        for pattern in _DATE_PATTERNS:
            matches = re.findall(pattern, text)
            candidates.extend(matches)

        if not candidates:
            return None

        # Try to parse candidates with dateparser
        try:
            import dateparser
            for candidate in candidates[:5]:  # Limit attempts
                parsed = dateparser.parse(
                    candidate,
                    settings={
                        "PREFER_DATES_FROM": "past",
                        "REQUIRE_PARTS": ["day", "month", "year"],
                    },
                )
                if parsed:
                    return parsed.date()
        except ImportError:
            # Fallback without dateparser
            return self._parse_date_fallback(candidates)

        return None

    @staticmethod
    def _parse_date_fallback(candidates: list[str]) -> date | None:
        """Simple date parsing fallback without dateparser."""
        from datetime import datetime
        formats = [
            "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y",
            "%m-%d-%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%d.%m.%Y",
        ]
        for candidate in candidates[:5]:
            for fmt in formats:
                try:
                    return datetime.strptime(candidate.strip(), fmt).date()
                except ValueError:
                    continue
        return None
