from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml
from jsonschema import Draft7Validator

from .core import ConfigResolver, load_yaml_file
from .scaffold import available_templates, scaffold_template

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
    schema: str = typer.Argument(..., help="Path to JSON schema file"),
) -> None:
    data = load_yaml_file(config)
    schema_data = yaml.safe_load(Path(schema).read_text(encoding="utf-8"))
    validator = Draft7Validator(schema_data)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            typer.echo(f"- {list(error.path) or '<root>'}: {error.message}", err=True)
        raise typer.Exit(code=1)
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


if __name__ == "__main__":
    app()
