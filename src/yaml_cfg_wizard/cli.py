from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml
from .core import ConfigResolver, load_yaml_file, validate_schema
from .scaffold import available_templates, scaffold_template
from .config_cli import show_config, list_config, validate_config, show_config_paths, generate_skeleton
from . import prompts_cli

app = typer.Typer(help="YAML config merge and validation wizard")


@app.command("scaffold")
def scaffold(
    template: str = typer.Argument(..., help="Template name to scaffold"),
    output: str = typer.Argument(..., help="Directory where the config skeleton should be written"),
) -> None:
    if template not in available_templates():
        typer.echo(f"Unknown template '{template}'. Available: {', '.join(available_templates()) or 'none'}", err=True)
        raise typer.Exit(code=1)
    try:
        scaffold_template(template, output)
        typer.echo(f"Scaffolded template '{template}' into {output}")
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("list-templates")
def list_templates() -> None:
    templates = available_templates()
    if not templates:
        typer.echo("No templates available.")
        return
    for template in templates:
        typer.echo(template)


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
):
    return ConfigResolver(
        defaults=defaults,
        profiles=profile,
        stage=stage,
        runtime=runtime,
        defaults_dir=defaults_dir,
        profiles_dir=profiles_dir,
        stages_dir=stages_dir,
        runtime_file=runtime_file,
        env_prefix=env_prefix,
    )


@app.command("resolve")
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
) -> None:
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
    if output:
        resolver.resolve_to_file(output)
    typer.echo(yaml.safe_dump(result, sort_keys=False, default_flow_style=False))


@app.command("validate")
def validate_config(
    config: str = typer.Argument(..., help="Path to YAML config file"),
    schema: str = typer.Argument(..., help="Path to schema file in YAML or JSON format"),
) -> None:
    data = load_yaml_file(config)
    try:
        validate_schema(data, schema)
    except ValueError as exc:
        for line in str(exc).splitlines()[1:]:
            typer.echo(f"- {line}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Configuration is valid.")


@app.command("list-profiles")
def list_profiles(
    profiles_dir: str = typer.Argument(..., help="Directory containing profile YAML files"),
) -> None:
    files = sorted(Path(profiles_dir).glob("*.yaml")) + sorted(Path(profiles_dir).glob("*.yml"))
    if not files:
        typer.echo("No profile files found.")
        return
    for file in files:
        typer.echo(file.name)


@app.command("env-show")
def env_show(prefix: str = typer.Option("APP_", "--prefix")) -> None:
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


# Config subcommands
config_app = typer.Typer(help="Config inspection and management")


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
) -> None:
    """Show config value by key."""
    try:
        config_dict = load_yaml_file(config_file)
        show_config(config_dict, key)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config_file}", err=True)
        raise typer.Exit(code=1)


@config_app.command("list")
def list_keys(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """List all config keys in hierarchical view."""
    try:
        config_dict = load_yaml_file(config_file)
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
    if search_dir:
        search_paths = [
            Path(search_dir) / "ki.yaml",
            Path(search_dir) / ".ki" / "ki.yaml",
            Path(search_dir) / ".ki.yaml",
        ]
    show_config_paths(search_paths if search_dir else None)


app.add_typer(config_app, name="config")


# Prompts subcommands
prompts_app = typer.Typer(help="Prompt management and configuration")


@prompts_app.command("list")
def prompts_list(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
    enabled_only: bool = typer.Option(False, "--enabled-only", help="Show only enabled roles"),
) -> None:
    """List all available prompt roles."""
    prompts_cli.list_roles(config_file, enabled_only)


@prompts_app.command("show")
def prompts_show(
    role_id: str = typer.Argument(..., help="Role ID to show"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Show details of a specific prompt role."""
    prompts_cli.show_role(role_id, config_file)


@prompts_app.command("set")
def prompts_set(
    role_id: str = typer.Argument(..., help="Role ID to activate"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Set the active prompt role."""
    prompts_cli.set_active_role(role_id, config_file)


# Templates subcommands
templates_app = typer.Typer(help="Manage custom prompt templates")


@templates_app.command("list")
def templates_list(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """List all custom prompt templates."""
    prompts_cli.list_templates(config_file)


@templates_app.command("show")
def templates_show(
    template_id: str = typer.Argument(..., help="Template ID to show"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Show details of a specific template."""
    prompts_cli.show_template(template_id, config_file)


@templates_app.command("create")
def templates_create(
    template_id: str = typer.Argument(..., help="Unique template ID"),
    name: str = typer.Option(..., "--name", "-n", help="Template name"),
    system_prompt: str = typer.Option(..., "--prompt", "-p", help="System prompt content"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
    description: str = typer.Option("", "--description", "-d", help="Template description"),
    tags: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Tags for the template"),
) -> None:
    """Create a new custom prompt template."""
    prompts_cli.create_template(template_id, name, system_prompt, config_file, description, tags)


@templates_app.command("delete")
def templates_delete(
    template_id: str = typer.Argument(..., help="Template ID to delete"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Delete a custom prompt template."""
    prompts_cli.delete_template(template_id, config_file)


# Favorites subcommands
favorites_app = typer.Typer(help="Manage favorite roles and templates")


@favorites_app.command("add")
def favorites_add(
    identifier: str = typer.Argument(..., help="Role or template ID to favorite"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Add a role or template to favorites."""
    prompts_cli.add_favorite(identifier, config_file)


@favorites_app.command("remove")
def favorites_remove(
    identifier: str = typer.Argument(..., help="Role or template ID to unfavorite"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Remove a role or template from favorites."""
    prompts_cli.remove_favorite(identifier, config_file)


# Language Learning subcommands
ll_app = typer.Typer(help="Manage language learning mode")


@ll_app.command("enable")
def ll_enable(
    target_language: str = typer.Argument(..., help="Language to learn"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
    level: str = typer.Option("beginner", "--level", "-l", help="Difficulty level (beginner/intermediate/advanced)"),
    native: str = typer.Option("English", "--native", help="Native language for translations"),
) -> None:
    """Enable language learning mode."""
    prompts_cli.enable_language_learning(target_language, config_file, level, native)


@ll_app.command("disable")
def ll_disable(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Disable language learning mode."""
    prompts_cli.disable_language_learning(config_file)


@ll_app.command("show")
def ll_show(
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Show language learning configuration."""
    prompts_cli.show_language_learning(config_file)


# Add nested command groups
prompts_app.add_typer(templates_app, name="templates")
prompts_app.add_typer(favorites_app, name="favorites")
prompts_app.add_typer(ll_app, name="language-learning")

# Config and prompts subcommands to main app
@prompts_app.command("export")
def prompts_export(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file (stdout if omitted)"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Export prompt configuration to file."""
    prompts_cli.export_config(output, config_file)


@prompts_app.command("import")
def prompts_import(
    input_file: str = typer.Argument(..., help="Input file to import"),
    config_file: str = typer.Option("ki.yaml", "--config", "-c", help="Target config file"),
    merge: bool = typer.Option(True, "--merge/--replace", help="Merge with existing or replace"),
) -> None:
    """Import prompt configuration from file."""
    prompts_cli.import_config(input_file, config_file, merge)


app.add_typer(prompts_app, name="prompts")


if __name__ == "__main__":
    app()
