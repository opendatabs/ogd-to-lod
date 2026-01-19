# Architecture & Tech Stack

## 1. Tech Stack (Decisions)

### Language
- **Python** - Strong RDF ecosystem (rdflib), good AI libraries, widely used for data processing

### AI Integration
- **Azure OpenAI (GPT)**
- **LangGraph** - State machine for multi-step conversation flow
- **langchain-openai** - Azure OpenAI integration for LangGraph

### RML Processing (for validation/preview only)
- **RMLMapper** (Java-based) - most mature option
- **MVP:** subprocess call (requires local Java install)
- **Later:** Docker exec (no manual installation needed)

### SPARQL Client
- **SPARQLWrapper**

### GitHub Integration
- **PyGithub**

### Conversation Interface
- **MVP: CLI** - Quick to build, no external dependencies
- **Later: Streamlit** - Chat-like web UI, easy to build on Python backend

### Runtime
- **MVP: Local** - Run on developer machine
- **Target: Service** - Deployable as web service (e.g., FastAPI + Streamlit, or containerized)

## 2. Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Conversation Interface                       │
│                       (CLI / Streamlit)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Conversation Manager (LangGraph)                │
│         (State machine: orchestrates flow, handles overrides)    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Input Parser │    │  AI Service   │    │ SPARQL Client │
│  (CSV + DCAT) │    │ (Azure GPT)   │    │ (Query dims)  │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RML Generator                               │
│            (Creates RML from AI suggestions)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RML Validator                               │
│        (Runs mapping against sample, checks output)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Integration                            │
│         (Create branch, commit files, open PR)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Config Manager                              │
│     (SPARQL endpoint, base URI, other memorable things)          │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Data Flow (MVP)

1. User provides CSV file + DCAT metadata
2. Input Parser extracts schema (columns, types) from CSV and metadata from DCAT
3. Conversation Manager sends context to AI Service
4. AI Service suggests RML mapping structure
5. User reviews/overrides suggestions in conversation
6. RML Generator creates RML file
7. RML Validator runs mapping against sample rows
8. If valid: GitHub Integration creates PR
9. If invalid: Loop back to step 4 with error context

## 4. Conversation Flow

### Phase 1: INITIALIZATION ⏸️ (confirmation required)
- User provides: CSV file path + DCAT metadata (file or URL)
- If first time: User provides base URI pattern
- Tool loads config (GitHub repo, token, SPARQL endpoint, base URI)
- **User confirms** inputs are correct before proceeding

### Phase 2: ANALYSIS
- Tool extracts: column names, detected types, sample values (first few rows)
- Tool parses: DCAT metadata (title, description, publisher, etc.)
- Tool displays summary to user
- AI may **ask clarifying questions** if data is ambiguous (e.g., unclear column purpose)

### Phase 3: MAPPING PROPOSAL ⏸️ (confirmation required)
- AI proposes (high-level summary):
  - Which columns → dimensions vs measures
  - Dimension types (temporal, spatial, categorical)
  - Suggested hierarchies
  - Units for measures
  - Proposed reuse of existing dimensions (V1)
- **User reviews and confirms** or requests changes

### Phase 4: REFINEMENT ⏸️ (loop until approved)
- User can:
  - Override specific suggestions ("Column X should be a dimension, not a measure")
  - Ask questions ("Why did you choose this hierarchy?")
  - Make suggestions ("I think this hierarchy is better")
  - Request alternatives ("Show me other options for this dimension")
- AI adjusts proposal and re-presents
- **User explicitly approves** final mapping

### Phase 5: GENERATION
- Tool generates full RML
- Tool shows full RML to user for review 
- Tool validates RML by running against sample rows
- Tool shows preview: sample RDF output (human-readable + Turtle)

### Phase 6: PR CREATION ⏸️ (confirmation required)
- User reviews preview
- **User confirms** to create PR
- Tool creates branch, commits RML + description, opens PR
- Tool displays PR URL

### Configuration
Config file (`config.yaml` or similar) contains:
```yaml
github:
  repo: "org/repo-name"
  token: "${GITHUB_TOKEN}"  # or direct value for local dev
sparql:
  endpoint: "https://..."
rml:
  base_uri: "https://ld.stadt-zuerich.ch/statistics/"
azure:
  endpoint: "https://..."
  api_key: "${AZURE_OPENAI_KEY}"
  deployment: "gpt-4"
```

