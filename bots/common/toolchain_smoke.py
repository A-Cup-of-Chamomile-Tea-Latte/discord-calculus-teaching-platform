"""Minimal typed module used to verify the Python toolchain."""


def runtime_mode() -> str:
    """Return the only safe mode available during foundation work."""
    return "fixture-only"
