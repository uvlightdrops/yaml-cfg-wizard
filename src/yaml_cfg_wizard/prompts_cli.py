"""CLI utilities for prompt management."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import typer
import yaml

try:
    from kicli_code_assist.prompts import PromptManager, CustomTemplate
except ImportError:
    # Fallback if kicli is not installed
    PromptManager = None
    CustomTemplate = None


def get_prompt_manager(config_file: str = "ki.yaml") -> PromptManager:
    """Load config and create PromptManager instance.
    
    Args:
        config_file: Path to config file
        
    Returns:
        PromptManager instance
        
    Raises:
        FileNotFoundError: If config file not found
        ImportError: If kicli_code_assist not available
    """
    if PromptManager is None:
        typer.echo("❌ kicli_code_assist not installed", err=True)
        raise typer.Exit(code=1)
    
    from yaml_cfg_wizard.core import load_yaml_file
    
    try:
        config_dict = load_yaml_file(config_file)
    except FileNotFoundError:
        # Create empty config if file doesn't exist
        config_dict = {}
    
    return PromptManager(config_dict)


def save_prompt_config(manager: PromptManager, config_file: str = "ki.yaml") -> None:
    """Save prompt config to YAML file.
    
    Args:
        manager: PromptManager instance
        config_file: Path to config file
    """
    from yaml_cfg_wizard.core import load_yaml_file
    
    # Load existing config or create empty
    try:
        config_dict = load_yaml_file(config_file)
    except FileNotFoundError:
        config_dict = {}
    
    # Update prompts section
    config_dict['prompts'] = manager.to_dict()
    
    # Write back to file
    Path(config_file).parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


def list_roles(
    config_file: str = "ki.yaml",
    enabled_only: bool = False,
) -> None:
    """List all available prompt roles.
    
    Args:
        config_file: Path to config file
        enabled_only: Only show enabled roles
    """
    manager = get_prompt_manager(config_file)
    
    if enabled_only:
        roles = manager.list_enabled_roles()
    else:
        roles = manager.list_roles()
    
    if not roles:
        typer.echo("No roles available.")
        return
    
    active_role = manager.prompts_config.active_role
    typer.echo("📚 Available Prompt Roles:")
    for role_id, role in sorted(roles.items()):
        marker = "▶️ " if role_id == active_role else "  "
        enabled = "✅" if role.enabled else "❌"
        typer.echo(f"{marker}{enabled} {role.id}: {role.name}")


def show_role(
    role_id: str,
    config_file: str = "ki.yaml",
) -> None:
    """Show details of a specific role.
    
    Args:
        role_id: ID of the role to show
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    role = manager.get_role(role_id)
    
    if not role:
        typer.echo(f"❌ Role '{role_id}' not found", err=True)
        raise typer.Exit(code=1)
    
    typer.echo(f"\n📝 Role: {role.name}")
    typer.echo(f"   ID: {role.id}")
    typer.echo(f"   Version: {role.version}")
    typer.echo(f"   Enabled: {'✅ Yes' if role.enabled else '❌ No'}")
    if role.description:
        typer.echo(f"   Description: {role.description}")
    if role.tags:
        typer.echo(f"   Tags: {', '.join(role.tags)}")
    typer.echo(f"\n📋 System Prompt:")
    typer.echo("─" * 60)
    typer.echo(role.system_prompt)
    typer.echo("─" * 60)


def set_active_role(
    role_id: str,
    config_file: str = "ki.yaml",
) -> None:
    """Set the active prompt role.
    
    Args:
        role_id: ID of the role to activate
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    
    if not manager.set_active_role(role_id):
        typer.echo(f"❌ Role '{role_id}' not found", err=True)
        raise typer.Exit(code=1)
    
    save_prompt_config(manager, config_file)
    typer.echo(f"✅ Active role set to: {role_id}")


def list_templates(
    config_file: str = "ki.yaml",
) -> None:
    """List all custom prompt templates.
    
    Args:
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    templates = manager.list_templates()
    
    if not templates:
        typer.echo("No custom templates. Use 'ki prompts templates create' to create one.")
        return
    
    typer.echo("📦 Custom Prompt Templates:")
    for template in templates:
        is_fav = "⭐" if manager.is_favorite(template.id) else "  "
        typer.echo(f"{is_fav} {template.id}: {template.name}")
        if template.description:
            typer.echo(f"    {template.description}")


