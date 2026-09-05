# YAML-Config-Wizard Features

**Last Updated:** 2026-09-05  
**Scope:** yaml-cfg-wizard library only (not app-specific features)

---

## ✅ Completed Features

### 1. Schema Utilities & Management
**Status:** ✅ **COMPLETE**

**What Was Built:**
- Schema merging with deep merge support
- Skeleton generation from schemas
- Schema validation and verification
- Multi-schema composition for inheritance

**Implementation Details:**
- `src/yaml_cfg_wizard/schema_utils.py` - Schema utilities
- `src/yaml_cfg_wizard/core.py` - Schema validation
- Supports JSON Schema format validation
- Enables schema inheritance patterns

**CLI Commands:**
```bash
yaml-cfg-wizard config skeleton <schema>             # Generate skeleton
yaml-cfg-wizard config verify <config> <schema>      # Validate
```

**Commits:**
- feat: Add schema utilities for merging and skeleton generation

**Documentation:**
- [CONFIG_CLI.md](./CONFIG_CLI.md) - CLI reference

---

### 2. Configuration CLI Utilities
**Status:** ✅ **COMPLETE**

**What Was Built:**
- Config show/display functionality
- Config list all settings
- Config path discovery
- Config file location reporting

**Implementation Details:**
- `src/yaml_cfg_wizard/config_cli.py` - CLI utilities
- Functions for show, list, validate, paths, skeleton
- Reusable for other projects

**CLI Commands:**
```bash
yaml-cfg-wizard config show [KEY]                     # Show config value
yaml-cfg-wizard config list                           # List all
yaml-cfg-wizard config paths                          # Show file locations
```

**Commits:**
- feat: Add config CLI utilities for show, list, validate, paths

**Documentation:**
- [CONFIG_CLI.md](./CONFIG_CLI.md) - Comprehensive reference

---

### 3. Path Validation Utilities
**Status:** ✅ **COMPLETE**

**What Was Built:**
- PathValidator class with full API
- Directory traversal prevention
- Path normalization and resolution
- Optional enforcement modes (warn vs block)
- 13 comprehensive tests (all passing)

**Implementation Details:**
- `src/yaml_cfg_wizard/path_validator.py` - Core validator (100 LOC)
- `tests/test_path_validator.py` - 13 tests
- `__init__.py` - Exported for reuse
- PathSecurityError exception

**Functions Available:**
```python
from yaml_cfg_wizard import PathValidator, create_validator_from_config

validator = PathValidator(allowed_base_path="/data", enforce=True)
validator.is_allowed("/data/file.txt")           # True
validator.validate("/data/file.txt")             # Path object
validator.make_relative("/data/file.txt")        # Path object
```

**Commits:**
- feat: Add path validation utilities for security

**Documentation:**
- [../kicli-code-assist/docs/SECURITY.md](../../kicli-code-assist/docs/SECURITY.md) - Usage guide for integration

---

## 📌 App-Specific Features

App-specific features (Security, GUI, KI Settings, etc.) have been moved to their respective project docs:

- **[kicli-code-assist/docs/FEATURES_IMPLEMENTED.md](../../kicli-code-assist/docs/FEATURES_IMPLEMENTED.md)** - kicli-code-assist implemented features
- **[kicli-code-assist/docs/customer_requests.md](../../kicli-code-assist/docs/customer_requests.md)** - kicli-code-assist backlog

This file now focuses on yaml-cfg-wizard library features only.

---

## 🔗 Related Documentation

- [CONFIG_CLI.md](./CONFIG_CLI.md) - Complete CLI reference
- [kicli-code-assist FEATURES_IMPLEMENTED.md](../../kicli-code-assist/docs/FEATURES_IMPLEMENTED.md) - App features
