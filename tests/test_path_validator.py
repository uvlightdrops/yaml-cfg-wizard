"""Tests for path validation and security utilities."""

import pytest
from pathlib import Path
import tempfile

from yaml_cfg_wizard import PathValidator, PathSecurityError, create_validator_from_config


class TestPathValidator:
    """Test PathValidator with various scenarios."""
    
    def test_no_restrictions(self):
        """Test validator with no restrictions."""
        validator = PathValidator()
        
        # Should allow any path
        assert validator.is_allowed("/tmp/file.txt")
        assert validator.is_allowed("/home/user/file.txt")
        assert validator.is_allowed("/etc/config.yaml")
        
        # All paths should pass validation
        assert validator.validate("/tmp/file.txt") == Path("/tmp/file.txt")
    
    def test_allowed_base_path(self):
        """Test validator with allowed base path."""
        validator = PathValidator(allowed_base_path="/home/user/project", enforce=False)
        
        # Paths within base should be allowed
        assert validator.is_allowed("/home/user/project/file.txt")
        assert validator.is_allowed("/home/user/project/subdir/file.txt")
        
        # Paths outside base should not be allowed
        assert not validator.is_allowed("/home/user/other/file.txt")
        assert not validator.is_allowed("/tmp/file.txt")
        assert not validator.is_allowed("/etc/config.yaml")
    
    def test_enforce_path_restriction(self):
        """Test strict enforcement of path restrictions."""
        validator = PathValidator(allowed_base_path="/home/user/project", enforce=True)
        
        # Valid path should pass
        result = validator.validate("/home/user/project/file.txt")
        assert result == Path("/home/user/project/file.txt")
        
        # Invalid path should raise
        with pytest.raises(PathSecurityError):
            validator.validate("/home/user/other/file.txt")
        
        with pytest.raises(PathSecurityError):
            validator.validate("/tmp/file.txt")
    
    def test_path_normalization(self):
        """Test that paths are properly normalized."""
        validator = PathValidator(allowed_base_path="/home/user/project", enforce=False)
        
        # Test with various forms
        assert validator.is_allowed("/home/user/project/./file.txt")
        assert validator.is_allowed("/home/user/project/subdir/../file.txt")
        
        # Symlinks attempting to escape should fail
        # (depends on actual filesystem, so we just verify normalization)
        normalized = validator.validate("/home/user/project/subdir/../file.txt")
        assert normalized == Path("/home/user/project/file.txt")
    
    def test_relative_path_conversion(self):
        """Test converting absolute paths to relative."""
        validator = PathValidator(allowed_base_path="/home/user/project")
        
        # Convert absolute to relative
        relative = validator.make_relative("/home/user/project/src/main.py")
        assert relative == Path("src/main.py")
        
        # Path outside base returns absolute
        absolute = validator.make_relative("/tmp/file.txt")
        assert absolute == Path("/tmp/file.txt")
        assert absolute.is_absolute()
    
    def test_empty_base_path(self):
        """Test validator with empty string base path."""
        validator = PathValidator(allowed_base_path="", enforce=True)
        
        # Empty string should mean no restrictions
        assert validator.is_allowed("/any/path")
        assert validator.is_allowed("/tmp/file.txt")
    
    def test_invalid_relative_base_path(self):
        """Test that relative base paths raise error."""
        with pytest.raises(ValueError, match="must be absolute"):
            PathValidator(allowed_base_path="./relative/path", enforce=True)
    
    def test_warning_on_violation_without_enforce(self):
        """Test that violations warn instead of raise without enforce."""
        validator = PathValidator(allowed_base_path="/home/user/project", enforce=False)
        
        # Should not raise, just warn
        with pytest.warns(UserWarning):
            validator.validate("/tmp/file.txt")


class TestCreateValidatorFromConfig:
    """Test creating validator from config dict."""
    
    def test_create_from_empty_config(self):
        """Test creating validator from empty config."""
        config = {}
        validator = create_validator_from_config(config)
        
        # Should create validator with no restrictions
        assert validator.allowed_base is None
        assert validator.enforce is False
    
    def test_create_from_config_with_security(self):
        """Test creating validator from config with security section."""
        config = {
            "security": {
                "allowed_base_path": "/home/user/project",
                "enforce_path_restriction": True
            }
        }
        validator = create_validator_from_config(config)
        
        assert validator.allowed_base == Path("/home/user/project")
        assert validator.enforce is True
        assert validator.is_allowed("/home/user/project/file.txt")
        assert not validator.is_allowed("/tmp/file.txt")
    
    def test_create_from_config_with_partial_security(self):
        """Test creating validator from config with partial security settings."""
        config = {
            "security": {
                "allowed_base_path": "/home/user/project"
            }
        }
        validator = create_validator_from_config(config)
        
        assert validator.allowed_base == Path("/home/user/project")
        assert validator.enforce is False
    
    def test_create_from_config_without_security(self):
        """Test creating validator from config without security section."""
        config = {
            "llm": {"provider": "openai"},
            "storage": {"cache_dir": "/tmp"}
        }
        validator = create_validator_from_config(config)
        
        assert validator.allowed_base is None
        assert validator.enforce is False


class TestPathSecurityIntegration:
    """Integration tests with temporary directories."""
    
    def test_with_real_temp_dir(self):
        """Test validator with actual temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            subdir = base_path / "project"
            subdir.mkdir()
            
            validator = PathValidator(allowed_base_path=str(base_path), enforce=True)
            
            # Create files and validate
            (subdir / "file.txt").touch()
            
            # Should allow access to created file
            assert validator.is_allowed(str(subdir / "file.txt"))
            
            # Should not allow access outside
            assert not validator.is_allowed("/etc/passwd")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
