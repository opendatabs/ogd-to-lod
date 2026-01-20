#!/usr/bin/env python3
"""Integration test script for the OGD to LOD mapping flow.

This script runs the mapping flow with real data and shows what happens
at each step. It uses a mock AI service by default to avoid API costs,
but can be run with a real AI service by setting USE_REAL_AI=1.

Usage:
    python scripts/integration_test.py
    USE_REAL_AI=1 python scripts/integration_test.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ogd_to_lod.config import load_config
from ogd_to_lod.graph import MappingFlow, FlowState
from ogd_to_lod.graph.nodes import init_node, analyze_node
from ogd_to_lod.graph.state import GraphState


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data" / "bs" / "lod-ki-test"
CSV_PATH = DATA_DIR / "data.csv"
DCAT_PATH = DATA_DIR / "dcat.ttl"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def create_mock_ai_service():
    """Create a mock AI service for testing without API calls."""
    service = MagicMock()

    # Mock proposal response
    service.send_message.return_value = """Based on the CSV schema and DCAT metadata, I propose the following mapping structure:

## Analysis

This is an air quality dataset from Basel-Binningen with hourly measurements. The data contains:
- **Temporal dimension**: `Datum/Zeit` - ISO 8601 timestamps
- **Measures**: Various air quality metrics (O3, NO2, PM10, PM2.5, etc.) and weather data (TEMP, PREC, RAD)

## Proposed Mapping

```yaml
dimensions:
  - column: Datum/Zeit
    type: temporal
    granularity: hour
    hierarchy: year > month > day > hour

measures:
  - column: O3 [ug/m3]
    unit: microgram per cubic meter
    aggregation: average
  - column: NO2 [ug/m3]
    unit: microgram per cubic meter
    aggregation: average
  - column: PM10 [ug/m3]
    unit: microgram per cubic meter
    aggregation: average
  - column: PM2.5 [ug/m3]
    unit: microgram per cubic meter
    aggregation: average
  - column: TEMP [C]
    unit: degree Celsius
    aggregation: average
  - column: PREC [mm]
    unit: millimeter
    aggregation: sum
  - column: RAD [W/m2]
    unit: watt per square meter
    aggregation: average
```

The `timestamp_text` column appears to be a human-readable version of `Datum/Zeit` and can be ignored in the mapping.

