"""Tests for RML generation module."""

import pytest
from unittest.mock import MagicMock, patch

from ogd_to_lod.config import Config, GitHubConfig, AzureOpenAIConfig, RMLConfig
from ogd_to_lod.rml import RMLGenerator, RMLGenerationError, generate_rml
from ogd_to_lod.rml.prompts import RML_GENERATION_PROMPT
from ogd_to_lod.graph.state import (
    DimensionProposal,
    FlowState,
    GraphState,
    MappingProposal,
    MeasureProposal,
)
from ogd_to_lod.graph.nodes import generate_node


# Sample RML output for testing
SAMPLE_RML_OUTPUT = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#> .
@prefix ql: <http://semweb.mmlab.be/ns/ql#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix cube: <https://cube.link/> .
@prefix ex: <https://example.org/> .

ex:TriplesMap a rr:TriplesMap ;
    rml:logicalSource [
        rml:source "/path/to/data.csv" ;
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


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service that returns sample RML."""
    service = MagicMock()
    service.send_message.return_value = f"""Here is the generated RML mapping:

```turtle
{SAMPLE_RML_OUTPUT}
```

This mapping creates observations from the CSV data with year and region as dimensions and value as a measure.
"""
    return service


@pytest.fixture
def sample_mapping_proposal():
    """Create a sample approved mapping proposal."""
    return {
        "dimensions": [
            {"column": "year", "type": "temporal", "granularity": "year"},
            {"column": "region", "type": "spatial"},
        ],
        "measures": [
            {"column": "value", "unit": "count"},
        ],
        "status": "approved",
    }


@pytest.fixture
def sample_csv_schema():
    """Create a sample CSV schema."""
    return {
        "source": "/path/to/data.csv",
        "columns": [
            {"name": "year", "type": "int", "samples": [2020, 2021, 2022]},
            {"name": "region", "type": "string", "samples": ["North", "South", "East"]},
            {"name": "value", "type": "float", "samples": [100.5, 200.3, 150.0]},
        ],
        "total_rows": 1000,
    }


class TestRMLGenerator:
    """Tests for RMLGenerator class."""

    def test_generate_success(self, mock_ai_service, sample_mapping_proposal, sample_csv_schema):
        """Test successful RML generation."""
        generator = RMLGenerator(mock_ai_service)

        result = generator.generate(
            mapping_proposal=sample_mapping_proposal,
            csv_schema=sample_csv_schema,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
        )

        assert result is not None
        assert "@prefix rr:" in result
        assert "@prefix rml:" in result
        assert "cube:Observation" in result
        mock_ai_service.send_message.assert_called_once()

    def test_generate_no_turtle_block(self, mock_ai_service, sample_mapping_proposal, sample_csv_schema):
        """Test generation fails when no Turtle block is returned."""
        mock_ai_service.send_message.return_value = "Here is some text without any code block."

        generator = RMLGenerator(mock_ai_service)

        with pytest.raises(RMLGenerationError) as exc_info:
            generator.generate(
                mapping_proposal=sample_mapping_proposal,
                csv_schema=sample_csv_schema,
                csv_path="/path/to/data.csv",
                base_uri="https://example.org/",
            )

        assert "AI did not generate valid RML Turtle output" in str(exc_info.value)

    def test_generate_ai_error(self, mock_ai_service, sample_mapping_proposal, sample_csv_schema):
        """Test generation handles AI service errors."""
        mock_ai_service.send_message.side_effect = Exception("API error")

        generator = RMLGenerator(mock_ai_service)

        with pytest.raises(RMLGenerationError) as exc_info:
            generator.generate(
                mapping_proposal=sample_mapping_proposal,
                csv_schema=sample_csv_schema,
                csv_path="/path/to/data.csv",
                base_uri="https://example.org/",
            )

        assert "Failed to generate RML" in str(exc_info.value)

    def test_format_proposal(self, mock_ai_service, sample_mapping_proposal):
        """Test proposal formatting for AI prompt."""
        generator = RMLGenerator(mock_ai_service)

        result = generator._format_proposal(sample_mapping_proposal)

        assert "### Dimensions:" in result
        assert "year: temporal" in result
        assert "region: spatial" in result
        assert "### Measures:" in result
        assert "value" in result

    def test_format_schema(self, mock_ai_service, sample_csv_schema):
        """Test schema formatting for AI prompt."""
        generator = RMLGenerator(mock_ai_service)

        result = generator._format_schema(sample_csv_schema)

        assert "Source: /path/to/data.csv" in result
        assert "Total rows: 1000" in result
        assert "year (int)" in result
        assert "region (string)" in result
        assert "value (float)" in result


class TestGenerateRMLFunction:
    """Tests for the generate_rml convenience function."""

    def test_generate_rml_function(self, mock_ai_service, sample_mapping_proposal, sample_csv_schema):
        """Test the convenience function."""
        result = generate_rml(
            ai_service=mock_ai_service,
            mapping_proposal=sample_mapping_proposal,
            csv_schema=sample_csv_schema,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
        )

        assert result is not None
        assert "@prefix rr:" in result


class TestGenerateNode:
    """Tests for the generate_node function."""

    def test_generate_node_success(self, mock_ai_service):
        """Test successful RML generation via node."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
            csv_schema={
                "source": "/path/to/data.csv",
                "columns": [
                    {"name": "year", "type": "int", "samples": [2020]},
                    {"name": "value", "type": "float", "samples": [100.0]},
                ],
                "total_rows": 100,
            },
            mapping_proposal=MappingProposal(
                dimensions=[DimensionProposal(column="year", dimension_type="temporal")],
                measures=[MeasureProposal(column="value")],
                status="approved",
            ),
        )

        result = generate_node(state, mock_ai_service)

        assert result.generated_rml is not None
        assert result.current_state == FlowState.PREVIEW
        assert "@prefix rr:" in result.generated_rml

    def test_generate_node_no_proposal(self, mock_ai_service):
        """Test generate node fails without mapping proposal."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
            csv_schema={"columns": []},
        )

        result = generate_node(state, mock_ai_service)

        assert result.current_state == FlowState.ERROR
        assert "No mapping proposal" in result.error_message

    def test_generate_node_not_approved(self, mock_ai_service):
        """Test generate node fails with unapproved proposal."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
            csv_schema={"columns": []},
            mapping_proposal=MappingProposal(status="pending"),
        )

        result = generate_node(state, mock_ai_service)

        assert result.current_state == FlowState.ERROR
        assert "must be approved" in result.error_message

    def test_generate_node_no_csv_schema(self, mock_ai_service):
        """Test generate node fails without CSV schema."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            csv_path="/path/to/data.csv",
            base_uri="https://example.org/",
            mapping_proposal=MappingProposal(status="approved"),
        )

        result = generate_node(state, mock_ai_service)

        assert result.current_state == FlowState.ERROR
        assert "CSV schema is required" in result.error_message

    def test_generate_node_no_csv_path(self, mock_ai_service):
        """Test generate node fails without CSV path."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            base_uri="https://example.org/",
            csv_schema={"columns": []},
            mapping_proposal=MappingProposal(status="approved"),
        )

        result = generate_node(state, mock_ai_service)

        assert result.current_state == FlowState.ERROR
        assert "CSV path is required" in result.error_message

    def test_generate_node_no_base_uri(self, mock_ai_service):
        """Test generate node fails without base URI."""
        state = GraphState(
            current_state=FlowState.GENERATE,
            csv_path="/path/to/data.csv",
            csv_schema={"columns": []},
            mapping_proposal=MappingProposal(status="approved"),
        )

        result = generate_node(state, mock_ai_service)

        assert result.current_state == FlowState.ERROR
        assert "Base URI is required" in result.error_message


