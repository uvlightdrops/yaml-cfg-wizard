from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml

from .core import ConfigResolver, deep_merge, load_yaml_file
from .scaffold import available_templates, scaffold_template
from .schema_utils import merge_schemas, scaffold_skeleton_from_schema
from .config_cli import show_config, list_config, validate_config, show_config_paths, generate_skeleton
from .profile_cli import (
    list_profiles as _list_profiles,
    show_profile as _show_profile,
    set_active_profile as _set_active_profile,
    create_profile as _create_profile,
    read_active_profile,
)

app = typer.Typer(help="YAML config merge and validation wizard")


# ---------------------------------------------------------------------------
# config: inspection, validation, skeleton generation, and layer resolution
# ---------------------------------------------------------------------------
config_app = typer.Typer(help="Config inspection, validation, and resolution")


def _auto_discover_schemas() -> list[str]:
    """Best-effort discovery of schema files describing the *full* (inherited)
    config tree: ki-core's generic base schema (if ki-core happens to be
    installed) plus any app-specific ``schema/*.schema.yaml`` files under the
    current directory.

    This lets ``config show``/``config list``/``config resolve`` display the
    complete, inherited config shape (not just the keys physically present in
    a single YAML file) without hard-coupling yaml-cfg-wizard to ki-core: the
    ki-core import is optional and silently skipped if unavailable.
    """
    schemas: list[str] = []
    try:
        from ki_core.schema_manager import get_schema_path

        base = get_schema_path()
        if Path(base).exists():
            schemas.append(str(base))
    except Exception:
        pass

    schema_dir = Path.cwd() / "schema"
    if schema_dir.is_dir():
        for candidate in sorted(schema_dir.glob("*.schema.yaml")):
            resolved = str(candidate)
            if resolved not in schemas:
                schemas.append(resolved)
    return schemas


def _apply_schema_defaults(config_dict: dict, schemas: Optional[list[str]]) -> dict:
    """Fill in keys declared by ``schemas`` but missing from ``config_dict``
    with their schema defaults, so inherited/base sections are visible even
    when a config file only sets its own app-specific values."""
    resolved_schemas = schemas if schemas else _auto_discover_schemas()
    if not resolved_schemas:
        return config_dict
    schema_defaults = scaffold_skeleton_from_schema(merge_schemas(*resolved_schemas))
    return deep_merge(schema_defaults, config_dict)


def _resolve_for_cli(
    defaults_dir: Optional[str],
    profiles_dir: Optional[str],
    stages_dir: Optional[str],
    runtime_file: Optional[str],
    defaults: list[str],
    profile: list[str],
    stage: list[str],
    runtime: list[str],
    env_prefix: str,
) -> ConfigResolver:
    # If no explicit profile was given but an active profile is set for this
    # profiles_dir, use it automatically (see `yaml-cfg profile set`).
    if profiles_dir and not profile:
        active = read_active_profile(profiles_dir)
        if active:
            candidate = Path(profiles_dir) / f"{active}.yaml"
            if candidate.exists():
                profile = [str(candidate)]

    return ConfigResolver(
        defaults=defaults,
        profiles=profile,
        stage=stage,
        runtime=runtime,
        defaults_dir=defaults_dir,
        profiles_dir=None if profile else profiles_dir,
        stages_dir=stages_dir,
        runtime_file=runtime_file,
        env_prefix=env_prefix,
    )


