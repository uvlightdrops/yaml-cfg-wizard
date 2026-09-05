# YAML Config Wizard - Configuration CLI Utilities

**Version:** 1.0  
**Last Updated:** 2026-09-05

---

## Overview

`yaml-cfg-wizard` provides a comprehensive set of command-line utilities for configuration management, schema validation, and config inspection. This package serves as the central hub for all config-related operations across the KI ecosystem.

---

## Core Components

### 1. Core Module (`core.py`)
**ConfigResolver** - Intelligent config merging with layered resolution

**Features:**
- Multi-level config merging (defaults, profiles, stages, runtime)
- Environment variable overrides with custom prefixes
- YAML/JSON format support
- Deep merge with proper precedence

**Example:**
```python
from yaml_cfg_wizard import ConfigResolver

resolver = ConfigResolver(
    defaults=["config/defaults.yaml"],
    profiles=["config/profiles/production.yaml"],
    stages=["config/stages/prod.yaml"],
    env_prefix="KI_"
)
result = resolver.resolve()
```

---

### 2. Schema Utilities (`schema_utils.py`)
**Schema management with merging and skeleton generation**

**Functions:**
- `merge_schemas(*paths)` - Deep merge multiple schema files
- `scaffold_skeleton_from_schema(schema, include_descriptions)` - Generate config skeleton
- `write_skeleton_to_file(skeleton, output_path)` - Write skeleton to YAML

**Example:**
```python
from yaml_cfg_wizard import merge_schemas, scaffold_skeleton_from_schema

# Merge base + app-specific schemas
merged = merge_schemas("base.schema.yaml", "app.schema.yaml")

# Generate skeleton with defaults
skeleton = scaffold_skeleton_from_schema(merged)
```

---

### 3. Config CLI (`config_cli.py`)
**High-level utilities for config inspection and management**

**Functions:**
- `show_config(config_dict, key)` - Display config value
- `list_config(config_dict)` - Show hierarchical tree view
- `validate_config(config_dict, schema)` - Validate against schema
- `show_config_paths(search_paths)` - Show file locations
- `generate_skeleton(base_schema, output, additional_schemas)` - Generate skeleton

---

## Command-Line Interface

### Available Commands

#### `config skeleton` - Generate config skeleton
```bash
yaml-cfg-wizard config skeleton base.schema.yaml \
  --output ki.yaml \
  --schema app.schema.yaml
```

#### `config show` - Display config value
```bash
# Show single value
yaml-cfg-wizard config show llm_provider --config ki.yaml

# Show all (omit key)
yaml-cfg-wizard config show --config ki.yaml
```

#### `config list` - Hierarchical key listing
```bash
yaml-cfg-wizard config list --config ki.yaml
```

**Output Example:**
```
📋 Config keys:
├── llm
│   ├── default_provider
│   └── providers
│       ├── ki
│       ├── openai
│       └── ollama
├── knowledge
│   ├── data_root
│   └── cache_db
└── storage
    ├── cache_dir
    └── session_dir
```

#### `config verify` - Validate config
```bash
yaml-cfg-wizard config verify ki.yaml base.schema.yaml
```

#### `config paths` - Show search paths
```bash
yaml-cfg-wizard config paths
```

**Output Example:**
```
📁 Config file search paths:
  ✅ exists : /home/user/ki.yaml
    missing: /home/user/.ki/ki.yaml
    missing: /home/user/.ki.yaml
    missing: /etc/ki/ki.yaml
```

---

### Other CLI Commands

#### `scaffold` - Scaffold config templates
```bash
yaml-cfg-wizard scaffold <template> <output-dir>
```

#### `resolve` - Resolve merged config
```bash
yaml-cfg-wizard resolve \
  --defaults-dir config/defaults \
  --profiles-dir config/profiles \
  --stages-dir config/stages \
  --output resolved.yaml
```

#### `validate` - Validate config file
```bash
yaml-cfg-wizard validate config.yaml schema.yaml
```

#### `list-profiles` - List available profiles
```bash
yaml-cfg-wizard list-profiles config/profiles
```

#### `env-show` - Show env variables
```bash
yaml-cfg-wizard env-show --prefix KI_
```

---

## Configuration Layer Resolution

When resolving configs, `yaml-cfg-wizard` follows this precedence order:

```
1. Environment variables (KI_* prefix)        ← Highest priority
2. Runtime files (config/runtime/)
3. Stages (config/stages/)
4. Profiles (config/profiles/)
5. Defaults (config/defaults/)
6. Schema defaults                            ← Lowest priority
```

---

## Schema Format

Schemas use **JSON Schema Draft 7** format with support for:
- Type definitions (string, number, boolean, object, array)
- Default values
- Property descriptions
- Nested objects
- Enum restrictions
- Required fields

**Example Schema:**
```yaml
$schema: http://json-schema.org/draft-07/schema#
type: object
properties:
  llm:
    type: object
    properties:
      default_provider:
        type: string
        default: openai
        enum: [ki, openai, ollama]
      providers:
        type: object
        properties:
          openai:
            type: object
            properties:
              api_key:
                type: string
                default: ""
              model:
                type: string
                default: gpt-4
```

---

## Integration Examples

