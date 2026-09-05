"""Unit tests for prompts CLI commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from yaml_cfg_wizard.cli import app
import yaml


runner = CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temp directory with test config."""
    config_file = tmp_path / "ki.yaml"
    config_file.write_text(yaml.dump({
        'prompts': {
            'active_role': 'developer',
            'roles': {},
            'custom_templates': [],
            'language_learning': {
                'enabled': False,
                'target_language': '',
                'native_language': 'English',
                'level': 'beginner',
            },
            'favorites': [],
        }
    }))
    return tmp_path, config_file


class TestPromptsListCommand:
    """Test prompts list command."""
    
    def test_list_roles(self, temp_config_dir):
        """Test listing available roles."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "list",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Developer" in result.stdout
        assert "Tutor" in result.stdout
        assert "Code Reviewer" in result.stdout
    
    def test_list_shows_active_role(self, temp_config_dir):
        """Test that active role is marked."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "list",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        # Should show arrow next to developer (active role)
        assert "▶️" in result.stdout


class TestPromptsShowCommand:
    """Test prompts show command."""
    
    def test_show_role(self, temp_config_dir):
        """Test showing role details."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "show", "tutor",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Tutor" in result.stdout
        assert "Educational" in result.stdout
        assert "System Prompt" in result.stdout
    
    def test_show_nonexistent_role(self, temp_config_dir):
        """Test showing non-existent role fails."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "show", "nonexistent",
            "--config", str(config_file),
        ])
        assert result.exit_code != 0
        assert "not found" in result.stdout or "not found" in result.stderr


class TestPromptsSetCommand:
    """Test prompts set command."""
    
    def test_set_active_role(self, temp_config_dir):
        """Test setting active role."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "set", "tutor",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Active role set to: tutor" in result.stdout
        
        # Verify config was updated
        config = yaml.safe_load(config_file.read_text())
        assert config['prompts']['active_role'] == 'tutor'
    
    def test_set_invalid_role(self, temp_config_dir):
        """Test setting invalid role fails."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "set", "nonexistent",
            "--config", str(config_file),
        ])
        assert result.exit_code != 0


class TestTemplatesListCommand:
    """Test templates list command."""
    
    def test_list_no_templates(self, temp_config_dir):
        """Test listing when no templates exist."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "templates", "list",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "No custom templates" in result.stdout or "Custom Prompt Templates" in result.stdout


class TestTemplatesCreateCommand:
    """Test templates create command."""
    
    def test_create_template(self, temp_config_dir):
        """Test creating a custom template."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "templates", "create", "my-template",
            "--name", "My Template",
            "--prompt", "My prompt content",
            "--description", "A test template",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Template created: my-template" in result.stdout
        
        # Verify template was saved
        config = yaml.safe_load(config_file.read_text())
        templates = config['prompts']['custom_templates']
        assert len(templates) == 1
        assert templates[0]['id'] == 'my-template'
        assert templates[0]['name'] == 'My Template'
    
    def test_create_template_with_tags(self, temp_config_dir):
        """Test creating template with tags."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "templates", "create", "python-debug",
            "--name", "Python Debugger",
            "--prompt", "Debug prompt",
            "--tag", "python",
            "--tag", "debugging",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # Verify tags were saved
        config = yaml.safe_load(config_file.read_text())
        template = config['prompts']['custom_templates'][0]
        assert 'python' in template['tags']
        assert 'debugging' in template['tags']
    
    def test_create_duplicate_template(self, temp_config_dir):
        """Test creating duplicate template fails."""
        tmp_path, config_file = temp_config_dir
        
        # Create first
        result1 = runner.invoke(app, [
            "prompts", "templates", "create", "test",
            "--name", "Test",
            "--prompt", "Prompt",
            "--config", str(config_file),
        ])
        assert result1.exit_code == 0
        
        # Try to create duplicate
        result2 = runner.invoke(app, [
            "prompts", "templates", "create", "test",
            "--name", "Test 2",
            "--prompt", "Prompt 2",
            "--config", str(config_file),
        ])
        assert result2.exit_code != 0


class TestTemplatesDeleteCommand:
    """Test templates delete command."""
    
    def test_delete_template(self, temp_config_dir):
        """Test deleting a template."""
        tmp_path, config_file = temp_config_dir
        
        # Create first
        runner.invoke(app, [
            "prompts", "templates", "create", "to-delete",
            "--name", "Delete Me",
            "--prompt", "Prompt",
            "--config", str(config_file),
        ])
        
        # Verify created
        config = yaml.safe_load(config_file.read_text())
        assert len(config['prompts']['custom_templates']) == 1
        
        # Delete it
        result = runner.invoke(app, [
            "prompts", "templates", "delete", "to-delete",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Template deleted: to-delete" in result.stdout
        
        # Verify deleted
        config = yaml.safe_load(config_file.read_text())
        assert len(config['prompts']['custom_templates']) == 0
    
    def test_delete_nonexistent_template(self, temp_config_dir):
        """Test deleting non-existent template fails."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "templates", "delete", "nonexistent",
            "--config", str(config_file),
        ])
        assert result.exit_code != 0


