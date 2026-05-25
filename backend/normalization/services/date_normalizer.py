"""
Date normalizer — handles the many date formats found in real enterprise data.

Why this is non-trivial:
- SAP default date format is DD.MM.YYYY (German)
- US locale SAP installs use MM/DD/YYYY
- Some exports use MM-DD-YYYY or DD-MMM-YYYY (e.g., 15-JAN-2024)
- ISO 8601 (YYYY-MM-DD) is what we want to store

The key problem is AMBIGUOUS dates: 01/02/2024 could be:
- January 2, 2024 (US: MM/DD/YYYY)
- February 1, 2024 (UK: DD/MM/YYYY)

Our policy: flag ambiguous dates as WARNING (not ERROR), store our
best guess (assume MM/DD/YYYY for US-locale sources, DD/MM/YYYY for
European-locale sources), and note the ambiguity.

In production, the source locale should be stored on SourceType so
parsers can make the right assumption automatically.
"""
from datetime import datetime, date
from typing import Optional, Tuple


class DateNormalizer:
    # Format strings to try, in order of preference
    # More specific/deterministic formats first
    FORMATS = [
        ("%Y-%m-%d", "ISO-8601"),
        ("%d.%m.%Y", "German/SAP default"),
        ("%d-%b-%Y", "Oracle-style (DD-MON-YYYY)"),
        ("%d %b %Y", "Long month name"),
        ("%Y/%m/%d", "ISO with slashes"),
        ("%d-%m-%Y", "Day-first with hyphens"),
    ]

    # Ambiguous formats — these need special handling
    SLASH_FORMATS = [
        ("%m/%d/%Y", "US (MM/DD/YYYY)"),
        ("%d/%m/%Y", "UK/EU (DD/MM/YYYY)"),
    ]

    def normalize(self, date_str: str, prefer_us_format: bool = False) -> Tuple[Optional[date], str]:
        """
        Parse a date string into a date object.

        Returns:
            (date_object, notes_string) tuple
            date_object is None if unparseable
            notes_string explains what happened (for normalization_notes field)
        """
        if not date_str or not date_str.strip():
            return None, "Date string is empty"

        cleaned = date_str.strip()

        # Try unambiguous formats first
        for fmt, fmt_name in self.FORMATS:
            try:
                parsed = datetime.strptime(cleaned, fmt).date()
                return parsed, f"Parsed as {fmt_name} → {parsed.isoformat()}"
            except ValueError:
                continue

        # Handle ambiguous MM/DD/YYYY vs DD/MM/YYYY
        if "/" in cleaned:
            parts = cleaned.split("/")
            if len(parts) == 3:
                month_part = int(parts[0]) if parts[0].isdigit() else 0
                day_part = int(parts[1]) if parts[1].isdigit() else 0

                # If the first part > 12, it MUST be a day (DD/MM/YYYY)
                if month_part > 12:
                    try:
                        parsed = datetime.strptime(cleaned, "%d/%m/%Y").date()
                        return parsed, f"Unambiguous DD/MM/YYYY (day > 12) → {parsed.isoformat()}"
                    except ValueError:
                        pass
                # If the second part > 12, it MUST be a day (MM/DD/YYYY)
                elif day_part > 12:
                    try:
                        parsed = datetime.strptime(cleaned, "%m/%d/%Y").date()
                        return parsed, f"Unambiguous MM/DD/YYYY (day > 12 in position 2) → {parsed.isoformat()}"
                    except ValueError:
                        pass
                else:
                    # Genuinely ambiguous — use preferred format and flag it
                    primary_fmt = "%m/%d/%Y" if prefer_us_format else "%d/%m/%Y"
                    fmt_name = "US MM/DD/YYYY" if prefer_us_format else "EU DD/MM/YYYY"
                    try:
                        parsed = datetime.strptime(cleaned, primary_fmt).date()
                        return parsed, (
                            f"AMBIGUOUS DATE: '{cleaned}' interpreted as {fmt_name} → "
                            f"{parsed.isoformat()}. Could also be {'DD/MM/YYYY' if prefer_us_format else 'MM/DD/YYYY'}."
                        )
                    except ValueError:
                        pass

        return None, f"Could not parse date: '{cleaned}' — no matching format found"
