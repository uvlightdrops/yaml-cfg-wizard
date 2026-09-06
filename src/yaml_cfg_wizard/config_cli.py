"""CLI utilities for config inspection and management."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import typer
import yaml
from .core import ConfigResolver
from .schema_utils import merge_schemas

def show_config(
    config_dict: Dict[str, Any],
    key: Optional[str] = None,
) -> None:
    """Show config value by key or all config."""
    if not key:
        # Show all config
        typer.echo(yaml.dump(config_dict, default_flow_style=False, sort_keys=True))
        return
    
    # Look up key directly
    if key in config_dict:
        value = config_dict[key]
        if value is None or value == "":
            typer.echo(f"⚠️  Key '{key}' is not set")
        else:
            typer.echo(f"{key}: {value}")
    else:
        typer.echo(f"❌ Key '{key}' not found", err=True)
        raise typer.Exit(code=1)


def list_config(config_dict: Dict[str, Any]) -> None:
    """List all config keys in hierarchical tree view."""
    
    def print_tree(d: dict, prefix: str = "") -> None:
        items = sorted(d.items())
        for i, (k, v) in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            typer.echo(f"{prefix}{current_prefix}{k}")
            
            if isinstance(v, dict):
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(v, next_prefix)
    
    typer.echo("📋 Config keys:")
    print_tree(config_dict)


def validate_config(
    config_dict: Dict[str, Any],
    schema: Dict[str, Any],
) -> None:
    """Validate config against schema, using the shared Draft7 validator for consistent error formatting."""
    import tempfile

    from .core import validate_schema

    # validate_schema expects a schema file path; write schema to a temp file to reuse
    # the single, consistent validation implementation instead of duplicating logic here.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
        yaml.safe_dump(schema, handle)
        schema_path = handle.name

    try:
        validate_schema(config_dict, schema_path)
        typer.echo("✅ Config is valid")
    except ValueError as exc:
        for line in str(exc).splitlines():
            typer.echo(f"❌ {line}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        Path(schema_path).unlink(missing_ok=True)


def generate_skeleton(
    base_schema_path: Path | str,
    output_path: Path | str,
    additional_schemas: Optional[list[Path | str]] = None,
) -> None:
    """Generate config skeleton from schema."""
    from .schema_utils import scaffold_skeleton_from_schema, merge_schemas, write_skeleton_to_file
    
    output = Path(output_path)
    try:
        # Load and merge schemas
        schema_paths = [base_schema_path]
        if additional_schemas:
            schema_paths.extend(additional_schemas)
        
        merged_schema = merge_schemas(*schema_paths)
        
        # Generate skeleton from merged schema
        skeleton = scaffold_skeleton_from_schema(merged_schema)
        
        # Write to file
        write_skeleton_to_file(skeleton, output)
        typer.echo(f"✅ Config skeleton generated: {output}")
        typer.echo(f"📝 Edit {output} and set your values")
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1) from e
