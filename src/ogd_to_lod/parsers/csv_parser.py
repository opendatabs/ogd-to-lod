"""CSV parser for extracting schema and sample data."""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .models import ColumnInfo, ColumnType, CSVData


class CSVParseError(Exception):
    """Exception raised when CSV parsing fails."""

    pass


def _is_url(source: str) -> bool:
    """Check if the source is a URL."""
    try:
        result = urlparse(source)
        return result.scheme in ("http", "https")
    except Exception:
        return False


def _read_file_content(source: str, encoding: str | None = None) -> tuple[str, str]:
    """Read content from file path or URL.

    Args:
        source: File path or URL.
        encoding: Optional encoding to use. If None, will try to detect.

    Returns:
        Tuple of (content, detected_encoding).

    Raises:
        CSVParseError: If the file cannot be read.
    """
    encodings_to_try = [encoding] if encoding else ["utf-8-sig", "utf-8", "iso-8859-1", "cp1252"]

    if _is_url(source):
        try:
            with urlopen(source, timeout=30) as response:
                raw_content = response.read()
        except Exception as e:
            raise CSVParseError(f"Failed to fetch URL '{source}': {e}") from e
    else:
        path = Path(source)
        if not path.exists():
            raise CSVParseError(f"File not found: {source}")
        try:
            raw_content = path.read_bytes()
        except Exception as e:
            raise CSVParseError(f"Failed to read file '{source}': {e}") from e

    # Try different encodings
    for enc in encodings_to_try:
        if enc is None:
            continue
        try:
            content = raw_content.decode(enc)
            # Strip BOM if present (in case utf-8 was used instead of utf-8-sig)
            if content.startswith("\ufeff"):
                content = content[1:]
            return content, enc
        except (UnicodeDecodeError, LookupError):
            continue

    raise CSVParseError(
        f"Failed to decode content from '{source}'. "
        f"Tried encodings: {', '.join(e for e in encodings_to_try if e)}"
    )


def _detect_delimiter(sample: str) -> str:
    """Detect the CSV delimiter from a sample of the content."""
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        # Default to comma if detection fails
        return ","


def _is_integer(value: str) -> bool:
    """Check if a string value represents an integer."""
    if not value:
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    """Check if a string value represents a float."""
    if not value:
        return False
    try:
        float(value)
        # Make sure it's actually a float, not an integer
        return "." in value or "e" in value.lower()
    except ValueError:
        return False


def _is_boolean(value: str) -> bool:
    """Check if a string value represents a boolean."""
    return value.lower() in ("true", "false", "yes", "no", "1", "0")


# Common date formats to try
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y",
]

DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


def _is_date(value: str) -> bool:
    """Check if a string value represents a date."""
    if not value or len(value) < 4:
        return False

    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_datetime(value: str) -> bool:
    """Check if a string value represents a datetime."""
    if not value:
        return False

    for fmt in DATETIME_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _detect_column_type(values: list[str]) -> ColumnType:
    """Detect the type of a column from sample values.

    Args:
        values: List of string values from the column.

    Returns:
        Detected column type.
    """
    # Filter out empty values
    non_empty = [v.strip() for v in values if v and v.strip()]

    if not non_empty:
        return ColumnType.STRING

    # Count type matches
    int_count = sum(1 for v in non_empty if _is_integer(v))
    float_count = sum(1 for v in non_empty if _is_float(v))
    bool_count = sum(1 for v in non_empty if _is_boolean(v))
    datetime_count = sum(1 for v in non_empty if _is_datetime(v))
    date_count = sum(1 for v in non_empty if _is_date(v))

    total = len(non_empty)
    threshold = 0.8  # 80% of values must match the type

    # Check types in order of specificity
    if datetime_count / total >= threshold:
        return ColumnType.DATETIME
    if date_count / total >= threshold:
        return ColumnType.DATE
    if float_count / total >= threshold:
        return ColumnType.FLOAT
    if int_count / total >= threshold:
        return ColumnType.INTEGER
    if bool_count / total >= threshold:
        return ColumnType.BOOLEAN

    return ColumnType.STRING


