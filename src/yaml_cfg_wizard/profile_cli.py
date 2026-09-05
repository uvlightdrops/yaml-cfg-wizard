"""CLI utilities for profile inspection and management."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml

from .core import load_yaml_file

ACTIVE_PROFILE_MARKER = ".active_profile"


def _profile_files(profiles_dir: str | Path) -> list[Path]:
    directory = Path(profiles_dir)
    if not directory.exists():
        return []
    return sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))


def _profile_names(profiles_dir: str | Path) -> list[str]:
    return [f.stem for f in _profile_files(profiles_dir)]


def _profile_path(profiles_dir: str | Path, name: str) -> Optional[Path]:
    directory = Path(profiles_dir)
    for ext in (".yaml", ".yml"):
        candidate = directory / f"{name}{ext}"
        if candidate.exists():
            return candidate
    return None


def read_active_profile(profiles_dir: str | Path) -> Optional[str]:
    """Read the currently active profile name, if one has been set."""
    marker = Path(profiles_dir) / ACTIVE_PROFILE_MARKER
    if not marker.exists():
        return None
    name = marker.read_text(encoding="utf-8").strip()
    return name or None


def list_profiles(profiles_dir: str | Path) -> None:
    """List available profiles, marking the active one."""
    names = _profile_names(profiles_dir)
    if not names:
        typer.echo("No profile files found.")
        return

    active = read_active_profile(profiles_dir)
    typer.echo("📋 Available profiles:")
    for name in names:
        marker = " (active)" if name == active else ""
        typer.echo(f"  - {name}{marker}")


def show_profile(profiles_dir: str | Path, name: str) -> None:
    """Show the contents of a single profile."""
    path = _profile_path(profiles_dir, name)
    if not path:
        typer.echo(f"❌ Profile '{name}' not found in {profiles_dir}", err=True)
        raise typer.Exit(code=1)

    data = load_yaml_file(path)
    typer.echo(f"📄 Profile '{name}' ({path}):")
    typer.echo(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))


def set_active_profile(profiles_dir: str | Path, name: str) -> None:
    """Mark a profile as the active one for subsequent resolves."""
    directory = Path(profiles_dir)
    path = _profile_path(directory, name)
    if not path:
        typer.echo(f"❌ Profile '{name}' not found in {profiles_dir}", err=True)
        raise typer.Exit(code=1)

    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / ACTIVE_PROFILE_MARKER
    marker.write_text(name, encoding="utf-8")
    typer.echo(f"✅ Active profile set to '{name}'")


def create_profile(profiles_dir: str | Path, name: str, from_template: Optional[str] = None) -> None:
    """Create a new, empty profile file (or copy from an existing template profile)."""
    directory = Path(profiles_dir)
    directory.mkdir(parents=True, exist_ok=True)

    existing = _profile_path(directory, name)
    if existing:
        typer.echo(f"❌ Profile '{name}' already exists: {existing}", err=True)
        raise typer.Exit(code=1)

    data: dict = {}
    if from_template:
        template_path = _profile_path(directory, from_template)
        if not template_path:
            typer.echo(f"❌ Template profile '{from_template}' not found", err=True)
            raise typer.Exit(code=1)
        data = load_yaml_file(template_path)

    target = directory / f"{name}.yaml"
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)
    typer.echo(f"✅ Profile created: {target}")
