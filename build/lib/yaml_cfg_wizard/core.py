from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml
from jsonschema import Draft7Validator


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        result = deepcopy(base)
        for key, value in override.items():
            if key in result:
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result
    return deepcopy(override)


def load_yaml_file(path: str | os.PathLike[str]) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}

    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML root must be a mapping: {file_path}")
        return data


def load_yaml_files(paths: Sequence[str | os.PathLike[str]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for path in paths:
        loaded = load_yaml_file(path)
        merged = deep_merge(merged, loaded)
    return merged


def load_directory_yaml(directory: str | os.PathLike[str]) -> Dict[str, Any]:
    directory_path = Path(directory)
    if not directory_path.exists():
        return {}

    merged: Dict[str, Any] = {}
    files = sorted(directory_path.glob("*.yaml")) + sorted(directory_path.glob("*.yml"))
    for file_path in files:
        merged = deep_merge(merged, load_yaml_file(file_path))
    return merged


def validate_schema(data: Dict[str, Any], schema_file: str | os.PathLike[str]) -> None:
    schema_path = Path(schema_file)
    schema_data = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema_data, dict):
        raise ValueError(f"Schema root must be a mapping: {schema_path}")
    validator = Draft7Validator(schema_data)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        ]
        raise ValueError("Schema validation failed:\n" + "\n".join(messages))


def env_to_dict(prefix: str, env: Optional[dict[str, str]] = None) -> Dict[str, Any]:
    source = env or os.environ
    result: Dict[str, Any] = {}
    prefix = prefix.rstrip("_") + "_"

    for key, value in source.items():
        if not key.startswith(prefix):
            continue
        relative = key[len(prefix):]
        if not relative:
            continue
        parts = relative.lower().split("__")
        target = result
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = _coerce_scalar(value)
    return result


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


class ConfigResolver:
    def __init__(
        self,
        defaults: Sequence[str | os.PathLike[str]] | None = None,
        profiles: Sequence[str | os.PathLike[str]] | None = None,
        stage: Sequence[str | os.PathLike[str]] | None = None,
        runtime: Sequence[str | os.PathLike[str]] | None = None,
        defaults_dir: str | os.PathLike[str] | None = None,
        profiles_dir: str | os.PathLike[str] | None = None,
        stages_dir: str | os.PathLike[str] | None = None,
        runtime_file: str | os.PathLike[str] | None = None,
        schema_file: str | os.PathLike[str] | None = None,
        env_prefix: str = "APP_",
        env: Optional[dict[str, str]] = None,
    ) -> None:
        self.defaults = list(defaults or [])
        self.profiles = list(profiles or [])
        self.stage = list(stage or [])
        self.runtime = list(runtime or [])
        self.defaults_dir = str(defaults_dir) if defaults_dir else None
        self.profiles_dir = str(profiles_dir) if profiles_dir else None
        self.stages_dir = str(stages_dir) if stages_dir else None
        self.runtime_file = str(runtime_file) if runtime_file else None
        self.schema_file = str(schema_file) if schema_file else None
        self.env_prefix = env_prefix
        self.env = env

    def resolve(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}

        if self.defaults_dir:
            merged = deep_merge(merged, load_directory_yaml(self.defaults_dir))
        merged = deep_merge(merged, load_yaml_files(self.defaults))

        if self.profiles_dir:
            merged = deep_merge(merged, load_directory_yaml(self.profiles_dir))
        merged = deep_merge(merged, load_yaml_files(self.profiles))

        if self.stages_dir:
            merged = deep_merge(merged, load_directory_yaml(self.stages_dir))
        merged = deep_merge(merged, load_yaml_files(self.stage))

        if self.runtime_file:
            merged = deep_merge(merged, load_yaml_file(self.runtime_file))
        merged = deep_merge(merged, load_yaml_files(self.runtime))

        env_overrides = env_to_dict(self.env_prefix, self.env)
        merged = deep_merge(merged, env_overrides)
        self.validate(merged)
        return merged

    def validate(self, data: Optional[Dict[str, Any]] = None) -> None:
        if not self.schema_file:
            return

        target = data if data is not None else self.resolve()
        validate_schema(target, self.schema_file)

    def resolve_to_file(self, target_path: str | os.PathLike[str]) -> None:
        resolved = self.resolve()
        output_path = Path(target_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(resolved, handle, sort_keys=False)
