"""DCAT metadata parser supporting JSON-LD and Turtle formats."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .models import DCATMetadata, SpatialCoverage, TemporalCoverage


class DCATParseError(Exception):
    """Exception raised when DCAT parsing fails."""

    pass


# Common DCAT namespace prefixes
DCAT_NS = "http://www.w3.org/ns/dcat#"
DCT_NS = "http://purl.org/dc/terms/"
FOAF_NS = "http://xmlns.com/foaf/0.1/"
SCHEMA_NS = "http://schema.org/"
VCARD_NS = "http://www.w3.org/2006/vcard/ns#"


def _is_url(source: str) -> bool:
    """Check if the source is a URL."""
    try:
        result = urlparse(source)
        return result.scheme in ("http", "https")
    except Exception:
        return False


def _read_content(source: str) -> tuple[str, str]:
    """Read content from file path or URL.

    Args:
        source: File path or URL.

    Returns:
        Tuple of (content, format_hint based on extension/content-type).

    Raises:
        DCATParseError: If the content cannot be read.
    """
    format_hint = "unknown"

    if _is_url(source):
        try:
            with urlopen(source, timeout=30) as response:
                content = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")

                if "json" in content_type:
                    format_hint = "json-ld"
                elif "turtle" in content_type or "ttl" in content_type:
                    format_hint = "turtle"
                elif "rdf" in content_type or "xml" in content_type:
                    format_hint = "rdf-xml"
        except Exception as e:
            raise DCATParseError(f"Failed to fetch URL '{source}': {e}") from e
    else:
        path = Path(source)
        if not path.exists():
            raise DCATParseError(f"File not found: {source}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="iso-8859-1")
            except Exception as e:
                raise DCATParseError(f"Failed to read file '{source}': {e}") from e
        except Exception as e:
            raise DCATParseError(f"Failed to read file '{source}': {e}") from e

        # Detect format from extension
        suffix = path.suffix.lower()
        if suffix in (".json", ".jsonld"):
            format_hint = "json-ld"
        elif suffix in (".ttl", ".turtle"):
            format_hint = "turtle"
        elif suffix in (".rdf", ".xml"):
            format_hint = "rdf-xml"

    return content, format_hint


def _get_value(obj: Any, *keys: str) -> str | None:
    """Extract a value from a nested dict structure, trying multiple keys.

    Args:
        obj: The object to extract from.
        *keys: Keys to try in order.

    Returns:
        The found value as string, or None.
    """
    if obj is None:
        return None

    for key in keys:
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                if isinstance(val, str):
                    return val
                elif isinstance(val, dict):
                    # Handle @value pattern in JSON-LD
                    if "@value" in val:
                        return str(val["@value"])
                    # Handle @id pattern
                    if "@id" in val:
                        return str(val["@id"])
                    # Handle name/value nested objects
                    if "name" in val:
                        return _get_value(val, "name")
                elif isinstance(val, list) and val:
                    # Take first value if list
                    return _get_value(val[0], "@value", "@id", "name") or str(val[0])
                else:
                    return str(val)
    return None


def _get_list(obj: Any, *keys: str) -> list[str]:
    """Extract a list of values from a nested dict structure.

    Args:
        obj: The object to extract from.
        *keys: Keys to try in order.

    Returns:
        List of string values.
    """
    if obj is None:
        return []

    for key in keys:
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                if isinstance(val, list):
                    result = []
                    for item in val:
                        if isinstance(item, str):
                            result.append(item)
                        elif isinstance(item, dict):
                            v = _get_value(item, "@value", "@id", "name", "prefLabel")
                            if v:
                                result.append(v)
                    return result
                elif isinstance(val, str):
                    return [val]
    return []


def _parse_temporal_coverage(obj: Any) -> TemporalCoverage | None:
    """Parse temporal coverage from DCAT metadata.

    Args:
        obj: The temporal coverage object.

    Returns:
        TemporalCoverage or None.
    """
    if obj is None:
        return None

    if isinstance(obj, str):
        # Simple string format, try to parse as period
        if "/" in obj:
            parts = obj.split("/")
            end_date = parts[1] if len(parts) > 1 else None
            return TemporalCoverage(start_date=parts[0], end_date=end_date)
        return TemporalCoverage(start_date=obj)

    if isinstance(obj, dict):
        start = _get_value(obj, "startDate", "start", "dct:startDate", "schema:startDate")
        end = _get_value(obj, "endDate", "end", "dct:endDate", "schema:endDate")
        return TemporalCoverage(start_date=start, end_date=end)

    if isinstance(obj, list) and obj:
        return _parse_temporal_coverage(obj[0])

    return None


def _parse_spatial_coverage(obj: Any) -> SpatialCoverage | None:
    """Parse spatial coverage from DCAT metadata.

    Args:
        obj: The spatial coverage object.

    Returns:
        SpatialCoverage or None.
    """
    if obj is None:
        return None

    if isinstance(obj, str):
        return SpatialCoverage(location=obj)

    if isinstance(obj, dict):
        location = _get_value(
            obj, "name", "prefLabel", "@id", "geo:name", "schema:name", "rdfs:label"
        )
        geometry = _get_value(obj, "geometry", "geo:geometry", "locn:geometry")
        bbox = _get_value(obj, "bbox", "dcat:bbox")
        return SpatialCoverage(location=location, geometry=geometry, bbox=bbox)

    if isinstance(obj, list) and obj:
        return _parse_spatial_coverage(obj[0])

    return None


def _parse_json_ld(content: str, source: str) -> DCATMetadata:
    """Parse DCAT metadata from JSON-LD content.

    Args:
        content: JSON-LD content string.
        source: Original source path/URL.

    Returns:
        Parsed DCATMetadata.

    Raises:
        DCATParseError: If parsing fails.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise DCATParseError(f"Invalid JSON-LD in '{source}': {e}") from e

    # Handle @graph structure
    if isinstance(data, dict) and "@graph" in data:
        graph = data["@graph"]
        # Find the Dataset entry
        dataset = None
        for item in graph:
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                if "dcat:Dataset" in item_type or "Dataset" in item_type:
                    dataset = item
                    break
            elif "Dataset" in item_type:
                dataset = item
                break
        if dataset is None and graph:
            dataset = graph[0]
        data = dataset or data

    # Handle array of datasets
    if isinstance(data, list):
        if not data:
            raise DCATParseError(f"Empty JSON-LD array in '{source}'")
        data = data[0]

    if not isinstance(data, dict):
        raise DCATParseError(f"Invalid JSON-LD structure in '{source}'")

    # Extract fields with multiple key variants
    title = _get_value(data, "title", "dct:title", "dcterms:title", "schema:name", "name")
    description = _get_value(
        data, "description", "dct:description", "dcterms:description", "schema:description"
    )

    # Publisher can be nested
    publisher_obj = (
        data.get("publisher") or data.get("dct:publisher") or data.get("dcterms:publisher")
    )
    publisher = None
    if publisher_obj:
        if isinstance(publisher_obj, str):
            publisher = publisher_obj
        elif isinstance(publisher_obj, dict):
            publisher = _get_value(publisher_obj, "name", "foaf:name", "schema:name", "@id")
        elif isinstance(publisher_obj, list) and publisher_obj:
            publisher = _get_value(publisher_obj[0], "name", "foaf:name", "schema:name", "@id")

    # Keywords
    keywords = _get_list(data, "keyword", "keywords", "dcat:keyword", "dct:keyword")

    # Temporal coverage
    temporal_obj = data.get("temporal") or data.get("dct:temporal") or data.get("dcterms:temporal")
    temporal_coverage = _parse_temporal_coverage(temporal_obj)

    # Spatial coverage
    spatial_obj = data.get("spatial") or data.get("dct:spatial") or data.get("dcterms:spatial")
    spatial_coverage = _parse_spatial_coverage(spatial_obj)

    # Other fields
    identifier = _get_value(data, "identifier", "dct:identifier", "dcterms:identifier", "@id")
    issued = _get_value(data, "issued", "dct:issued", "dcterms:issued")
    modified = _get_value(data, "modified", "dct:modified", "dcterms:modified")
    language = _get_value(data, "language", "dct:language", "dcterms:language")
    license_val = _get_value(data, "license", "dct:license", "dcterms:license")
    access_rights = _get_value(data, "accessRights", "dct:accessRights", "dcterms:accessRights")

    # Contact point
    contact_obj = data.get("contactPoint") or data.get("dcat:contactPoint")
    contact_point = None
    if contact_obj:
        if isinstance(contact_obj, str):
            contact_point = contact_obj
        elif isinstance(contact_obj, dict):
            contact_point = _get_value(
                contact_obj, "fn", "vcard:fn", "email", "vcard:hasEmail", "name"
            )

    return DCATMetadata(
        source=source,
        title=title,
        description=description,
        publisher=publisher,
        keywords=keywords,
        temporal_coverage=temporal_coverage,
        spatial_coverage=spatial_coverage,
        identifier=identifier,
        issued=issued,
        modified=modified,
        language=language,
        license=license_val,
        access_rights=access_rights,
        contact_point=contact_point,
    )


