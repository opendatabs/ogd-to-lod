"""Tests for the LangGraph conversation flow."""

import pytest
from unittest.mock import MagicMock, patch

from ogd_to_lod.config import Config, GitHubConfig, AzureOpenAIConfig, RMLConfig
from ogd_to_lod.graph.state import (
    DimensionProposal,
    FlowState,
    GraphState,
    MappingProposal,
    MeasureProposal,
    UserIntent,
)
from ogd_to_lod.graph.nodes import (
    init_node,
    analyze_node,
    propose_node,
    handle_user_input,
    _build_summary,
    _build_ai_context,
    _parse_proposal,
)
from ogd_to_lod.graph.flow import MappingFlow


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return Config(
        github=GitHubConfig(repo="test/repo", token="test-token"),
        azure=AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        ),
        rml=RMLConfig(base_uri="https://example.org/"),
    )


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service."""
    service = MagicMock()
    service.send_message.return_value = """Based on the data, I suggest:

**Dimensions:**
- `year` - temporal dimension
- `region` - spatial dimension

**Measures:**
- `value` - count measure

```yaml
dimensions:
  - column: year
    type: temporal
    granularity: year
  - column: region
    type: spatial
measures:
  - column: value
    unit: count
```
"""
    service.parse_response = MagicMock(side_effect=lambda x: MagicMock(
        text="Based on the data...",
        code_blocks=[MagicMock(language="yaml", content="""dimensions:
  - column: year
    type: temporal
    granularity: year
  - column: region
    type: spatial
measures:
  - column: value
    unit: count""")],
        get_yaml_blocks=MagicMock(return_value=["""dimensions:
  - column: year
    type: temporal
    granularity: year
  - column: region
    type: spatial