class TestLanguageLearningCommand:
    """Test language learning commands."""
    
    def test_enable_language_learning(self, temp_config_dir):
        """Test enabling language learning."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "language-learning", "enable", "Deutsch",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Language learning enabled" in result.stdout
        
        # Verify config
        config = yaml.safe_load(config_file.read_text())
        ll = config['prompts']['language_learning']
        assert ll['enabled'] is True
        assert ll['target_language'] == 'Deutsch'
    
    def test_enable_language_learning_with_level(self, temp_config_dir):
        """Test enabling language learning with level."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "language-learning", "enable", "Español",
            "--level", "advanced",
            "--native", "Português",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # Verify config
        config = yaml.safe_load(config_file.read_text())
        ll = config['prompts']['language_learning']
        assert ll['level'] == 'advanced'
        assert ll['native_language'] == 'Português'
    
    def test_disable_language_learning(self, temp_config_dir):
        """Test disabling language learning."""
        tmp_path, config_file = temp_config_dir
        
        # Enable first
        runner.invoke(app, [
            "prompts", "language-learning", "enable", "Français",
            "--config", str(config_file),
        ])
        
        # Disable it
        result = runner.invoke(app, [
            "prompts", "language-learning", "disable",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Language learning disabled" in result.stdout
        
        # Verify
        config = yaml.safe_load(config_file.read_text())
        assert config['prompts']['language_learning']['enabled'] is False
    
    def test_show_language_learning(self, temp_config_dir):
        """Test showing language learning config."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "language-learning", "show",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Language Learning Configuration" in result.stdout


class TestExportImportCommands:
    """Test export and import commands."""
    
    def test_export_config(self, temp_config_dir, tmp_path):
        """Test exporting configuration."""
        tmp_path, config_file = temp_config_dir
        
        # Create a template first
        runner.invoke(app, [
            "prompts", "templates", "create", "test",
            "--name", "Test Template",
            "--prompt", "Test prompt",
            "--config", str(config_file),
        ])
        
        # Export
        export_file = tmp_path / "export.yaml"
        result = runner.invoke(app, [
            "prompts", "export",
            "--output", str(export_file),
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert export_file.exists()
        
        # Verify content
        exported = yaml.safe_load(export_file.read_text())
        assert 'prompts' in exported
        assert len(exported['prompts']['custom_templates']) == 1
    
    def test_export_to_stdout(self, temp_config_dir):
        """Test exporting to stdout."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "export",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "prompts:" in result.stdout
        assert "active_role:" in result.stdout
    
    def test_import_config(self, temp_config_dir, tmp_path):
        """Test importing configuration."""
        tmp_path, config_file = temp_config_dir
        
        # Create import file
        import_data = {
            'prompts': {
                'active_role': 'tutor',
                'custom_templates': [
                    {
                        'id': 'imported',
                        'name': 'Imported Template',
                        'system_prompt': 'Imported prompt',
                        'description': '',
                        'tags': [],
                    }
                ],
                'language_learning': {
                    'enabled': True,
                    'target_language': 'Italian',
                    'native_language': 'English',
                    'level': 'beginner',
                },
            }
        }
        import_file = tmp_path / "import.yaml"
        import_file.write_text(yaml.dump(import_data))
        
        # Import
        result = runner.invoke(app, [
            "prompts", "import", str(import_file),
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Config imported" in result.stdout
        
        # Verify
        config = yaml.safe_load(config_file.read_text())
        assert config['prompts']['active_role'] == 'tutor'
        assert len(config['prompts']['custom_templates']) == 1
        assert config['prompts']['language_learning']['target_language'] == 'Italian'


class TestFavoritesCommands:
    """Test favorites management commands."""
    
    def test_add_favorite(self, temp_config_dir):
        """Test adding favorite."""
        tmp_path, config_file = temp_config_dir
        result = runner.invoke(app, [
            "prompts", "favorites", "add", "tutor",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Added to favorites: tutor" in result.stdout
        
        # Verify
        config = yaml.safe_load(config_file.read_text())
        assert 'tutor' in config['prompts']['favorites']
    
    def test_remove_favorite(self, temp_config_dir):
        """Test removing favorite."""
        tmp_path, config_file = temp_config_dir
        
        # Add first
        runner.invoke(app, [
            "prompts", "favorites", "add", "developer",
            "--config", str(config_file),
        ])
        
        # Remove
        result = runner.invoke(app, [
            "prompts", "favorites", "remove", "developer",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        assert "Removed from favorites: developer" in result.stdout
        
        # Verify
        config = yaml.safe_load(config_file.read_text())
        assert 'developer' not in config['prompts']['favorites']


class TestIntegrationWorkflows:
    """Integration tests for complete workflows."""
    
    def test_complete_workflow(self, temp_config_dir, tmp_path):
        """Test a complete workflow."""
        tmp_path, config_file = temp_config_dir
        
        # 1. List roles
        result = runner.invoke(app, ["prompts", "list", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "Developer" in result.stdout
        
        # 2. Create custom template
        result = runner.invoke(app, [
            "prompts", "templates", "create", "custom",
            "--name", "Custom Prompt",
            "--prompt", "Custom content",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # 3. Add to favorites
        result = runner.invoke(app, [
            "prompts", "favorites", "add", "custom",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # 4. Enable language learning
        result = runner.invoke(app, [
            "prompts", "language-learning", "enable", "Français",
            "--level", "intermediate",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # 5. Set active role
        result = runner.invoke(app, [
            "prompts", "set", "tutor",
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # 6. Export
        export_file = tmp_path / "final.yaml"
        result = runner.invoke(app, [
            "prompts", "export",
            "--output", str(export_file),
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
        
        # Verify final state
        final_config = yaml.safe_load(export_file.read_text())
        assert final_config['prompts']['active_role'] == 'tutor'
        assert len(final_config['prompts']['custom_templates']) == 1
        assert 'custom' in final_config['prompts']['favorites']
        assert final_config['prompts']['language_learning']['enabled'] is True
