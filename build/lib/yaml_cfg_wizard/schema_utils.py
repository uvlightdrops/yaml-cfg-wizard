"""Schema utilities for merging and generating config skeletons."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml


def merge_schemas(*schema_paths: str | os.PathLike[str]) -> Dict[str, Any]:
    """Merge multiple JSON Schema files deeply.
    
    Later schemas override earlier ones.
    """
    merged: Dict[str, Any] = {}
    
    for schema_path in schema_paths:
        path = Path(schema_path)
        if not path.exists():
            continue
        
        with path.open("r", encoding="utf-8") as f:
            schema = yaml.safe_load(f)
            if schema:
                merged = _deep_merge_schema(merged, schema)
    
    return merged


def _deep_merge_schema(base: Any, override: Any) -> Any:
    """Recursively merge JSON Schema objects."""
    if isinstance(base, dict) and isinstance(override, dict):
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Merge nested objects
                result[key] = _deep_merge_schema(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result
    return deepcopy(override)


def scaffold_skeleton_from_schema(
    schema: Dict[str, Any],
    include_descriptions: bool = False,
) -> Dict[str, Any]:
    """Generate a config skeleton with default values from a JSON Schema.
    
    Args:
        schema: JSON Schema Draft 7 object
        include_descriptions: Include schema descriptions as comments (via leading _ key)
    
    Returns:
        Dictionary skeleton with defaults populated
    """
    result: Dict[str, Any] = {}
    
    if schema.get("type") != "object":
        return result
    
    properties = schema.get("properties", {})
    
    for prop_name, prop_schema in properties.items():
        if isinstance(prop_schema, dict):
            value = _generate_default_value(prop_schema, include_descriptions)
            if value is not None:
                result[prop_name] = value
    
    return result


def _generate_default_value(
    schema: Dict[str, Any],
    include_descriptions: bool = False,
) -> Any:
    """Generate a default value for a schema property."""
    if "default" in schema:
        return schema["default"]
    
    schema_type = schema.get("type")
    
    if schema_type == "object":
        properties = schema.get("properties", {})
        obj: Dict[str, Any] = {}
        for prop_name, prop_schema in properties.items():
            if isinstance(prop_schema, dict):
                value = _generate_default_value(prop_schema, include_descriptions)
                if value is not None:
                    obj[prop_name] = value
        return obj if obj else None
    
    elif schema_type == "array":
        return []
    
    elif schema_type == "string":
        return ""
    
    elif schema_type == "integer":
        return 0
    
    elif schema_type == "number":
        return 0.0
    
    elif schema_type == "boolean":
        return False
    
    return None


def write_skeleton_to_file(
    skeleton: Dict[str, Any],
    output_path: str | os.PathLike[str],
) -> None:
    """Write skeleton to a YAML file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(skeleton, f, sort_keys=False, default_flow_style=False)
