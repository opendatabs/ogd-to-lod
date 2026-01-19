# OGD to LOD

Tool to create RML (RDF Mapping Language) mappings for CSV files using generative AI.

## Overview

This tool helps transform Open Government Data (OGD) CSV files into Linked Open Data (LOD) by:

1. Analyzing CSV structure and DCAT metadata
2. Using AI to propose RML mappings targeting cube.link and schema.org vocabularies
3. Validating mappings with RMLMapper
4. Creating GitHub PRs with the generated mappings

## Installation

### Prerequisites

- Python 3.11+
- Java (for RMLMapper validation)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/redlink-gmbh/ogd-to-lod.git
   cd ogd-to-lod
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. Configure the application:
   ```bash
   # Edit config/config.yaml with your settings
   ```

## Configuration

The application uses a YAML configuration file (`config/config.yaml`) with environment variable substitution.

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `repo` scope |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |

### Configuration File

```yaml
github:
  repo: "org/repo-name"
  token: "${GITHUB_TOKEN}"

azure:
  endpoint: "${AZURE_OPENAI_ENDPOINT}"
  api_key: "${AZURE_OPENAI_KEY}"
  deployment: "gpt-4"

sparql:
  endpoint: null  # Optional: for querying existing dimensions

rml:
  base_uri: "https://example.org/resource/"
```

## Usage

```bash
ogd-to-lod <csv_path> <dcat_path>
```

### Options

- `--config`, `-c`: Path to configuration file (default: `config/config.yaml`)
- `--help`: Show help message

## Development

### Running Tests

```bash
pytest
```

### Linting

```bash
ruff check .
ruff format .
```

## Project Structure

```
ogd-to-lod/
├── src/ogd_to_lod/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration management
│   ├── parsers/         # CSV and DCAT parsers
│   ├── ai/              # Azure OpenAI integration
│   ├── graph/           # LangGraph conversation flow
│   ├── github/          # GitHub PR creation
│   └── validation/      # RML validation
├── tests/
├── config/
│   └── config.yaml
├── pyproject.toml
└── README.md
```

## License

MIT
