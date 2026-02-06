"""Tests for RML validation module."""

import csv
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ogd_to_lod.validation import (
    RMLMapperNotFoundError,
    RMLValidationError,
    RMLValidator,
    ValidationResult,
    validate_rml,
)


# Sample RML for testing
SAMPLE_RML = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix cube: <https://cube.link/> .
@prefix ex: <https://example.org/> .

ex:TriplesMap a rr:TriplesMap ;
    rml:logicalSource [
        rml:source "data.csv" ;
        rml:referenceFormulation ql:CSV
    ] ;
    rr:subjectMap [
        rr:template "https://example.org/observation/{year}/{region}" ;
        rr:class cube:Observation
    ] ;
    rr:predicateObjectMap [
        rr:predicate cube:dimension ;
        rr:objectMap [
            rml:reference "year" ;
            rr:datatype xsd:gYear
        ]
    ] ;
    rr:predicateObjectMap [
        rr:predicate cube:dimension ;
        rr:objectMap [
            rml:reference "region" ;
            rr:datatype xsd:string
        ]
    ] ;
    rr:predicateObjectMap [
        rr:predicate cube:measure ;
        rr:objectMap [
            rml:reference "value" ;
            rr:datatype xsd:decimal
        ]
    ] .
"""

# Invalid RML (syntax error)
INVALID_RML_SYNTAX = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
This is not valid Turtle syntax!!!
"""

# RML missing components (valid syntax but missing logical source)
MINIMAL_RML = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ex: <http://example.org/> .

ex:Something rr:predicateObjectMap [ ] .
"""


@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write("year,region,value\n")
        f.write("2020,North,100.5\n")
        f.write("2021,South,200.3\n")
        f.write("2022,East,300.1\n")
        f.write("2023,West,400.7\n")
        f.write("2024,North,500.2\n")
        f.write("2025,South,600.9\n")
        f.write("2026,East,700.4\n")
        csv_path = f.name
    # File is now closed and flushed
    yield csv_path
    os.unlink(csv_path)


@pytest.fixture
def temp_csv_semicolon():
    """Create a temporary semicolon-delimited CSV file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write("year;region;value\n")
        f.write("2020;North;100.5\n")
        f.write("2021;South;200.3\n")
        f.write("2022;East;300.1\n")
        csv_path = f.name
    # File is now closed and flushed
    yield csv_path
    os.unlink(csv_path)


