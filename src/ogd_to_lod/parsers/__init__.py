"""Parsers for CSV and DCAT metadata."""

from .csv_parser import CSVParseError, parse_csv
from .dcat_parser import DCATParseError, parse_dcat
from .models import (
    ColumnInfo,
    ColumnType,
    CSVData,
    DCATMetadata,
    ParsedInput,
    SpatialCoverage,
    TemporalCoverage,
)

__all__ = [
    # CSV parser
    "parse_csv",
    "CSVParseError",
    # DCAT parser
    "parse_dcat",
    "DCATParseError",
    # Models
    "ColumnInfo",
    "ColumnType",
    "CSVData",
    "DCATMetadata",
    "ParsedInput",
    "SpatialCoverage",
    "TemporalCoverage",
]