measures:
  - column: value
    unit: count"""]),
    ))
    return service


class TestGraphState:
    """Tests for GraphState dataclass."""

    def test_initial_state(self):
        """Test default state initialization."""
        state = GraphState()
        assert state.current_state == FlowState.INIT
        assert state.csv_path is None
        assert state.messages == []
        assert state.awaiting_user_input is False

    def test_add_message(self):
        """Test adding messages to history."""
        state = GraphState()
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there!")

        assert len(state.messages) == 2
        assert state.messages[0] == {"role": "user", "content": "Hello"}
        assert state.messages[1] == {"role": "assistant", "content": "Hi there!"}

    def test_get_last_ai_message(self):
        """Test getting last AI message."""
        state = GraphState()
        state.add_message("user", "Question")
        state.add_message("assistant", "First answer")
        state.add_message("user", "Follow up")
        state.add_message("assistant", "Second answer")

        assert state.get_last_ai_message() == "Second answer"

    def test_get_last_ai_message_empty(self):
        """Test getting last AI message when none exist."""
        state = GraphState()
        state.add_message("user", "Question")
        assert state.get_last_ai_message() is None

    def test_to_dict(self):
        """Test state serialization."""
        state = GraphState(
            csv_path="/path/to/file.csv",
            base_uri="https://example.org/",
        )
        result = state.to_dict()

        assert result["csv_path"] == "/path/to/file.csv"
        assert result["base_uri"] == "https://example.org/"
        assert result["current_state"] == "init"


class TestMappingProposal:
    """Tests for MappingProposal dataclass."""

    def test_empty_proposal(self):
        """Test empty proposal creation."""
        proposal = MappingProposal()
        assert proposal.dimensions == []
        assert proposal.measures == []
        assert proposal.status == "pending"

    def test_proposal_with_data(self):
        """Test proposal with dimensions and measures."""
        proposal = MappingProposal(
            dimensions=[
                DimensionProposal(column="year", dimension_type="temporal"),
                DimensionProposal(column="region", dimension_type="spatial"),
            ],
            measures=[
                MeasureProposal(column="value", unit="count"),
            ],
        )

        assert len(proposal.dimensions) == 2
        assert len(proposal.measures) == 1
        assert proposal.dimensions[0].column == "year"

    def test_proposal_to_dict(self):
        """Test proposal serialization."""
        proposal = MappingProposal(
            dimensions=[
                DimensionProposal(column="year", dimension_type="temporal", granularity="year"),
            ],
            measures=[
                MeasureProposal(column="value", unit="count"),
            ],
            status="approved",
        )

        result = proposal.to_dict()

        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["column"] == "year"
        assert result["dimensions"][0]["type"] == "temporal"
        assert result["status"] == "approved"


class TestInitNode:
    """Tests for init_node function."""

    def test_init_with_valid_csv(self, mock_config):
        """Test init with valid CSV path."""
        state = GraphState(csv_path="/path/to/file.csv")
        result = init_node(state, mock_config)

        assert result.current_state == FlowState.ANALYZE
        assert result.base_uri == "https://example.org/"

    def test_init_without_csv(self, mock_config):
        """Test init without CSV path."""
        state = GraphState()
        result = init_node(state, mock_config)

        assert result.current_state == FlowState.ERROR
        assert "CSV path is required" in result.error_message

    def test_init_with_custom_base_uri(self, mock_config):
        """Test init preserves custom base URI."""
        state = GraphState(
            csv_path="/path/to/file.csv",
            base_uri="https://custom.org/",
        )
        result = init_node(state, mock_config)

        assert result.base_uri == "https://custom.org/"


class TestAnalyzeNode:
    """Tests for analyze_node function."""

    @patch("ogd_to_lod.graph.nodes.parse_csv")
    def test_analyze_csv_success(self, mock_parse_csv, mock_config):
        """Test successful CSV analysis."""
        from ogd_to_lod.parsers.models import CSVData, ColumnInfo, ColumnType

        mock_parse_csv.return_value = CSVData(
            source="/path/to/file.csv",
            columns=[
                ColumnInfo(name="year", detected_type=ColumnType.INTEGER, sample_values=[2020, 2021]),
                ColumnInfo(name="value", detected_type=ColumnType.FLOAT, sample_values=[1.5, 2.5]),
            ],
            sample_rows=[{"year": 2020, "value": 1.5}],
            total_rows=100,
        )

        state = GraphState(csv_path="/path/to/file.csv")
        state.current_state = FlowState.ANALYZE

        result = analyze_node(state, mock_config)

        assert result.current_state == FlowState.PROPOSE
        assert result.csv_schema is not None
        assert len(result.csv_schema["columns"]) == 2
        assert result.parsed_summary is not None

    @patch("ogd_to_lod.graph.nodes.parse_csv")
    def test_analyze_csv_failure(self, mock_parse_csv, mock_config):
        """Test CSV analysis failure."""
        from ogd_to_lod.parsers import CSVParseError

        mock_parse_csv.side_effect = CSVParseError("Invalid CSV")

        state = GraphState(csv_path="/invalid/file.csv")
        state.current_state = FlowState.ANALYZE

        result = analyze_node(state, mock_config)

        assert result.current_state == FlowState.ERROR
        assert "Failed to parse CSV" in result.error_message


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_build_summary_with_csv(self):
        """Test summary building with CSV data."""
        csv_schema = {
            "source": "/path/to/file.csv",
            "columns": [
                {"name": "year", "type": "int", "samples": [2020, 2021]},
                {"name": "value", "type": "float", "samples": [1.5, 2.5]},
            ],
            "total_rows": 100,
        }

        summary = _build_summary(csv_schema, None)

        assert "CSV Schema" in summary
        assert "year" in summary
        assert "value" in summary
        assert "100" in summary

    def test_build_summary_with_dcat(self):
        """Test summary building with DCAT metadata."""
        dcat_metadata = {
            "title": "Test Dataset",
            "description": "A test dataset for testing",
            "publisher": "Test Org",
            "keywords": ["test", "data"],
        }

        summary = _build_summary(None, dcat_metadata)

        assert "DCAT Metadata" in summary
        assert "Test Dataset" in summary
        assert "Test Org" in summary

    def test_parse_proposal(self):
        """Test parsing YAML proposal data."""
        data = {
            "dimensions": [
                {"column": "year", "type": "temporal", "granularity": "year"},
                {"column": "region", "type": "spatial"},
            ],
            "measures": [
                {"column": "value", "unit": "count"},
            ],
        }

        proposal = _parse_proposal(data)

        assert len(proposal.dimensions) == 2
        assert len(proposal.measures) == 1
        assert proposal.dimensions[0].column == "year"
        assert proposal.dimensions[0].dimension_type == "temporal"
        assert proposal.measures[0].unit == "count"


class TestUserIntentHandling:
    """Tests for user intent handling."""

    def test_approve_intent(self, mock_ai_service):
        """Test handling approval intent."""
        mock_ai_service.send_message.return_value = "APPROVE"

        state = GraphState(
            current_state=FlowState.PROPOSE,
            mapping_proposal=MappingProposal(),
        )

        result = handle_user_input(state, "looks good", mock_ai_service)

        assert result.user_intent == UserIntent.APPROVE
        assert result.current_state == FlowState.GENERATE
        assert result.mapping_proposal.status == "approved"

    def test_override_intent(self, mock_ai_service):
        """Test handling override intent."""
        mock_ai_service.send_message.return_value = "OVERRIDE"

        state = GraphState(
            current_state=FlowState.PROPOSE,
            mapping_proposal=MappingProposal(),
        )

        result = handle_user_input(state, "change year to categorical", mock_ai_service)

        assert result.user_intent == UserIntent.OVERRIDE
        assert result.current_state == FlowState.REFINE
        assert result.mapping_proposal.status == "refining"

    def test_question_intent(self, mock_ai_service):
        """Test handling question intent."""
        mock_ai_service.send_message.return_value = "QUESTION"

        state = GraphState(
            current_state=FlowState.PROPOSE,
            mapping_proposal=MappingProposal(),
        )

        result = handle_user_input(state, "why did you choose temporal?", mock_ai_service)

        assert result.user_intent == UserIntent.QUESTION
        assert result.current_state == FlowState.REFINE


class TestMappingFlow:
    """Tests for MappingFlow class."""

    @patch("ogd_to_lod.graph.flow.analyze_node")
    @patch("ogd_to_lod.graph.flow.init_node")
    def test_flow_initialization(self, mock_init, mock_analyze, mock_config, mock_ai_service):
        """Test flow initialization."""
        mock_init.return_value = GraphState(current_state=FlowState.ANALYZE)
        mock_analyze.return_value = GraphState(current_state=FlowState.PROPOSE)

        flow = MappingFlow(mock_config, mock_ai_service)

        assert flow.state.current_state == FlowState.INIT
        assert flow.ai_service == mock_ai_service

    def test_is_awaiting_input(self, mock_config, mock_ai_service):
        """Test is_awaiting_input method."""
        flow = MappingFlow(mock_config, mock_ai_service)
        flow._state.awaiting_user_input = True

        assert flow.is_awaiting_input() is True

    def test_is_complete(self, mock_config, mock_ai_service):
        """Test is_complete method."""
        flow = MappingFlow(mock_config, mock_ai_service)

        assert flow.is_complete() is False

        flow._state.current_state = FlowState.END
        assert flow.is_complete() is True

        flow._state.current_state = FlowState.ERROR
        assert flow.is_complete() is True

    def test_is_approved(self, mock_config, mock_ai_service):
        """Test is_approved method."""
        flow = MappingFlow(mock_config, mock_ai_service)

        assert flow.is_approved() is False

        flow._state.mapping_proposal = MappingProposal(status="approved")
        assert flow.is_approved() is True
