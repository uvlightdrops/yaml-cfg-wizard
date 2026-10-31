# yaml-cfg-wizard Documentation

## Overview
`yaml-cfg-wizard` is a reusable YAML configuration resolution, merge, and validation toolkit. It provides:
- Layered configuration loading (defaults → profiles → stages → environment)
- Deep YAML merging with conflict resolution
- Environment variable overrides via `KI_CFG_*` pattern
- Schema validation with jsonschema
- Optional CLI for interactive config editing

**Status**: Stable (0.2.0)  
**Python**: ≥3.10  

## Quick Start

```bash
pip install yaml-cfg-wizard
```

```python
from yaml_cfg_wizard import load_config_stack

# Load base config + stage overlay
config = load_config_stack(base="config/defaults/stack.yaml", stage="dev")
```

## Key Documentation

- **[Concepts](./YAML_CONFIG_CONCEPTS.md)** - Core design and merge algorithm
- **[Sysadmin Guide](./YAML_CONFIG_SYSADMIN.md)** - Deployment and operations
- **[Archive](./YAML_CONFIG_ARCHIVE.md)** - Historical design notes

## Dependencies

- PyYAML ≥6.0 (YAML parsing)
- jsonschema ≥4.0 (validation)
- Optional: typer ≥0.12 (CLI), Django ≥4.2 (Django integration)

## Architecture

```
config/
├── defaults/
│   └── stack.yaml          # Base configuration
├── stages/                 # Stage overlays
│   ├── .active_stage       # Current active stage
│   ├── dev-lokal.yaml
│   ├── prod.yaml
│   └── minimal.yaml
└── runtime/                # Runtime overrides (git-ignored)
    └── runtime.yaml

Load Order (highest priority last):
1. config/defaults/*.yaml
2. config/stages/<active-stage>.yaml
3. config/runtime/*.yaml (if present)
4. Environment variables (KI_CFG_*)
```

## Configuration Pattern

All KI ecosystem projects use the same config pattern:
1. **Base** (`config/defaults/stack.yaml`): Default service configuration
2. **Stage** (`config/stages/<stage>.yaml`): Environment-specific overrides
3. **Runtime** (`config/runtime/runtime.yaml`): Local runtime config (git-ignored)
4. **Environment**: `KI_CFG_*` variables override everything

Set active stage via `KI_STAGE=dev-lokal` (default: `dev-lokal`)

## See Also

- [ki-core](../ki-core) - AI client abstraction (depends on yaml-cfg-wizard)
- [stackctl](../stackctl) - Stack management tool (uses this config pattern)
- [KI Ecosystem](../../../) - Full ecosystem documentation

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## License

MIT
