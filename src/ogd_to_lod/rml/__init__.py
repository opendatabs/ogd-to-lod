"""RML generation module for creating RDF Mapping Language configurations."""

from ogd_to_lod.rml.generator import (
    RMLGenerator,
    RMLGenerationError,
    generate_rml,
)
from ogd_to_lod.rml.prompts import RML_GENERATION_PROMPT

__all__ = [
    "RMLGenerator",
    "RMLGenerationError",
    "generate_rml",
    "RML_GENERATION_PROMPT",
]
