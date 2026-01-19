"""CLI entry point for OGD to LOD tool."""

import argparse
import sys

from ogd_to_lod.config import load_config


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="ogd-to-lod",
        description="Create RML mappings for CSV files using generative AI",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Path to the CSV file to map",
    )
    parser.add_argument(
        "dcat_path",
        nargs="?",
        help="Path to the DCAT metadata file (JSON-LD or Turtle)",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid configuration: {e}", file=sys.stderr)
        return 1

    # TODO: Implement conversation flow (Issue #4)
    print("OGD to LOD - RML Mapping Tool")
    print(f"Configuration loaded from: {args.config}")

    if args.csv_path and args.dcat_path:
        print(f"CSV file: {args.csv_path}")
        print(f"DCAT file: {args.dcat_path}")
        print("\nConversation flow not yet implemented. See Issue #4.")
    else:
        print("\nUsage: ogd-to-lod <csv_path> <dcat_path>")
        print("Run 'ogd-to-lod --help' for more information.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
