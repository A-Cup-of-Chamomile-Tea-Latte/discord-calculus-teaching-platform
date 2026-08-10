"""Fixture-only proposed configuration validation and documentation."""

from tools.config_proposal.core import (
    ConfigBundle,
    ValidationIssue,
    generate_documents,
    load_bundle,
    validate_bundle,
)

__all__ = [
    "ConfigBundle",
    "ValidationIssue",
    "generate_documents",
    "load_bundle",
    "validate_bundle",
]
