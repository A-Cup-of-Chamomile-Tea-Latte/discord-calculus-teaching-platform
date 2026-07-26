"""Local JSON contract registry and validation helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from bots.common.errors import ContractValidationError

SCHEMA_NAME_PATTERN = re.compile(r"^[a-z0-9-]+\.schema\.json$")


class ContractRegistry:
    def __init__(self, schema_directory: Path) -> None:
        self._schema_directory = schema_directory.resolve()
        if not self._schema_directory.is_dir():
            raise ContractValidationError("Contract schema directory does not exist.")
        self._schemas: dict[str, dict[str, Any]] = {}
        for path in sorted(self._schema_directory.glob("*.schema.json")):
            value = self._load_json(path)
            if not isinstance(value, dict):
                raise ContractValidationError(f"Schema {path.name} must be a JSON object.")
            Draft202012Validator.check_schema(value)
            self._schemas[path.name] = value
        if not self._schemas:
            raise ContractValidationError("No contract schemas were found.")
        self._registry = Registry().with_resources(
            (str(schema["$id"]), Resource.from_contents(schema))
            for schema in self._schemas.values()
        )

    @classmethod
    def project_default(cls) -> ContractRegistry:
        root = Path(__file__).resolve().parents[2]
        return cls(root / "contracts" / "schemas")

    @property
    def schema_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))

    def validate(self, schema_name: str, instance: object) -> None:
        if not SCHEMA_NAME_PATTERN.fullmatch(schema_name):
            raise ContractValidationError("Contract schema name is invalid.")
        schema = self._schemas.get(schema_name)
        if schema is None:
            raise ContractValidationError(f"Unknown contract schema: {schema_name}.")
        validator = Draft202012Validator(
            schema,
            registry=self._registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            first = errors[0]
            location = ".".join(str(item) for item in first.absolute_path) or "<root>"
            raise ContractValidationError(
                f"Contract {schema_name} rejected the value at {location} (rule {first.validator})."
            )

    def load_and_validate(self, schema_name: str, path: Path) -> object:
        value = self._load_json(path)
        self.validate(schema_name, value)
        return value

    def load_records(self, schema_name: str, path: Path) -> tuple[dict[str, Any], ...]:
        value = self._load_json(path)
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ContractValidationError("A record fixture must be a JSON array of objects.")
        records = tuple(value)
        for record in records:
            self.validate(schema_name, record)
        return records

    @staticmethod
    def _load_json(path: Path) -> object:
        if path.suffix.lower() != ".json" or not path.is_file():
            raise ContractValidationError("Contract input must be an existing JSON file.")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ContractValidationError("Contract input is not readable valid JSON.") from error
