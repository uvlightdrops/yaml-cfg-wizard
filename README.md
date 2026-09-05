# yaml_cfg_wizard

A reusable YAML configuration resolver and optional CLI wizard for layered config projects.

## Goal

This package is designed to be reused by apps that need deterministic multi-layer config resolution with:

- defaults
- profiles
- stage overlays
- runtime overrides
- environment overrides
- validation via JSON Schema

## Robust directory structure

```text
yaml_cfg_wizard/
├── README.md
├── pyproject.toml
├── schema/
│   └── config.schema.yaml
├── defaults/
│   └── app.yaml
├── profiles/
│   └── local.yaml
├── stages/
│   └── dev.yaml
├── runtime/
│   └── runtime.yaml
├── src/
│   └── yaml_cfg_wizard/
│       ├── __init__.py
│       ├── core.py
│       └── cli.py
├── examples/
│   ├── defaults/
│   │   └── app.yaml
│   ├── profiles/
│   │   └── local.yaml
│   ├── stages/
│   │   └── dev.yaml
│   └── runtime.yaml
├── tests/
│   └── test_core.py
└── .gitignore
```

This is more robust because it makes the config layers explicit and deterministic.

## Merge order

The resolver applies config in this order:

1. defaults
2. profile
3. stage
4. runtime
5. environment variables

The last layer wins.

## Installation

Library-only usage:

```bash
pip install yaml-cfg-wizard
```

With CLI support:

```bash
pip install "yaml-cfg-wizard[cli]"
```

## CLI commands

The `yaml-cfg-wizard` command provides multiple subcommands.

### resolve

Merge and resolve all config layers:

```bash
yaml-cfg-wizard resolve \
  --defaults-dir defaults \
  --profiles-dir profiles \
  --stages-dir stages \
  --runtime-file runtime/runtime.yaml
```

### validate

Validate a config file against a schema:

```bash
yaml-cfg-wizard validate examples/defaults/app.yaml schema/config.schema.yaml
```

### list-profiles

List available profiles:

```bash
yaml-cfg-wizard list-profiles profiles
```

### env-show

Show relevant environment variables:

```bash
yaml-cfg-wizard env-show --prefix APP_
```

### scaffold

Create config skeleton from template:

```bash
yaml-cfg-wizard scaffold ia3 /path/to/your/project/config
```

### config (NEW)

Config inspection and management utilities:

```bash
# Generate config skeleton from schema
yaml-cfg-wizard config skeleton base.schema.yaml -o ki.yaml

# Show config value by key
yaml-cfg-wizard config show llm_provider --config ki.yaml

# List all config keys hierarchically
yaml-cfg-wizard config list --config ki.yaml

# Validate config against schema
yaml-cfg-wizard config verify config.yaml schema.yaml

# Show config file search paths
yaml-cfg-wizard config paths
```

See [docs/CONFIG_CLI.md](docs/CONFIG_CLI.md) for detailed config CLI documentation.

## Python usage

```python
from yaml_cfg_wizard import ConfigResolver

resolver = ConfigResolver(
    defaults_dir="defaults",
    profiles_dir="profiles",
    stages_dir="stages",
    runtime_file="runtime/runtime.yaml",
    env_prefix="APP_",
)
config = resolver.resolve()
print(config)
```

## IA3 template format

The package includes an IA3-style template under `src/yaml_cfg_wizard/templates/ia3/`. This is a reusable scaffold, not the live config of the sim project.

```bash
yaml-cfg scaffold ia3 /path/to/your/project/config
```

This creates a layout like:

```text
config/
├── defaults/
│   ├── ports.yaml
│   ├── world.yaml
│   ├── node.yaml
│   ├── ai.yaml
│   └── ui.yaml
├── profiles/
│   ├── small-test.yaml
│   ├── medium-standard.yaml
│   ├── large-federated.yaml
│   └── perf-benchmark.yaml
├── stages/
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── runtime/
│   └── runtime.yaml
├── schema/
│   └── ia3-config.schema.yaml
└── README.md
```

This is intentionally generic. The consuming app remains responsible for the real config values it actually uses.

Example default config:

```yaml
world:
  width: 2560
  height: 2560
  tick_rate_ms: 200
  terrain:
    grass_ratio: 0.62
    forest_ratio: 0.18
    water_ratio: 0.08
    river_width: 3
  settlements:
    count: 4
    min_distance: 80
  agents:
    max_per_node: 1000
```

Example profile:

```yaml
world:
  width: 512
  height: 512
  tick_rate_ms: 50
  agents:
    max_per_node: 50

ai:
  ollama:
    enabled: false
```

Example stage:

```yaml
node:
  id: ia3-staging-1
  role: staging

ui:
  polling:
    compact_interval_ms: 1500
    full_state_interval_ms: 6000
```

Example runtime override:

```yaml
ui:
  polling:
    compact_interval_ms: 3000
```

Merge order:

1. defaults
2. profile
3. stage
4. runtime
5. environment variables

This is the reusable pattern for IA3 config layering, and it allows all services to share one config contract without duplicating merge logic.

## Notes

This project intentionally keeps the config engine generic. The consuming app still defines what keys exist in the config, while the library handles the merge and validation logic.
