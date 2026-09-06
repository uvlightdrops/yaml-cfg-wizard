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

The `yaml-cfg` command provides subcommands organized into four groups:

- `config` — inspect, validate, resolve, and scaffold single config files
- `profile` — list, inspect, activate, and create named config profiles
- `template` — scaffold a full config directory tree from a bundled template
- `env` — inspect environment variable overrides

### config resolve

Merge and resolve all config layers:

```bash
yaml-cfg config resolve \
  --defaults-dir defaults \
  --profiles-dir profiles \
  --stages-dir stages \
  --runtime-file runtime/runtime.yaml
```

If a profile has been activated with `yaml-cfg profile set` (see below), it is
picked up automatically from `--profiles-dir` unless `--profile` is given
explicitly to override it.

### config verify

Validate a config file against a schema:

```bash
yaml-cfg config verify examples/defaults/app.yaml schema/config.schema.yaml
```

### config skeleton

Generate a config skeleton with default values from a schema:

```bash
yaml-cfg config skeleton base.schema.yaml -o ki.yaml
```

### config show / list

Inspect a resolved config file:

```bash
yaml-cfg config show llm_provider --config ki.yaml
yaml-cfg config list --config ki.yaml
```

### profile list / show / set / create

Manage named config profiles:

```bash
yaml-cfg profile list profiles
yaml-cfg profile show local --profiles-dir profiles
yaml-cfg profile set local --profiles-dir profiles      # marks "local" active
yaml-cfg profile create staging --profiles-dir profiles --from local
```

Once a profile is marked active with `profile set`, `config resolve` uses it
automatically whenever the same `--profiles-dir` is passed, without needing
`--profile` on every call.

### template list / scaffold

Scaffold a full config directory tree (defaults/profiles/stages/runtime) from
a template. yaml-cfg-wizard ships with **no bundled templates** (it is
app-agnostic); drop your own template directory under
`site-packages/yaml_cfg_wizard/templates/<name>/` (or vendor/fork the
package) to use this feature, following the same
defaults/profiles/stages/runtime/schema layout `ConfigResolver` expects:

```bash
yaml-cfg template list
yaml-cfg template scaffold <name> /path/to/your/project/config
```

### env show

Show environment variables matching a prefix:

```bash
yaml-cfg env show --prefix APP_
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

This is the reusable pattern for layered config resolution, and it allows all services to share one config contract without duplicating merge logic.

## Notes

This project intentionally keeps the config engine generic. The consuming app still defines what keys exist in the config, while the library handles the merge and validation logic.