### With ki-core
```python
from ki_core import Config
from ki_core.schema_manager import get_schema_path, load_merged_schema
from yaml_cfg_wizard import scaffold_skeleton_from_schema

# Load merged schemas (base + app-specific)
base_schema = get_schema_path()
merged = load_merged_schema(base_schema, [app_schema])

# Generate skeleton
skeleton = scaffold_skeleton_from_schema(merged)

# Load and validate config
config = Config.from_yaml("ki.yaml")
```

### With kicli-code-assist
```bash
# Generate config with app-specific defaults
kicli-assist config init -o my_config.yaml

# Inspect config
kicli-assist config show context_max_files
```

---

## Use Cases

### 1. Initial Setup
```bash
# Generate skeleton with all options
yaml-cfg-wizard config skeleton base.schema.yaml -o ki.yaml

# Edit with your values
vim ki.yaml

# Validate
yaml-cfg-wizard config verify ki.yaml base.schema.yaml
```

### 2. Environment-Specific Configs
```bash
# Create layered structure
config/
  ├── defaults.yaml          # All defaults
  ├── profiles/
  │   ├── development.yaml   # Dev overrides
  │   └── production.yaml    # Prod overrides
  └── stages/
      ├── dev.yaml
      └── prod.yaml

# Resolve for environment
yaml-cfg-wizard resolve \
  --defaults-dir config \
  --profiles-dir config/profiles \
  --stages-dir config/stages \
  --profile production \
  --stage prod
```

### 3. Validation Pipeline
```bash
# Validate all configs in CI
for config in config/**/*.yaml; do
  yaml-cfg-wizard config verify "$config" schema.yaml || exit 1
done
```

---

## API Reference

### ConfigResolver

**Constructor:**
```python
ConfigResolver(
    defaults: list[str] = [],
    profiles: list[str] = [],
    stage: list[str] = [],
    runtime: list[str] = [],
    defaults_dir: Optional[str] = None,
    profiles_dir: Optional[str] = None,
    stages_dir: Optional[str] = None,
    runtime_file: Optional[str] = None,
    env_prefix: str = "APP_"
)
```

**Methods:**
- `resolve() -> Dict[str, Any]` - Resolve all layers and return merged config
- `resolve_to_file(output_path: str)` - Write resolved config to file

### Schema Functions

**merge_schemas(*paths):**
```python
merged = merge_schemas("base.yaml", "app.yaml", "custom.yaml")
# Returns: Dict[str, Any]
```

**scaffold_skeleton_from_schema(schema, include_descriptions=False):**
```python
skeleton = scaffold_skeleton_from_schema(schema)
# Returns: Dict[str, Any] with all default values
```

**write_skeleton_to_file(skeleton, output_path):**
```python
write_skeleton_to_file(skeleton, Path("config.yaml"))
```

### Config CLI Functions

**show_config(config_dict, key=None):**
```python
show_config(config_dict, "llm_provider")
show_config(config_dict)  # Show all
```

**list_config(config_dict):**
```python
list_config(config_dict)  # Print tree view
```

**validate_config(config_dict, schema):**
```python
validate_config(config_dict, schema)  # Raises if invalid
```

---

## Best Practices

### 1. Schema Design
- Keep schemas DRY (Don't Repeat Yourself)
- Use `$ref` for reusable components
- Document all properties
- Provide sensible defaults

### 2. Config Organization
```
config/
  ├── defaults.yaml          # All options with defaults
  ├── profiles/
  │   ├── docker.yaml        # Docker overrides
  │   └── local.yaml         # Local dev overrides
  ├── stages/
  │   ├── dev.yaml
  │   ├── staging.yaml
  │   └── prod.yaml
  ├── runtime/
  │   └── runtime.yaml       # Runtime overrides
  └── creds.yaml             # Secrets (not in git)
```

### 3. Environment Variables
- Use consistent prefix (e.g., `KI_`)
- Double underscore for nesting: `KI_LLM__PROVIDER=openai`
- Values are auto-coerced: `true/false` → boolean, digits → int

### 4. Validation
- Always validate after modifications
- Validate in CI/CD pipeline
- Use schema versioning for compatibility

---

## Troubleshooting

### Config not found
```bash
yaml-cfg-wizard config paths  # Check search paths
ls -la ki.yaml               # Verify file exists
```

### Validation error
```bash
# Check exact error
yaml-cfg-wizard config verify config.yaml schema.yaml

# Inspect config
yaml-cfg-wizard config show --config config.yaml

# Validate schema syntax
python3 -c "import yaml; yaml.safe_load(open('schema.yaml'))"
```

### Merge not working
```bash
# Test merge explicitly
yaml-cfg-wizard config skeleton base.yaml --schema app.yaml

# Inspect result
yaml-cfg-wizard config list
```

---

## Contributing

Schema utilities follow these principles:
- Type-safe with full type hints
- Minimal dependencies (yaml, jsonschema only)
- Deep merge for nested objects
- Clear error messages
- Comprehensive validation

---

## See Also

- [ki-core CONFIG_GUIDE.md](../../ki-core/CONFIG_GUIDE.md)
- [kicli-code-assist docs](../../kicli-code-assist/docs/)