Do you want me to proceed with this mapping, or would you like to make any changes?
"""
    return service


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_state(state: GraphState):
    """Print relevant state information."""
    print(f"  Current state: {state.current_state.value}")
    print(f"  Awaiting input: {state.awaiting_user_input}")
    if state.error_message:
        print(f"  Error: {state.error_message}")


def test_init_and_analyze():
    """Test the INIT and ANALYZE phases independently."""
    print_section("Phase 1: INIT and ANALYZE (no AI needed)")

    # Load config
    config = load_config(str(CONFIG_PATH))
    print(f"\n  Config loaded from: {CONFIG_PATH}")
    print(f"  Base URI: {config.rml.base_uri}")

    # Create initial state
    state = GraphState(
        csv_path=str(CSV_PATH),
        dcat_path=str(DCAT_PATH),
    )
    print(f"\n  CSV path: {state.csv_path}")
    print(f"  DCAT path: {state.dcat_path}")

    # Run INIT
    print("\n  Running init_node...")
    state = init_node(state, config)
    print_state(state)

    if state.current_state == FlowState.ERROR:
        print(f"\n  INIT FAILED: {state.error_message}")
        return None, None

    # Run ANALYZE
    print("\n  Running analyze_node...")
    state = analyze_node(state, config)
    print_state(state)

    if state.current_state == FlowState.ERROR:
        print(f"\n  ANALYZE FAILED: {state.error_message}")
        return None, None

    # Show parsed data
    print("\n  CSV Schema:")
    if state.csv_schema:
        print(f"    Source: {state.csv_schema.get('source')}")
        print(f"    Total rows: {state.csv_schema.get('total_rows')}")
        print(f"    Columns ({len(state.csv_schema.get('columns', []))}):")
        for col in state.csv_schema.get("columns", [])[:5]:
            samples = ", ".join(str(s) for s in col.get("samples", [])[:2])
            print(f"      - {col['name']} ({col['type']}): {samples}")
        if len(state.csv_schema.get("columns", [])) > 5:
            print(f"      ... and {len(state.csv_schema.get('columns', [])) - 5} more columns")

    print("\n  DCAT Metadata:")
    if state.dcat_metadata:
        print(f"    Title: {state.dcat_metadata.get('title')}")
        print(f"    Publisher: {state.dcat_metadata.get('publisher')}")
        if state.dcat_metadata.get("keywords"):
            keywords = state.dcat_metadata["keywords"][:5]
            print(f"    Keywords: {', '.join(keywords)}")

    return state, config


def test_full_flow_with_mock():
    """Test the full flow with a mock AI service."""
    print_section("Phase 2: Full Flow with Mock AI")

    # Load config
    config = load_config(str(CONFIG_PATH))

    # Create mock AI service
    mock_ai = create_mock_ai_service()

    # Create flow
    flow = MappingFlow(config, ai_service=mock_ai)
    print("\n  MappingFlow created with mock AI service")

    # Start flow
    print("\n  Starting flow...")
    state = flow.start(
        csv_path=str(CSV_PATH),
        dcat_path=str(DCAT_PATH),
    )
    print_state(state)

    if state.current_state == FlowState.ERROR:
        print(f"\n  FLOW FAILED: {state.error_message}")
        return

    # Show proposal
    print("\n  AI Proposal:")
    proposal_text = flow.get_proposal_text()
    if proposal_text:
        # Show first 500 chars
        preview = proposal_text[:500]
        print(f"    {preview}...")

    # Show parsed proposal
    if state.mapping_proposal:
        print(f"\n  Parsed Proposal:")
        print(f"    Dimensions: {len(state.mapping_proposal.dimensions)}")
        for dim in state.mapping_proposal.dimensions:
            print(f"      - {dim.column} ({dim.dimension_type})")
        print(f"    Measures: {len(state.mapping_proposal.measures)}")
        for measure in state.mapping_proposal.measures[:3]:
            print(f"      - {measure.column} ({measure.unit})")
        if len(state.mapping_proposal.measures) > 3:
            print(f"      ... and {len(state.mapping_proposal.measures) - 3} more")

    # Simulate user approval
    print("\n  Simulating user approval...")
    mock_ai.send_message.return_value = "APPROVE"
    state = flow.continue_with_input("looks good, proceed")
    print_state(state)

    if flow.is_approved():
        print("\n  SUCCESS: Proposal approved!")
        print("  Next step would be RML generation (Issue #7)")

    return state


def test_full_flow_with_real_ai():
    """Test with real AI service (requires API key)."""
    print_section("Phase 3: Full Flow with Real AI")

    # Load config
    config = load_config(str(CONFIG_PATH))

    # Create flow with real AI
    flow = MappingFlow(config)
    print("\n  MappingFlow created with real AI service")
    print(f"  Azure endpoint: {config.azure.endpoint}")
    print(f"  Deployment: {config.azure.deployment}")

    # Start flow
    print("\n  Starting flow (this will call Azure OpenAI)...")
    try:
        state = flow.start(
            csv_path=str(CSV_PATH),
            dcat_path=str(DCAT_PATH),
        )
        print_state(state)

        if state.current_state == FlowState.ERROR:
            print(f"\n  FLOW FAILED: {state.error_message}")
            return

        # Show full proposal
        print("\n  AI Proposal (from Azure OpenAI):")
        print("-" * 60)
        proposal_text = flow.get_proposal_text()
        if proposal_text:
            print(proposal_text)
        print("-" * 60)

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run integration tests."""
    print("\n" + "#" * 70)
    print("#  OGD to LOD - Integration Test")
    print("#" * 70)

    # Check test data exists
    if not CSV_PATH.exists():
        print(f"\nERROR: CSV file not found: {CSV_PATH}")
        return 1
    if not DCAT_PATH.exists():
        print(f"\nERROR: DCAT file not found: {DCAT_PATH}")
        return 1
    if not CONFIG_PATH.exists():
        print(f"\nERROR: Config file not found: {CONFIG_PATH}")
        return 1

    print(f"\n  Test data: {DATA_DIR}")
    print(f"  CSV: {CSV_PATH.name}")
    print(f"  DCAT: {DCAT_PATH.name}")

    # Phase 1: Test init and analyze (no AI)
    state, config = test_init_and_analyze()
    if state is None:
        return 1

    # Phase 2: Test full flow with mock AI
    test_full_flow_with_mock()

    # Phase 3: Test with real AI if requested
    if os.environ.get("USE_REAL_AI") == "1":
        print(f"Azure Endpoint: {os.environ.get("AZURE_OPENAI_ENDPOINT")}")
        test_full_flow_with_real_ai()
    else:
        print_section("Phase 3: Skipped (Real AI)")
        print("\n  Set USE_REAL_AI=1 to test with real Azure OpenAI")

    print_section("Integration Test Complete")
    print("\n  All phases completed successfully!\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