def _parse_turtle(content: str, source: str) -> DCATMetadata:
    """Parse DCAT metadata from Turtle content.

    This is a simplified parser that extracts common patterns.
    For full RDF parsing, consider using rdflib.

    Args:
        content: Turtle content string.
        source: Original source path/URL.

    Returns:
        Parsed DCATMetadata.

    Raises:
        DCATParseError: If parsing fails.
    """
    import re

    # Helper to extract literal values
    def extract_literal(pattern: str) -> str | None:
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            # Remove language tag
            if "@" in val:
                val = val.split("@")[0]
            # Remove quotes
            val = val.strip('"').strip("'")
            return val
        return None

    def extract_literals(pattern: str) -> list[str]:
        matches = re.findall(pattern, content, re.MULTILINE)
        return [m.strip().strip('"').strip("'").split("@")[0] for m in matches]

    # Common property patterns
    title_pattern = r'(?:dct|dcterms):title\s+["\'](.+?)["\']'
    desc_pattern = r'(?:dct|dcterms):description\s+["\'](.+?)["\']'
    publisher_pattern = r'(?:dct|dcterms):publisher\s+(?:<([^>]+)>|["\'](.+?)["\'])'
    keyword_pattern = r'(?:dcat):keyword\s+["\']([^"\']+)["\']'
    identifier_pattern = r'(?:dct|dcterms):identifier\s+["\'](.+?)["\']'
    issued_pattern = r'(?:dct|dcterms):issued\s+["\'](.+?)["\']'
    modified_pattern = r'(?:dct|dcterms):modified\s+["\'](.+?)["\']'

    title = extract_literal(title_pattern)
    description = extract_literal(desc_pattern)
    keywords = extract_literals(keyword_pattern)
    identifier = extract_literal(identifier_pattern)
    issued = extract_literal(issued_pattern)
    modified = extract_literal(modified_pattern)

    # Publisher
    publisher_match = re.search(publisher_pattern, content)
    publisher = None
    if publisher_match:
        publisher = publisher_match.group(1) or publisher_match.group(2)

    # Temporal coverage
    temporal_start = extract_literal(r'(?:dcat|dct|dcterms):startDate\s+["\'](.+?)["\']')
    temporal_end = extract_literal(r'(?:dcat|dct|dcterms):endDate\s+["\'](.+?)["\']')
    temporal_coverage = None
    if temporal_start or temporal_end:
        temporal_coverage = TemporalCoverage(start_date=temporal_start, end_date=temporal_end)

    # Spatial coverage
    spatial_location = extract_literal(r'(?:dct|dcterms):spatial\s+(?:<([^>]+)>|["\'](.+?)["\'])')
    spatial_coverage = None
    if spatial_location:
        spatial_coverage = SpatialCoverage(location=spatial_location)

    return DCATMetadata(
        source=source,
        title=title,
        description=description,
        publisher=publisher,
        keywords=keywords,
        temporal_coverage=temporal_coverage,
        spatial_coverage=spatial_coverage,
        identifier=identifier,
        issued=issued,
        modified=modified,
    )


