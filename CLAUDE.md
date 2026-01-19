# Claude Code Project Configuration

## Project Overview

This is the OGD to LOD project - a tool to create RML (RDF Mapping Language) mappings for CSV files using generative AI.

## Allowed Operations

### Git Operations
- `git add`, `git commit`, `git push` - for committing and pushing changes
- `git rm`, `git reset` - for managing staged files

### GitHub CLI
- `gh issue create` - create issues in the repository
- `gh label create` - create labels for issues

### Python Development
- `python3` - run Python scripts
- `pip install` - install dependencies
- `pytest` - run tests
- `ogd-to-lod` - run the CLI tool

### Environment
- GitHub token available via `$GITHUB_TOKEN` environment variable (from `.env`)
- Azure OpenAI credentials via `$AZURE_OPENAI_ENDPOINT` and `$AZURE_OPENAI_KEY`

## Project Structure

```
ogd-to-lod/
├── src/ogd_to_lod/    # Main package
│   ├── parsers/       # CSV and DCAT parsers
│   ├── ai/            # Azure OpenAI integration
│   ├── graph/         # LangGraph conversation flow
│   ├── github/        # GitHub PR creation
│   └── validation/    # RML validation
├── tests/             # Test files
├── config/            # Configuration files
├── brainstorm.md      # Project requirements
└── architecture.md    # Technical architecture
```

## Key Documentation

- `brainstorm.md` - Project goals, milestones (MVP, V1, Later), and scope
- `architecture.md` - Tech stack, conversation flow, LangGraph states, prompting strategy

## GitHub Repository

- Repository: `redlink-gmbh/ogd-to-lod`
- Issues: MVP issues #1-#10 are created

## Development Workflow

1. Work on issues from the GitHub issue tracker
2. Run tests with `pytest`
3. Commit with descriptive messages referencing issue numbers
4. Push to main branch
