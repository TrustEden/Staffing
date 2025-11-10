from __future__ import annotations

import re
from datetime import datetime, time
from io import BytesIO
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {"date", "start_time", "end_time", "role_required", "visibility"}
FACILITY_COLUMNS = {"date", "time", "title"}


class ExcelParser:
    """Parses CSV/Excel uploads into normalized shift payloads."""

    def parse(self, file_bytes: bytes, *, file_name: str) -> list[dict[str, Any]]:
        extension = file_name.lower().split(".")[-1]
        stream = BytesIO(file_bytes)

        # Try reading normally first
        if extension == "csv":
            frame = pd.read_csv(stream)
        else:
            frame = pd.read_excel(stream)

        frame.columns = [str(col).strip().lower() for col in frame.columns]

        # Check if this is facility format but header is in row 2
        # (first row contains instructions)
        if "unnamed" in str(frame.columns[0]).lower():
            stream.seek(0)
            # Skip first row and use row 2 as header
            if extension == "csv":
                frame = pd.read_csv(stream, skiprows=1)
            else:
                frame = pd.read_excel(stream, skiprows=1)
            frame.columns = [str(col).strip().lower() for col in frame.columns]

        # Detect format: facility CSV or standard format
        if FACILITY_COLUMNS.issubset(set(frame.columns)):
            return self._parse_facility_format(frame)
        else:
            return self._parse_standard_format(frame)

    def _parse_standard_format(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        """Parse standard format with date, start_time, end_time, role_required columns."""
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        records: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            records.append(
                {
                    "date": self._parse_date(row["date"]),
                    "start_time": self._parse_time(row["start_time"]),
                    "end_time": self._parse_time(row["end_time"]),
                    "role_required": str(row["role_required"]).strip(),
                    "visibility": str(row.get("visibility", "internal")).strip().lower(),
                    "notes": str(row.get("notes", "") or "").strip() or None,
                }
            )
        return records

    def _parse_facility_format(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        """Parse facility CSV format with DATE, TIME, TITLE, STATUS columns."""
        records: list[dict[str, Any]] = []

        for _, row in frame.iterrows():
            # Skip rows with empty date or time
            if pd.isna(row.get("date")) or pd.isna(row.get("time")):
                continue

            # Skip rows with STATUS = "NOT NEEDED"
            status = str(row.get("status", "")).strip().upper()
            if status == "NOT NEEDED":
                continue

            # Parse time range (e.g., "6A-6P")
            time_str = str(row["time"]).strip()
            try:
                start_time, end_time = self._parse_time_range(time_str)
            except ValueError:
                # Skip rows with invalid time format
                continue

            # Extract role from TITLE
            role = str(row["title"]).strip()

            # Extract notes if available (handle NaN properly)
            notes_value = row.get("notes")
            if pd.isna(notes_value):
                notes = None
            else:
                notes_str = str(notes_value).strip()
                notes = notes_str if notes_str and notes_str.lower() != 'nan' else None

            try:
                records.append(
                    {
                        "date": self._parse_date(row["date"]),
                        "start_time": start_time,
                        "end_time": end_time,
                        "role_required": role,
                        "visibility": "internal",  # Default visibility
                        "notes": notes,
                    }
                )
            except Exception:
                # Skip rows that can't be parsed
                continue

        return records

    def _parse_time_range(self, time_str: str) -> tuple[time, time]:
        """Parse time range like '6A-6P' or '12P-6P' into start and end times."""
        # Pattern matches: 6A-6P, 12P-6P, 6:00A-6:00P, etc.
        pattern = r'(\d{1,2}):?(\d{2})?\s*([AP])M?\s*-\s*(\d{1,2}):?(\d{2})?\s*([AP])M?'
        match = re.search(pattern, time_str.upper())

        if not match:
            raise ValueError(f"Invalid time range format: {time_str}")

        start_hour = int(match.group(1))
        start_min = int(match.group(2) or 0)
        start_period = match.group(3)
        end_hour = int(match.group(4))
        end_min = int(match.group(5) or 0)
        end_period = match.group(6)

        # Convert to 24-hour format
        if start_period == 'P' and start_hour != 12:
            start_hour += 12
        elif start_period == 'A' and start_hour == 12:
            start_hour = 0

        if end_period == 'P' and end_hour != 12:
            end_hour += 12
        elif end_period == 'A' and end_hour == 12:
            end_hour = 0

        return time(start_hour, start_min), time(end_hour, end_min)

    @staticmethod
    def _parse_date(value: Any) -> datetime.date:
        if isinstance(value, datetime):
            return value.date()
        return pd.to_datetime(value).date()

    @staticmethod
    def _parse_time(value: Any) -> datetime.time:
        if isinstance(value, datetime):
            return value.time()
        parsed = pd.to_datetime(value)
        return parsed.time()