def show_template(
    template_id: str,
    config_file: str = "ki.yaml",
) -> None:
    """Show details of a specific template.
    
    Args:
        template_id: ID of the template to show
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    template = manager.get_template(template_id)
    
    if not template:
        typer.echo(f"❌ Template '{template_id}' not found", err=True)
        raise typer.Exit(code=1)
    
    typer.echo(f"\n📦 Template: {template.name}")
    typer.echo(f"   ID: {template.id}")
    if template.description:
        typer.echo(f"   Description: {template.description}")
    if template.tags:
        typer.echo(f"   Tags: {', '.join(template.tags)}")
    typer.echo(f"   Favorite: {'⭐ Yes' if manager.is_favorite(template.id) else 'No'}")
    typer.echo(f"\n📋 System Prompt:")
    typer.echo("─" * 60)
    typer.echo(template.system_prompt)
    typer.echo("─" * 60)


def create_template(
    template_id: str,
    name: str,
    system_prompt: str,
    config_file: str = "ki.yaml",
    description: str = "",
    tags: Optional[list[str]] = None,
) -> None:
    """Create a new custom prompt template.
    
    Args:
        template_id: Unique ID for the template
        name: Human-readable name
        system_prompt: The system prompt content
        config_file: Path to config file
        description: Optional description
        tags: Optional list of tags
    """
    if CustomTemplate is None:
        typer.echo("❌ kicli_code_assist not installed", err=True)
        raise typer.Exit(code=1)
    
    manager = get_prompt_manager(config_file)
    
    template = CustomTemplate(
        id=template_id,
        name=name,
        system_prompt=system_prompt,
        description=description,
        tags=tags or [],
    )
    
    if not manager.create_template(template):
        typer.echo(f"❌ Template '{template_id}' already exists", err=True)
        raise typer.Exit(code=1)
    
    save_prompt_config(manager, config_file)
    typer.echo(f"✅ Template created: {template_id}")


def delete_template(
    template_id: str,
    config_file: str = "ki.yaml",
) -> None:
    """Delete a custom prompt template.
    
    Args:
        template_id: ID of the template to delete
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    
    if not manager.delete_template(template_id):
        typer.echo(f"❌ Template '{template_id}' not found", err=True)
        raise typer.Exit(code=1)
    
    save_prompt_config(manager, config_file)
    typer.echo(f"✅ Template deleted: {template_id}")


def add_favorite(
    identifier: str,
    config_file: str = "ki.yaml",
) -> None:
    """Add a role or template to favorites.
    
    Args:
        identifier: Role or template ID
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    
    if not manager.add_favorite(identifier):
        typer.echo(f"⚠️  '{identifier}' is already a favorite", err=True)
        raise typer.Exit(code=1)
    
    save_prompt_config(manager, config_file)
    typer.echo(f"⭐ Added to favorites: {identifier}")


def remove_favorite(
    identifier: str,
    config_file: str = "ki.yaml",
) -> None:
    """Remove a role or template from favorites.
    
    Args:
        identifier: Role or template ID
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    
    if not manager.remove_favorite(identifier):
        typer.echo(f"❌ '{identifier}' is not in favorites", err=True)
        raise typer.Exit(code=1)
    
    save_prompt_config(manager, config_file)
    typer.echo(f"✅ Removed from favorites: {identifier}")


def enable_language_learning(
    target_language: str,
    config_file: str = "ki.yaml",
    level: str = "beginner",
    native_language: str = "English",
) -> None:
    """Enable language learning mode.
    
    Args:
        target_language: Language to learn
        config_file: Path to config file
        level: Difficulty level (beginner/intermediate/advanced)
        native_language: Native language for translations
    """
    manager = get_prompt_manager(config_file)
    
    if not manager.enable_language_learning(target_language, level):
        typer.echo(f"❌ Invalid level: {level}", err=True)
        raise typer.Exit(code=1)
    
    manager.prompts_config.language_learning.native_language = native_language
    save_prompt_config(manager, config_file)
    typer.echo(f"✅ Language learning enabled for: {target_language} (Level: {level})")


def disable_language_learning(
    config_file: str = "ki.yaml",
) -> None:
    """Disable language learning mode.
    
    Args:
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    manager.disable_language_learning()
    save_prompt_config(manager, config_file)
    typer.echo("✅ Language learning disabled")


def show_language_learning(
    config_file: str = "ki.yaml",
) -> None:
    """Show language learning configuration.
    
    Args:
        config_file: Path to config file
    """
    manager = get_prompt_manager(config_file)
    ll = manager.prompts_config.language_learning
    
    typer.echo("🌍 Language Learning Configuration:")
    typer.echo(f"   Enabled: {'✅ Yes' if ll.enabled else '❌ No'}")
    if ll.enabled:
        typer.echo(f"   Target Language: {ll.target_language}")
        typer.echo(f"   Native Language: {ll.native_language}")
        typer.echo(f"   Level: {ll.level.value}")


def export_config(
    output_file: Optional[str] = None,
    config_file: str = "ki.yaml",
) -> None:
    """Export prompt configuration to file.
    
    Args:
        output_file: Output file path (stdout if None)
        config_file: Source config file
    """
    manager = get_prompt_manager(config_file)
    config_data = manager.to_config()
    
    output_yaml = yaml.dump(config_data, default_flow_style=False, sort_keys=False)
    
    if output_file:
        Path(output_file).write_text(output_yaml)
        typer.echo(f"✅ Config exported to: {output_file}")
    else:
        typer.echo(output_yaml)


def import_config(
    input_file: str,
    config_file: str = "ki.yaml",
    merge: bool = True,
) -> None:
    """Import prompt configuration from file.
    
    Args:
        input_file: Input file path
        config_file: Target config file
        merge: If True, merge with existing. If False, replace.
    """
    from yaml_cfg_wizard.core import load_yaml_file
    
    try:
        import_data = load_yaml_file(input_file)
    except FileNotFoundError:
        typer.echo(f"❌ File not found: {input_file}", err=True)
        raise typer.Exit(code=1)
    
    if merge:
        # Load existing config and merge
        try:
            config_dict = load_yaml_file(config_file)
        except FileNotFoundError:
            config_dict = {}
        
        # Merge prompts section
        if 'prompts' in import_data:
            config_dict['prompts'] = import_data['prompts']
    else:
        # Replace entire config
        config_dict = import_data
    
    # Write back
    Path(config_file).parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    typer.echo(f"✅ Config imported from: {input_file}")
