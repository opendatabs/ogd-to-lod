# Sprint Roadmap — Q2 2026

> Planned sprints following MVP completion. Priorities ordered by business value and dependency.

---

## Sprint KW 13–15

### Priority 1: Static Files, Prompt Hardening & SPARQL Reuse
**Goal:** Generate companion RDF files alongside YARRRML, harden AI output quality, and land SPARQL lookup.

- **#37 — SPARQL-based reuse of cube.link properties and DefinedTerms** (overspill — implemented, needs test alignment and merge)
  - Align with current workflow (flexible context input, updated graph flow)
  - Ensure tests pass against main branch
  - Merge to main
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

### Priority 2: SHACL & Standalone Blueprint
**Goal:** Generate SHACL validation shapes. Provide a standalone usage blueprint.

- **#43 — SHACL shape generation**
  - Generate SHACL shapes for observation validation
  - Derive constraints from CSV schema + AI proposal (value types, cardinality, patterns)
  - Output as `<mapping>-shapes.ttl`
- **#47 — Standalone blueprint**
  - Minimal example: local CSV + metadata file → YARRRML + static triples
  - Docker-based, no external dependencies beyond Azure OpenAI
  - README with step-by-step usage

---

## Sprint KW 16–18

### Priority 3: Huewise Blueprint
**Goal:** Provide ready-to-use integration with the Huewise portal.

- **#46 — Huewise Portal blueprint**
  - Download CSV + DCAT metadata via Huewise API
  - Feed into ogd-to-lod library
  - Upload generated RML skeleton back via API
  - Example script / CLI command with configuration

### Priority 4: Full Automation (Claude Code Integration)
**Goal:** Enable fully autonomous mapping generation via Claude Code skills.

- **#48 — Package as library/module**
  - Refactor CLI entry points into a clean Python API
  - Publish as installable package (pip / internal registry)
  - Stable public interface for programmatic use
- **#49 — Claude Code skill integration**
  - Create Claude Code skill definition for ogd-to-lod
  - AI autonomously decides mapping strategy, runs tool, reviews output
  - End-to-end: CSV input → validated YARRRML + static triples → PR, no human in the loop

---

## Open / Existing Issues (not yet scheduled)
- **#23** — LangSmith integration for tracing
