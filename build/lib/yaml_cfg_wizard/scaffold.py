from __future__ import annotations

import shutil
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"


def available_templates() -> list[str]:
    if not TEMPLATE_ROOT.exists():
        return []
    return sorted(p.name for p in TEMPLATE_ROOT.iterdir() if p.is_dir())


def scaffold_template(template_name: str, output_dir: str | Path) -> None:
    source = TEMPLATE_ROOT / template_name
    if not source.exists():
        raise FileNotFoundError(f"Unknown template: {template_name}")

    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {destination}")

    shutil.copytree(source, destination)
