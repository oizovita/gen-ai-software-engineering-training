"""Small shared helpers: ids, timestamps, date parsing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


def generate_id() -> str:
    """Return a new UUID4 string for a transaction id."""
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    """Current UTC time as an ISO 8601 string with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp into a timezone-aware UTC datetime."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_filter_date(value: str, *, end_of_range: bool = False) -> datetime:
    """Parse a filter boundary.

    Accepts either a plain date (``YYYY-MM-DD``) or a full ISO 8601 datetime.
    A plain date used as the ``to`` boundary covers the whole day, so we move
    the boundary to the very end of that day.
    Raises ``ValueError`` for anything unparsable.
    """
    if len(value) == 10:
        day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_of_range:
            return day + timedelta(days=1) - timedelta(microseconds=1)
        return day
    return parse_timestamp(value)


CSV_COLUMNS = ("id", "fromAccount", "toAccount", "amount", "currency", "type", "timestamp", "status")


def transactions_to_csv(rows) -> str:
    """Serialize transactions (pydantic models) to CSV text with a header row."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        data = row.model_dump(mode="json")
        data["amount"] = f"{data['amount']:.2f}"
        writer.writerow({col: ("" if data.get(col) is None else data[col]) for col in CSV_COLUMNS})
    return buffer.getvalue()
