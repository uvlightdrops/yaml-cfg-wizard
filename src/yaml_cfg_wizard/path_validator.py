"""Path validation utilities for security-conscious file operations."""

from __future__ import annotations

from pathlib import Path
from typing import Union


class PathSecurityError(Exception):
    """Raised when a path violates security restrictions."""
    pass


class PathValidator:
    """Validates file paths against security restrictions."""
    
    def __init__(self, allowed_base_path: Union[str, Path, None] = None, enforce: bool = False):
        """
        Initialize path validator.
        
        Args:
            allowed_base_path: Absolute path that must not be left (e.g., /home/user/project)
            enforce: Whether to enforce restriction (if False, only warns)
            
        Raises:
            ValueError: If allowed_base_path is not absolute
        """
        self.enforce = enforce
        
        if allowed_base_path:
            base = Path(allowed_base_path)
            if not base.is_absolute():
                raise ValueError(f"allowed_base_path must be absolute: {allowed_base_path}")
            self.allowed_base = base.resolve()
        else:
            self.allowed_base = None
    
    def validate(self, path: Union[str, Path]) -> Path:
        """
        Validate a path against restrictions.
        
        Args:
            path: Path to validate
            
        Returns:
            Validated absolute path
            
        Raises:
            PathSecurityError: If path violates restrictions (and enforce=True)
        """
        abs_path = Path(path).resolve()
        
        if not self.allowed_base:
            return abs_path  # No restrictions
        
        # Check if path is within allowed base
        try:
            abs_path.relative_to(self.allowed_base)
        except ValueError:
            # Path is outside allowed base
            msg = (
                f"Path '{path}' escapes allowed base '{self.allowed_base}'. "
                f"All file operations must stay within the allowed directory."
            )
            if self.enforce:
                raise PathSecurityError(msg)
            else:
                # Log warning
                import warnings
                warnings.warn(msg, UserWarning)
        
        return abs_path
    
    def is_allowed(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is allowed.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        if not self.allowed_base:
            return True
        
        abs_path = Path(path).resolve()
        
        try:
            abs_path.relative_to(self.allowed_base)
            return True
        except ValueError:
            return False
    
    def make_relative(self, path: Union[str, Path]) -> Path:
        """
        Make path relative to allowed base (if set).
        
        Args:
            path: Path to convert
            
        Returns:
            Relative path from allowed_base, or absolute path if no base set
        """
        abs_path = Path(path).resolve()
        
        if not self.allowed_base:
            return abs_path
        
        try:
            return abs_path.relative_to(self.allowed_base)
        except ValueError:
            # Path is outside allowed base, return absolute
            return abs_path


def create_validator_from_config(config: dict) -> PathValidator:
    """
    Create a PathValidator from config dictionary.
    
    Args:
        config: Config dict with 'security' section
        
    Returns:
        PathValidator instance
    """
    security = config.get('security', {})
    return PathValidator(
        allowed_base_path=security.get('allowed_base_path'),
        enforce=security.get('enforce_path_restriction', False)
    )