class TestRMLValidator:
    """Tests for RMLValidator class."""

    def test_init_default(self):
        """Test default initialization."""
        validator = RMLValidator()
        assert validator._rmlmapper_jar is None
        assert validator._use_docker is False

    def test_init_with_jar(self):
        """Test initialization with JAR path."""
        validator = RMLValidator(rmlmapper_jar="/path/to/rmlmapper.jar")
        assert validator._rmlmapper_jar == "/path/to/rmlmapper.jar"

    def test_init_with_docker(self):
        """Test initialization with Docker."""
        validator = RMLValidator(use_docker=True)
        assert validator._use_docker is True
        assert validator._docker_image == "rmlio/rmlmapper-java:latest"

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("RMLMAPPER_JAR", "/env/path/rmlmapper.jar")
        validator = RMLValidator()
        assert validator._rmlmapper_jar == "/env/path/rmlmapper.jar"

    def test_validate_syntax_only_valid(self):
        """Test syntax-only validation with valid RML."""
        validator = RMLValidator()  # No JAR configured
        result = validator.validate(SAMPLE_RML, "/nonexistent/path.csv")

        assert result.valid is True
        assert result.rdf_output is None  # No actual RDF generation

    def test_validate_syntax_only_invalid(self):
        """Test syntax-only validation with invalid RML."""
        validator = RMLValidator()
        result = validator.validate(INVALID_RML_SYNTAX, "/nonexistent/path.csv")

        assert result.valid is False
        assert "syntax error" in result.error_message.lower()

    def test_validate_syntax_only_with_warnings(self):
        """Test syntax-only validation produces warnings for missing components."""
        validator = RMLValidator()
        result = validator.validate_syntax(MINIMAL_RML)

        # Should be valid syntax but may have warnings
        assert result.valid is True
        # Warnings about missing logical source or subject map
        assert result.warnings is not None
        assert any(
            "logical source" in w.lower() or "subject map" in w.lower()
            for w in result.warnings
        )

    def test_validate_csv_not_found(self):
        """Test validation fails when CSV doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            result = validator.validate_with_rmlmapper(
                SAMPLE_RML, "/nonexistent/data.csv"
            )

            assert result.valid is False
            assert "not found" in result.error_message.lower()
        finally:
            os.unlink(jar_path)

    @patch("subprocess.run")
    def test_validate_with_jar_success(self, mock_run, temp_csv):
        """Test successful validation with JAR."""
        # Mock successful RMLMapper execution
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)

            # Need to mock the output file creation
            with patch.object(Path, "read_text", return_value="<rdf output>"):
                with patch.object(Path, "exists", return_value=True):
                    result = validator.validate(SAMPLE_RML, temp_csv)

            assert result.valid is True
            assert mock_run.called
        finally:
            os.unlink(jar_path)

    @patch("subprocess.run")
    def test_validate_with_jar_failure(self, mock_run, temp_csv):
        """Test validation failure with JAR."""
        # Mock failed RMLMapper execution
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Error: Invalid column reference 'unknown_column'",
        )

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            result = validator.validate(SAMPLE_RML, temp_csv)

            assert result.valid is False
            assert "unknown_column" in result.error_message
        finally:
            os.unlink(jar_path)

    @patch("subprocess.run")
    def test_validate_timeout(self, mock_run, temp_csv):
        """Test validation timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="java", timeout=60)

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            result = validator.validate(SAMPLE_RML, temp_csv, timeout=60)

            assert result.valid is False
            assert "timed out" in result.error_message.lower()
        finally:
            os.unlink(jar_path)

    def test_clean_error_message(self):
        """Test error message cleaning."""
        validator = RMLValidator()

        # Test with Java stack trace
        raw_error = """java.lang.RuntimeException: Error processing mapping
at be.ugent.rml.Executor.execute(Executor.java:123)
at be.ugent.rml.Main.main(Main.java:45)
Caused by: java.io.FileNotFoundException: file.csv
Invalid file path"""

        cleaned = validator._clean_error_message(raw_error)

        # Should not contain stack trace lines
        assert "at be.ugent" not in cleaned
        assert "Caused by:" not in cleaned
        # Should contain the actual error
        assert "Invalid file path" in cleaned

    def test_is_available_no_jar(self):
        """Test availability check with no JAR."""
        validator = RMLValidator()
        assert validator.is_available() is False

    def test_is_available_with_nonexistent_jar(self):
        """Test availability check with nonexistent JAR."""
        validator = RMLValidator(rmlmapper_jar="/nonexistent/path.jar")
        assert validator.is_available() is False

    def test_is_available_with_existing_jar(self):
        """Test availability check with existing JAR."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            assert validator.is_available() is True
        finally:
            os.unlink(jar_path)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid result creation."""
        result = ValidationResult(
            valid=True,
            rdf_output="<rdf content>",
        )
        assert result.valid is True
        assert result.rdf_output == "<rdf content>"
        assert result.error_message is None
        assert result.warnings is None
        assert result.error_category is None
        assert result.user_friendly_error is None

    def test_invalid_result(self):
        """Test invalid result creation."""
        result = ValidationResult(
            valid=False,
            error_message="Something went wrong",
        )
        assert result.valid is False
        assert result.rdf_output is None
        assert result.error_message == "Something went wrong"

    def test_result_with_warnings(self):
        """Test result with warnings."""
        result = ValidationResult(
            valid=True,
            warnings=["Warning 1", "Warning 2"],
        )
        assert result.valid is True
        assert len(result.warnings) == 2

    def test_result_with_error_category(self):
        """Test result with error categorisation fields."""
        result = ValidationResult(
            valid=False,
            error_message="Column 'foo' not found",
            error_category="missing_column",
            user_friendly_error="The mapping references a CSV column that does not exist.",
        )
        assert result.error_category == "missing_column"
        assert "does not exist" in result.user_friendly_error


class TestValidateRMLFunction:
    """Tests for the validate_rml convenience function."""

    def test_validate_rml_syntax_only(self):
        """Test convenience function with syntax-only validation."""
        result = validate_rml(SAMPLE_RML, "/nonexistent/path.csv")

        assert result.valid is True


