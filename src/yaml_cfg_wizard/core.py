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


def merge_with_replacement(base: Any, override: Any) -> Any:
    """Merge sections, retaining replacement metadata for subsequent merges."""
    if isinstance(override, dict):
        marker = override.get("__replace__", False)
        if not isinstance(marker, bool):
            raise ValueError("__replace__ must be a boolean")
        result = deepcopy(base) if isinstance(base, dict) and not marker else {}
        if marker:
            result["__replace__"] = True
        for key, value in override.items():
            if key != "__replace__":
                result[key] = merge_with_replacement(result.get(key), value)
        return result
    if isinstance(override, list):
        return [merge_with_replacement(None, item) for item in override]
    return deepcopy(override)


def strip_replace_markers(config: Any) -> Any:
    """Remove replacement metadata after the final merge."""
    if isinstance(config, dict):
        return {
            key: strip_replace_markers(value)
            for key, value in config.items() if key != "__replace__"
        }
    if isinstance(config, list):
        return [strip_replace_markers(item) for item in config]
    return config


def load_yaml_file(path: str | os.PathLike[str]) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}

    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML root must be a mapping: {file_path}")
        return data


def load_yaml_files(
    paths: Sequence[str | os.PathLike[str]], *, replace_sections: bool = False,
) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    merge = merge_with_replacement if replace_sections else deep_merge
    for path in paths:
        loaded = load_yaml_file(path)
        merged = merge(merged, loaded)
    return merged


def load_directory_yaml(
    directory: str | os.PathLike[str], *, replace_sections: bool = False,
) -> Dict[str, Any]:
    directory_path = Path(directory)
    if not directory_path.exists():
        return {}

    files = sorted(directory_path.glob("*.yaml")) + sorted(directory_path.glob("*.yml"))
    return load_yaml_files(files, replace_sections=replace_sections)


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
        replace_sections: bool = False,
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
        self.replace_sections = replace_sections

    def resolve(self, *, preserve_replace_markers: bool = False) -> Dict[str, Any]:
        """Resolve and validate; optionally retain metadata for further merges."""
        merged: Dict[str, Any] = {}
        merge = merge_with_replacement if self.replace_sections else deep_merge

        def files(paths: Sequence[str | os.PathLike[str]]) -> Dict[str, Any]:
            return load_yaml_files(paths, replace_sections=self.replace_sections)

        def directory(path: str) -> Dict[str, Any]:
            return load_directory_yaml(path, replace_sections=self.replace_sections)

        if self.defaults_dir:
            merged = merge(merged, directory(self.defaults_dir))
        merged = merge(merged, files(self.defaults))

        if self.profiles_dir:
            merged = merge(merged, directory(self.profiles_dir))
        merged = merge(merged, files(self.profiles))

        if self.stages_dir:
            merged = merge(merged, directory(self.stages_dir))
        merged = merge(merged, files(self.stage))

        for layer in self._runtime_layers():
            merged = merge(merged, layer)

        env_overrides = env_to_dict(self.env_prefix, self.env)
        merged = merge(merged, env_overrides)
        effective = strip_replace_markers(merged) if self.replace_sections else merged
        self.validate(effective)
        return merged if preserve_replace_markers else effective

    def _runtime_layers(self) -> Sequence[Dict[str, Any]]:
        """Return runtime layers without changing their merge boundaries."""
        layers = [load_yaml_file(self.runtime_file)] if self.runtime_file else []
        return [
            *layers, load_yaml_files(self.runtime, replace_sections=self.replace_sections),
        ]

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