def parse_dcat(source: str, format_hint: str | None = None) -> DCATMetadata:
    """Parse DCAT metadata from a file or URL.

    Args:
        source: File path or URL to the DCAT metadata.
        format_hint: Optional format hint ('json-ld', 'turtle'). If None, will try to detect.

    Returns:
        DCATMetadata object containing parsed information.

    Raises:
        DCATParseError: If the DCAT metadata cannot be parsed.
    """
    content, detected_format = _read_content(source)

    # Use provided format or detected one
    fmt = format_hint or detected_format

    # Try to detect format from content if still unknown
    if fmt == "unknown":
        content_stripped = content.strip()
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            fmt = "json-ld"
        elif "@prefix" in content or content_stripped.startswith("<"):
            fmt = "turtle"
        else:
            fmt = "json-ld"  # Default to JSON-LD

    if fmt == "json-ld":
        return _parse_json_ld(content, source)
    elif fmt in ("turtle", "ttl"):
        return _parse_turtle(content, source)
    else:
        # Try JSON-LD first, then Turtle
        try:
            return _parse_json_ld(content, source)
        except DCATParseError:
            try:
                return _parse_turtle(content, source)
            except Exception as e:
                raise DCATParseError(
                    f"Failed to parse DCAT metadata from '{source}'. "
                    f"Tried JSON-LD and Turtle formats. Error: {e}"
                ) from e
