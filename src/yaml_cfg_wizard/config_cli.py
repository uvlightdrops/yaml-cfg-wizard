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
    """Validate config against schema."""
    import jsonschema
    
    try:
        jsonschema.validate(config_dict, schema)
        typer.echo("✅ Config is valid")
    except jsonschema.ValidationError as e:
        typer.echo(f"❌ Validation error: {e.message}", err=True)
        if e.path:
            typer.echo(f"   Path: {' → '.join(str(p) for p in e.path)}", err=True)
        raise typer.Exit(code=1) from e


def show_config_paths(search_paths: Optional[list[Path]] = None) -> None:
    """Show config file search paths and existence status."""
    if search_paths is None:
        search_paths = [
            Path.cwd() / "ki.yaml",
            Path.home() / ".ki" / "ki.yaml",
            Path.home() / ".ki.yaml",
            Path("/etc/ki/ki.yaml"),
        ]
    
    typer.echo("📁 Config file search paths:")
    for p in search_paths:
        status = "✅ exists " if p.exists() else "  missing"
        typer.echo(f"  {status}: {p}")
    
    # Show env var override
    import os
    env_override = os.getenv("KI_CONFIG_PATH")
    if env_override:
        typer.echo(f"\n📌 Environment override (KI_CONFIG_PATH):")
        typer.echo(f"  {env_override}")


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