@config_app.command("resolve")
def resolve_config(
    defaults_dir: Optional[str] = typer.Option(None, "--defaults-dir", help="Directory with default YAML files"),
    profiles_dir: Optional[str] = typer.Option(None, "--profiles-dir", help="Directory with profile YAML files"),
    stages_dir: Optional[str] = typer.Option(None, "--stages-dir", help="Directory with stage YAML files"),
    runtime_file: Optional[str] = typer.Option(None, "--runtime-file", help="Runtime override YAML file"),
    defaults: list[str] = typer.Option([], "--defaults", help="Explicit default YAML files"),
    profile: list[str] = typer.Option([], "--profile", help="Explicit profile YAML files"),
    stage: list[str] = typer.Option([], "--stage", help="Explicit stage YAML files"),
    runtime: list[str] = typer.Option([], "--runtime", help="Explicit runtime YAML files"),
    env_prefix: str = typer.Option("APP_", "--env-prefix", help="Environment variable prefix"),
    output: Optional[str] = typer.Option(None, "--output", help="Write resolved config to file"),
    schema: Optional[list[str]] = typer.Option(
        None,
        "--schema",
        help="Schema file(s) whose defaults fill in keys missing from the resolved layers "
        "(auto-discovered from ki-core's base schema + ./schema/*.schema.yaml if omitted)",
    ),
    no_schema: bool = typer.Option(False, "--no-schema", help="Disable schema-defaults auto-discovery"),
) -> None:
    """Merge and resolve all config layers (defaults -> profile -> stage -> runtime -> env)."""
    resolver = _resolve_for_cli(
        defaults_dir,
        profiles_dir,
        stages_dir,
        runtime_file,
        defaults,
        profile,
        stage,
        runtime,
        env_prefix,
    )
    result = resolver.resolve()
    if not no_schema:
        result = _apply_schema_defaults(result, schema)
    if output:
        resolver.resolve_to_file(output)
    typer.echo(yaml.safe_dump(result, sort_keys=False, default_flow_style=False))


@config_app.command("skeleton")
def skeleton(
    base_schema: str = typer.Argument(..., help="Path to base schema file"),
    output: str = typer.Option("ki.yaml", "--output", "-o", help="Output config file path"),
    additional: Optional[list[str]] = typer.Option(None, "--schema", help="Additional schema files to merge"),
) -> None:
    """Generate config skeleton from schema."""
    generate_skeleton(base_schema, output, additional)


@config_app.command("show")
def show(
    key: Optional[str] = typer.Argument(None, help="Config key to show (omit to show all)"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
    schema: Optional[list[str]] = typer.Option(
        None,
        "--schema",
        help="Schema file(s) whose defaults fill in inherited/base keys missing from --config "
        "(auto-discovered from ki-core's base schema + ./schema/*.schema.yaml if omitted)",
    ),
    no_schema: bool = typer.Option(False, "--no-schema", help="Disable schema-defaults auto-discovery"),
) -> None:
    """Show config value by key."""
    try:
        config_dict = load_yaml_file(config_file)
        if not no_schema:
            config_dict = _apply_schema_defaults(config_dict, schema)
        show_config(config_dict, key)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config_file}", err=True)
        raise typer.Exit(code=1)


@config_app.command("list")
def list_keys(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
    schema: Optional[list[str]] = typer.Option(
        None,
        "--schema",
        help="Schema file(s) whose defaults fill in inherited/base keys missing from --config "
        "(auto-discovered from ki-core's base schema + ./schema/*.schema.yaml if omitted)",
    ),
    no_schema: bool = typer.Option(False, "--no-schema", help="Disable schema-defaults auto-discovery"),
) -> None:
    """List all config keys in hierarchical view."""
    try:
        config_dict = load_yaml_file(config_file)
        if not no_schema:
            config_dict = _apply_schema_defaults(config_dict, schema)
        list_config(config_dict)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config_file}", err=True)
        raise typer.Exit(code=1)


@config_app.command("verify")
def verify(
    config_file: str = typer.Argument(..., help="Path to config file"),
    schema_file: str = typer.Argument(..., help="Path to schema file"),
) -> None:
    """Validate config against schema."""
    try:
        config_dict = load_yaml_file(config_file)
        schema_dict = load_yaml_file(schema_file)
        validate_config(config_dict, schema_dict)
    except FileNotFoundError as e:
        typer.echo(f"❌ File not found: {e}", err=True)
        raise typer.Exit(code=1)


