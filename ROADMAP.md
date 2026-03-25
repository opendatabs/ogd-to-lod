# Sprint Roadmap — Q2 2026

> Planned sprint following MVP completion. Priorities ordered by business value and dependency.

## Priority 1: Static Files & Prompt Hardening
**Goal:** Generate companion RDF files alongside YARRRML and harden AI output quality.

- **#41 — Static RDF triples** (cube:Cube, ObservationSet, ObservationConstraint, property definitions)
  - Generate `<mapping>-metadata.ttl` with cube metadata from context
  - Include per-property DimensionConstraint / MeasureConstraint (SHACL-based)
  - Commit to PR alongside YARRRML
- **#44 — Prompt robustness**
  - Systematic testing with diverse CSV/DCAT inputs (edge cases, multilingual, sparse metadata)
  - Guard against prompt injection via CSV content or metadata
  - Improve few-shot examples for better cube.link conformance
- **#45 — Output validation tightening**
  - Stricter YARRRML schema validation before RMLMapper execution
  - Validate static triples against cube.link constraints
  - Better error messages / AI self-repair on validation failure

## Priority 2: SHACL & Standalone Blueprint
**Goal:** Generate SHACL validation shapes. Provide a standalone usage blueprint.

- **#43 — SHACL shape generation**
  - Generate SHACL shapes for observation validation
  - Derive constraints from CSV schema + AI proposal (value types, cardinality, patterns)
  - Output as `<mapping>-shapes.ttl`
- **#47 — Standalone blueprint**
  - Minimal example: local CSV + metadata file → YARRRML + static triples
  - Docker-based, no external dependencies beyond Azure OpenAI
  - README with step-by-step usage

## Priority 3: Huewise Blueprint
**Goal:** Provide ready-to-use integration with the Huewise portal.

- **#46 — Huewise Portal blueprint**
  - Download CSV + DCAT metadata via Huewise API
  - Feed into ogd-to-lod library
  - Upload generated RML skeleton back via API
  - Example script / CLI command with configuration

## Priority 4: Full Automation (Claude Code Integration)
**Goal:** Enable fully autonomous mapping generation via Claude Code skills.

- **#48 — Package as library/module**
  - Refactor CLI entry points into a clean Python API
  - Publish as installable package (pip / internal registry)
  - Stable public interface for programmatic use
- **#49 — Claude Code skill integration**
  - Create Claude Code skill definition for ogd-to-lod
  - AI autonomously decides mapping strategy, runs tool, reviews output
  - End-to-end: CSV input → validated YARRRML + static triples → PR, no human in the loop

## Open / Existing Issues (carried over)
- **#37** — SPARQL-based reuse of existing cube.link properties and DefinedTerms
- **#39** — Flexible dataset context input (in progress)
- **#35** — Use field-based metadata from Explore API
- **#31** — Path traversal vulnerability (security)
- **#23** — LangSmith integration for tracing

---

## Sprint Scope Note

Priorities 1–2 are the core sprint. Priority 3 (Huewise blueprint) is achievable if velocity allows. Priority 4 (full automation) is a stretch goal — recommend deferring to a follow-up sprint.

- **Sprint A:** Static files (#41) + Prompt hardening (#44, #45) + SHACL (#43) + Standalone blueprint (#47)
- **Sprint B:** Huewise blueprint (#46) + Library packaging (#48) + Claude Code integration (#49)