class TestValidateSyntax:
    """Tests for the public validate_syntax() method (Tier 1)."""

    def test_valid_turtle(self):
        """Test syntax validation passes for valid Turtle."""
        validator = RMLValidator()
        result = validator.validate_syntax(SAMPLE_RML)

        assert result.valid is True
        assert result.error_message is None

    def test_invalid_turtle(self):
        """Test syntax validation fails for invalid Turtle."""
        validator = RMLValidator()
        result = validator.validate_syntax(INVALID_RML_SYNTAX)

        assert result.valid is False
        assert result.error_message is not None
        assert "syntax error" in result.error_message.lower()

    def test_minimal_valid_turtle(self):
        """Test syntax validation passes for minimal valid Turtle."""
        validator = RMLValidator()
        result = validator.validate_syntax(MINIMAL_RML)

        assert result.valid is True

    def test_empty_string(self):
        """Test syntax validation with empty string."""
        validator = RMLValidator()
        result = validator.validate_syntax("")

        # Empty RML is technically parseable Turtle but fails structural
        # checks (SPARQL queries reference undefined prefixes), so it's
        # correctly reported as invalid.
        assert result.valid is False


class TestValidateWithRMLMapper:
    """Tests for validate_with_rmlmapper() method (Tier 2)."""

    def test_skips_when_no_jar_configured(self):
        """Test Tier 2 gracefully skips when RMLMapper is not configured."""
        validator = RMLValidator()  # No JAR
        result = validator.validate_with_rmlmapper(SAMPLE_RML, "/some/path.csv")

        assert result.valid is True
        assert result.warnings is not None
        assert any("skipped" in w.lower() for w in result.warnings)

    def test_skips_when_jar_not_found(self):
        """Test Tier 2 gracefully skips when JAR file doesn't exist."""
        validator = RMLValidator(rmlmapper_jar="/nonexistent/rmlmapper.jar")
        result = validator.validate_with_rmlmapper(SAMPLE_RML, "/some/path.csv")

        assert result.valid is True
        assert result.warnings is not None
        assert any("not found" in w.lower() for w in result.warnings)

    def test_csv_not_found(self):
        """Test Tier 2 fails when CSV file doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            result = validator.validate_with_rmlmapper(
                SAMPLE_RML, "/nonexistent/data.csv"
            )

            assert result.valid is False
            assert result.error_category == "file_not_found"
        finally:
            os.unlink(jar_path)

    @patch("subprocess.run")
    def test_success_with_mocked_rmlmapper(self, mock_run, temp_csv):
        """Test successful Tier 2 validation with mocked RMLMapper."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            with patch.object(Path, "read_text", return_value="<rdf>"):
                with patch.object(Path, "exists", return_value=True):
                    result = validator.validate_with_rmlmapper(
                        SAMPLE_RML, temp_csv
                    )

            assert result.valid is True
            assert mock_run.called
        finally:
            os.unlink(jar_path)

    @patch("subprocess.run")
    def test_failure_with_mocked_rmlmapper(self, mock_run, temp_csv):
        """Test failed Tier 2 validation with mocked RMLMapper."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Error: Column 'foo' not found in CSV",
        )

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as jar_file:
            jar_path = jar_file.name

        try:
            validator = RMLValidator(rmlmapper_jar=jar_path)
            result = validator.validate_with_rmlmapper(SAMPLE_RML, temp_csv)

            assert result.valid is False
            assert result.error_category == "missing_column"
            assert result.user_friendly_error is not None
        finally:
            os.unlink(jar_path)


class TestSampleCSVExtraction:
    """Tests for _extract_sample_csv and _get_rml_source_filename."""

    def test_correct_filename_from_rml(self):
        """Test that source filename is parsed from RML content."""
        filename = RMLValidator._get_rml_source_filename(
            SAMPLE_RML, "/path/to/other.csv"
        )
        assert filename == "data.csv"

    def test_fallback_to_csv_path(self):
        """Test fallback to csv_path basename when RML has no source."""
        rml_no_source = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
ex:Map rr:subjectMap [ ] .
"""
        filename = RMLValidator._get_rml_source_filename(
            rml_no_source, "/path/to/mydata.csv"
        )
        assert filename == "mydata.csv"

    def test_sample_csv_row_count(self, temp_csv):
        """Test that sample CSV has the correct number of rows."""
        validator = RMLValidator()
        tmpdir = validator._extract_sample_csv(SAMPLE_RML, temp_csv, sample_rows=3)

        try:
            sample_path = Path(tmpdir.name) / "data.csv"
            assert sample_path.exists()

            with open(sample_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Header + 3 data rows = 4
            assert len(rows) == 4
            assert rows[0] == ["year", "region", "value"]
        finally:
            tmpdir.cleanup()

    def test_sample_csv_default_rows(self, temp_csv):
        """Test default sample size (5 rows)."""
        validator = RMLValidator()
        tmpdir = validator._extract_sample_csv(SAMPLE_RML, temp_csv)

        try:
            sample_path = Path(tmpdir.name) / "data.csv"
            with open(sample_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Header + 5 data rows = 6
            assert len(rows) == 6
        finally:
            tmpdir.cleanup()

    def test_semicolon_delimiter(self, temp_csv_semicolon):
        """Test that semicolon delimiters are preserved."""
        rml_with_source = SAMPLE_RML  # Uses "data.csv" but we'll use our fixture
        # Override the source filename to match
        rml_custom = SAMPLE_RML.replace('rml:source "data.csv"', 'rml:source "test.csv"')

        validator = RMLValidator()
        tmpdir = validator._extract_sample_csv(
            rml_custom, temp_csv_semicolon, sample_rows=2
        )

        try:
            sample_path = Path(tmpdir.name) / "test.csv"
            assert sample_path.exists()

            with open(sample_path, "r") as f:
                content = f.read()

            # Should contain semicolons (preserved delimiter)
            assert ";" in content

            # Parse and check row count
            with open(sample_path, "r") as f:
                reader = csv.reader(f, delimiter=";")
                rows = list(reader)

            assert len(rows) == 3  # header + 2 data rows
        finally:
            tmpdir.cleanup()

    def test_small_csv_fewer_rows_than_requested(self):
        """Test extraction from CSV with fewer rows than requested."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("a,b\n")
            f.write("1,2\n")
            csv_path = f.name

        try:
            validator = RMLValidator()
            tmpdir = validator._extract_sample_csv(
                SAMPLE_RML, csv_path, sample_rows=10
            )

            try:
                sample_path = Path(tmpdir.name) / "data.csv"
                with open(sample_path, "r") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                # Only header + 1 row available
                assert len(rows) == 2
            finally:
                tmpdir.cleanup()
        finally:
            os.unlink(csv_path)


class TestErrorCategorization:
    """Tests for _categorize_error."""

    def test_missing_column(self):
        """Test categorisation of missing column errors."""
        category, desc = RMLValidator._categorize_error(
            "Error: Column 'population' not found in CSV"
        )
        assert category == "missing_column"
        assert "column" in desc.lower()

    def test_invalid_iri(self):
        """Test categorisation of invalid IRI errors."""
        category, desc = RMLValidator._categorize_error(
            "Error: Invalid IRI generated from template"
        )
        assert category == "invalid_iri"
        assert "iri" in desc.lower() or "uri" in desc.lower()

    def test_type_mismatch(self):
        """Test categorisation of type mismatch errors."""
        category, desc = RMLValidator._categorize_error(
            "Error: Type mismatch — cannot cast 'abc' to xsd:integer"
        )
        assert category == "type_mismatch"
        assert "type" in desc.lower()

    def test_file_not_found(self):
        """Test categorisation of file not found errors."""
        category, desc = RMLValidator._categorize_error(
            "Error: File not found: data.csv"
        )
        assert category == "file_not_found"
        assert "file" in desc.lower()

    def test_syntax_error(self):
        """Test categorisation of syntax errors."""
        category, desc = RMLValidator._categorize_error(
            "Parse error at line 5: unexpected token"
        )
        assert category == "syntax_error"

    def test_unknown_error(self):
        """Test categorisation of unrecognised errors."""
        category, desc = RMLValidator._categorize_error(
            "Something completely unexpected happened"
        )
        assert category == "unknown"
        assert "Something completely unexpected" in desc