### LangGraph State Machine
```
┌───────────┐
│   START   │
└─────┬─────┘
      ▼
┌───────────┐     user confirms      ┌───────────┐
│   INIT    │ ──────────────────────▶│  ANALYZE  │
└───────────┘                        └─────┬─────┘
                                           ▼
                                    ┌───────────┐
                              ┌────▶│  PROPOSE  │◀────┐
                              │     └─────┬─────┘     │
                              │           │           │
                              │     user confirms     │ user requests changes
                              │           ▼           │
                              │     ┌───────────┐     │
                              │     │  REFINE   │─────┘
                              │     └─────┬─────┘
                              │           │
                              │     user approves
                              │           ▼
                              │     ┌───────────┐
                              │     │ GENERATE  │
                              │     └─────┬─────┘
                              │           │
                              │     validation fails
                              └───────────┘
                                          │
                                    validation ok
                                          ▼
                                    ┌───────────┐     user confirms      ┌───────────┐
                                    │  PREVIEW  │ ──────────────────────▶│ CREATE_PR │
                                    └───────────┘                        └─────┬─────┘
                                                                               ▼
                                                                         ┌───────────┐
                                                                         │    END    │
                                                                         └───────────┘
```

### AI Behavior
- Proactively asks clarifying questions when:
  - Column purpose is ambiguous
  - Multiple valid interpretations exist
  - Data quality issues detected (e.g., mixed types in column)
- Explains reasoning when proposing mappings
- Suggests alternatives when user seems unsure

### Alternative Entry Point: Refinement from PR (V1/Later)

Instead of starting with CSV + DCAT, user can start with an existing PR number:

```
1. INITIALIZATION (PR mode)
   └─ User provides: PR number
   └─ Tool fetches: PR details, existing RML, PR comments

2. COMMENT ANALYSIS
   └─ AI analyzes PR comments as feedback
   └─ AI summarizes requested changes
   └─ User confirms understanding is correct

3. REFINEMENT (same as Phase 4)
   └─ AI proposes changes based on comments
   └─ User can further adjust
   └─ User approves final mapping

4. UPDATE PR
   └─ Tool validates updated RML
   └─ Tool commits changes to existing PR branch
   └─ Tool adds comment summarizing changes made
```

This enables iterative review workflows:
- Reviewer leaves comments on PR
- Author runs tool with PR number
- Tool processes feedback and proposes fixes
- Author approves → PR is updated

## 5. Prompting Strategy

### Output Format
- **Markdown with code blocks** (hybrid approach)
- AI explains reasoning in natural language
- Structured data (mapping proposals, RML) in fenced code blocks (```yaml, ```turtle)
- Easy to parse: extract code blocks with regex, display rest to user
- Works well in CLI and Streamlit

### System Prompt (MVP)
```
You are an RDF mapping expert specializing in creating RML (RDF Mapping Language)
configurations for statistical data cubes.

Your task: Help users transform CSV files into RDF data cubes using:
- cube.link vocabulary for cube structure
- schema.org vocabulary for dimensions (DefinedTerm, DefinedTermSet, isPartOf)

Guidelines:
- Identify dimensions vs measures from column analysis
- Suggest appropriate dimension types (temporal, spatial, categorical)
- Propose hierarchies where applicable
- Ask clarifying questions when column purpose is ambiguous
- Explain your reasoning when making suggestions
- When user overrides a suggestion, accept it and adjust accordingly

Response format:
- Use markdown for explanations
- Put structured data (mapping proposals) in fenced YAML code blocks
- Put RML output in fenced Turtle code blocks
```

### Context Provided to AI
For each mapping request, include:
1. **CSV schema:** column names, detected types, sample values (3-5 rows)
2. **DCAT metadata:** title, description, publisher, keywords, temporal coverage
3. **Base URI:** pattern for generating resource URIs
4. **Conversation history:** previous turns for context

### Example AI Response
```markdown
Based on the CSV structure, I suggest the following mapping:

**Dimensions:**
- `jahr` → Temporal dimension (year)
- `quartier` → Spatial dimension (district)
- `altersgruppe` → Categorical dimension (age group)

**Measures:**
- `anzahl` → Count measure (unit: persons)

I noticed `quartier` contains codes like "AltI", "Werd". Should these map
to an existing spatial hierarchy, or create a new one?

​```yaml
dimensions:
  - column: jahr
    type: temporal
    granularity: year
  - column: quartier
    type: spatial
    hierarchy: district
  - column: altersgruppe
    type: categorical
measures:
  - column: anzahl
    unit: schema:Person
​```
```

### Few-shot Examples
- **MVP:** None - rely on model's training knowledge
- **Later:** Add 1-2 complete examples if output quality needs improvement

### Vocabulary Constraints
- **MVP:** None - trust model knows cube.link and schema.org
- **Later:** Add spec snippets if model makes vocabulary errors

## 6. Decisions Made

- No existing infrastructure - greenfield project
- RMLMapper: subprocess for MVP, Docker exec later
- Chat platform integration: out of scope (Streamlit provides sufficient chat-like UX)