class TestRMLPrompts:
    """Tests for RML generation prompts."""

    def test_prompt_has_required_prefixes(self):
        """Test that the prompt includes required vocabulary prefixes."""
        assert "rr:" in RML_GENERATION_PROMPT
        assert "rml:" in RML_GENERATION_PROMPT
        assert "cube:" in RML_GENERATION_PROMPT
        assert "schema:" in RML_GENERATION_PROMPT
        assert "xsd:" in RML_GENERATION_PROMPT

    def test_prompt_has_placeholders(self):
        """Test that the prompt has required placeholders."""
        assert "{base_uri}" in RML_GENERATION_PROMPT
        assert "{csv_path}" in RML_GENERATION_PROMPT
        assert "{mapping_proposal}" in RML_GENERATION_PROMPT
        assert "{csv_schema}" in RML_GENERATION_PROMPT

    def test_prompt_mentions_cube_link(self):
        """Test that the prompt mentions cube.link vocabulary."""
        assert "cube.link" in RML_GENERATION_PROMPT
        assert "cube:Observation" in RML_GENERATION_PROMPT
        assert "cube:dimension" in RML_GENERATION_PROMPT
        assert "cube:measure" in RML_GENERATION_PROMPT

    def test_prompt_mentions_schema_org(self):
        """Test that the prompt mentions schema.org vocabulary."""
        assert "schema.org" in RML_GENERATION_PROMPT
        assert "DefinedTerm" in RML_GENERATION_PROMPT
        assert "DefinedTermSet" in RML_GENERATION_PROMPT