@config_app.command("paths")
def paths(
    search_dir: Optional[str] = typer.Option(None, "--search-dir", "-d", help="Base directory for search paths"),
) -> None:
    """Show config file search paths."""
    search_paths = None
    if search_dir:
        search_paths = [
            Path(search_dir) / "ki.yaml",
            Path(search_dir) / ".ki" / "ki.yaml",
            Path(search_dir) / ".ki.yaml",
        ]
    show_config_paths(search_paths)


app.add_typer(config_app, name="config")


# ---------------------------------------------------------------------------
# profile: list, inspect, activate, and create named config profiles
# ---------------------------------------------------------------------------
profile_app = typer.Typer(help="Profile listing and management")


@profile_app.command("list")
def profile_list(
    profiles_dir: str = typer.Argument(..., help="Directory containing profile YAML files"),
) -> None:
    """List available profiles, marking the currently active one."""
    _list_profiles(profiles_dir)


@profile_app.command("show")
def profile_show(
    name: str = typer.Argument(..., help="Profile name (without extension)"),
    profiles_dir: str = typer.Option(..., "--profiles-dir", "-d", help="Directory containing profile YAML files"),
) -> None:
    """Show the contents of a single profile."""
    _show_profile(profiles_dir, name)


@profile_app.command("set")
def profile_set(
    name: str = typer.Argument(..., help="Profile name (without extension) to activate"),
    profiles_dir: str = typer.Option(..., "--profiles-dir", "-d", help="Directory containing profile YAML files"),
) -> None:
    """Mark a profile as active; `config resolve` will use it automatically."""
    _set_active_profile(profiles_dir, name)


@profile_app.command("create")
def profile_create(
    name: str = typer.Argument(..., help="Name of the new profile (without extension)"),
    profiles_dir: str = typer.Option(..., "--profiles-dir", "-d", help="Directory containing profile YAML files"),
    from_template: Optional[str] = typer.Option(
        None, "--from", help="Copy contents from an existing profile as a starting point"
    ),
) -> None:
    """Create a new profile file, optionally copied from an existing profile."""
    _create_profile(profiles_dir, name, from_template)


app.add_typer(profile_app, name="profile")


# ---------------------------------------------------------------------------
# template: scaffold entire config directory trees from bundled templates
# ---------------------------------------------------------------------------
template_app = typer.Typer(help="Config directory template scaffolding")


@template_app.command("list")
def template_list() -> None:
    """List available scaffold templates."""
    templates = available_templates()
    if not templates:
        typer.echo("No templates available.")
        return
    for template in templates:
        typer.echo(template)


@template_app.command("scaffold")
def template_scaffold(
    template: str = typer.Argument(..., help="Template name to scaffold"),
    output: str = typer.Argument(..., help="Directory where the config skeleton should be written"),
) -> None:
    """Scaffold a full config directory tree (defaults/profiles/stages/runtime) from a template."""
    if template not in available_templates():
        typer.echo(f"Unknown template '{template}'. Available: {', '.join(available_templates()) or 'none'}", err=True)
        raise typer.Exit(code=1)
    try:
        scaffold_template(template, output)
        typer.echo(f"Scaffolded template '{template}' into {output}")
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


app.add_typer(template_app, name="template")


# ---------------------------------------------------------------------------
# env: environment variable inspection
# ---------------------------------------------------------------------------
env_app = typer.Typer(help="Environment variable inspection")


@env_app.command("show")
def env_show(prefix: str = typer.Option("APP_", "--prefix")) -> None:
    """Show environment variables matching a prefix."""
    import os

    matches = []
    for key, value in sorted(os.environ.items()):
        if key.startswith(prefix):
            matches.append(f"{key}={value}")

    if not matches:
        typer.echo("No matching environment variables found.")
        return

    for item in matches:
        typer.echo(item)


app.add_typer(env_app, name="env")


if __name__ == "__main__":
    app()