def _convert_value(value: str, col_type: ColumnType) -> Any:
    """Convert a string value to its detected type.

    Args:
        value: String value to convert.
        col_type: Target column type.

    Returns:
        Converted value.
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    try:
        if col_type == ColumnType.INTEGER:
            return int(value)
        elif col_type == ColumnType.FLOAT:
            return float(value)
        elif col_type == ColumnType.BOOLEAN:
            return value.lower() in ("true", "yes", "1")
        else:
            # For date, datetime, and string types, keep as string
            return value
    except (ValueError, TypeError):
        return value


def parse_csv(
    source: str,
    encoding: str | None = None,
    delimiter: str | None = None,
    sample_rows: int = 5,
    max_rows: int | None = None,
) -> CSVData:
    """Parse a CSV file and extract schema information.

    Args:
        source: File path or URL to the CSV file.
        encoding: Optional encoding to use. If None, will try to detect.
        delimiter: Optional delimiter to use. If None, will try to detect.
        sample_rows: Number of sample rows to extract (default: 5).
        max_rows: Maximum number of rows to read from the file. If None,
            all rows are read. When set, total_rows is estimated from the
            raw line count rather than a full read.

    Returns:
        CSVData object containing parsed information.

    Raises:
        CSVParseError: If the CSV cannot be parsed.
    """
    # Read content
    content, detected_encoding = _read_file_content(source, encoding)

    # Detect delimiter if not provided
    if delimiter is None:
        delimiter = _detect_delimiter(content[:2000])

    # Parse CSV
    try:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

        if reader.fieldnames is None:
            raise CSVParseError(f"CSV file '{source}' has no header row")

        # Validate fieldnames
        fieldnames = list(reader.fieldnames)
        if not fieldnames:
            raise CSVParseError(f"CSV file '{source}' has no columns")

        # Read rows up to max_rows; estimate total from raw line count
        all_rows: list[dict[str, str]] = []
        column_values: dict[str, list[str]] = {name: [] for name in fieldnames}

        for row in reader:
            all_rows.append(row)
            for name in fieldnames:
                column_values[name].append(row.get(name, ""))
            if max_rows is not None and len(all_rows) >= max_rows:
                break

        # Total row count: exact when all rows read, estimated otherwise
        if max_rows is None or len(all_rows) < max_rows:
            total_rows = len(all_rows)
        else:
            # Count non-empty lines minus header as a fast estimate
            total_rows = sum(1 for line in content.splitlines() if line.strip()) - 1

        if total_rows == 0:
            raise CSVParseError(f"CSV file '{source}' has no data rows")

        # Detect column types using sample of values
        columns: list[ColumnInfo] = []
        for name in fieldnames:
            # Use up to 100 values for type detection
            sample_for_detection = column_values[name][:100]
            detected_type = _detect_column_type(sample_for_detection)

            # Get sample values for display
            sample_vals = [
                _convert_value(v, detected_type)
                for v in column_values[name][:sample_rows]
            ]

            columns.append(
                ColumnInfo(
                    name=name,
                    detected_type=detected_type,
                    sample_values=sample_vals,
                )
            )

        # Build column type mapping for row conversion
        col_types = {col.name: col.detected_type for col in columns}

        # Convert sample rows
        sample_data: list[dict[str, Any]] = []
        for row in all_rows[:sample_rows]:
            converted_row = {
                name: _convert_value(row.get(name, ""), col_types[name])
                for name in fieldnames
            }
            sample_data.append(converted_row)

        return CSVData(
            source=source,
            columns=columns,
            sample_rows=sample_data,
            total_rows=total_rows,
            encoding=detected_encoding,
            delimiter=delimiter,
        )

    except csv.Error as e:
        raise CSVParseError(f"Failed to parse CSV '{source}': {e}") from e
