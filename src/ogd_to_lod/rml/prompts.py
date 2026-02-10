"""AI prompts for RML generation."""

RML_GENERATION_PROMPT = """\
Generate a valid RML (RDF Mapping Language) mapping in Turtle format \
based on the approved mapping proposal and CSV schema.

## Prefix Definitions

Always use the following standard prefixes:
- @prefix rr: <http://www.w3.org/ns/r2rml#> .
- @prefix rml: <http://semweb.mmlab.be/ns/rml#> .
- @prefix ql: <http://semweb.mmlab.be/ns/ql#> .
- @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
- @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
- @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
- @prefix schema: <http://schema.org/> .
- @prefix cube: <https://cube.link/> .
- @prefix ex: <{base_uri}> .

Define additional sub-prefixes for each sub-path of the base URI that you need. \
For example, if the mapping uses dimensions, measures, and observations:
- @prefix ex-dim: <{base_uri}dimension/> .
- @prefix ex-measure: <{base_uri}measure/> .
- @prefix ex-obs: <{base_uri}observation/> .

## CRITICAL: Turtle Syntax Rules

### No `/` in prefixed name local parts
The `/` character is NOT allowed in the local part of a prefixed name. \
This is a hard constraint of the W3C Turtle grammar (PN_LOCAL production).

WRONG — produces invalid Turtle:
  ex:dimension/time
  ex:measure/O3
  ex:observation/{{year}}

CORRECT — use sub-prefixes instead:
  ex-dim:time
  ex-measure:O3
  ex-obs:{{year}}

You MUST define a sub-prefix for every sub-path and use it consistently. \
Never write a prefixed name that contains `/` in the local part.

### No relative IRIs (e.g. <#Name>)
Do NOT use relative IRIs such as `<#LogicalSource>` or `<#TriplesMap>`. \
RMLMapper uses RDF4J which rejects relative IRIs without a @base directive. \
Instead, use prefixed names like `ex:LogicalSource` or `ex:TriplesMap`.

## CSV Source Configuration
The CSV source file path is: {csv_path}

## Approved Mapping Proposal
{mapping_proposal}

## CSV Schema
{csv_schema}

## RML Structure Requirements

1. **Logical Source**: Define the CSV source with:
   - rml:source for the CSV file path
   - rml:referenceFormulation ql:CSV

2. **TriplesMap**: Create a main TriplesMap that:
   - Uses a subject template combining dimension values for unique observation URIs
   - Example: https://ld.stadt-zuerich.ch/statistics/observation/{{year}}/{{region}}

3. **Dimension Mappings**: For each dimension in the proposal:
   - Use cube:dimension predicate
   - For temporal dimensions: map to xsd:gYear, xsd:date, or xsd:dateTime based on granularity
   - For spatial dimensions: create DefinedTerm references
   - For categorical dimensions: create DefinedTerm references with schema:inDefinedTermSet

4. **Measure Mappings**: For each measure in the proposal:
   - Use cube:measure predicate
   - Apply appropriate XSD datatype (xsd:decimal for floats, xsd:integer for integers)
   - Include unit annotations where specified

5. **Observation Type**: Each observation should be typed as:
   - rr:class cube:Observation

6. **DefinedTermSet Generation**: For categorical and spatial dimensions:
   - Generate schema:DefinedTermSet resources
   - Link dimension values using schema:DefinedTerm and schema:inDefinedTermSet

## Output Format
Provide ONLY the RML Turtle code in a fenced code block with language 'turtle'.
The RML must be syntactically valid Turtle.
Do not include explanations outside the code block.

```turtle
# Your RML mapping here
```
"""

RML_CORRECTION_PROMPT = """\
The RML Turtle you generated has a syntax error. Please fix it.

## Error
{error_message}

## Instructions
- Fix ONLY the issue described above.
- Return the complete corrected RML in a fenced ```turtle``` code block.
- Do NOT change anything else about the mapping.
"""

RML_VALIDATION_PROMPT = """\
Validate the following RML Turtle mapping for syntactic correctness and completeness.

Check for:
1. All required prefixes are defined
2. Turtle syntax is valid
3. All TriplesMaps have:
   - A logical source
   - A subject map
   - At least one predicate-object map
4. All predicate-object maps have valid predicates and object maps
5. Datatype declarations are appropriate for the data

RML to validate:
```turtle
{rml_content}
```

If valid, respond with: VALID
If invalid, respond with: INVALID: <reason>
"""
