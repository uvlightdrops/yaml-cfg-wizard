# yaml_cfg_wizard

A reusable YAML configuration resolver and optional CLI wizard for layered config projects.

## Current operation and design

- [YAML_CONFIG_SYSADMIN.md](doc/YAML_CONFIG_SYSADMIN.md): current app-specific
  resolution, setup, CLI/UI operation, secrets and restart requirements.
- [YAML_CONFIG_CONCEPTS.md](doc/YAML_CONFIG_CONCEPTS.md): implemented components
  versus future engineering ideas and integration gaps.
- [YAML_CONFIG_ARCHIVE.md](doc/YAML_CONFIG_ARCHIVE.md): superseded YAML-only
  excerpts with source provenance, not operating instructions.

Status is based on current working-tree code, including unfinished extensions,
not proof of an installed or tested production rollout. The editor is a scalar
allowlist API, not a full configuration-tree UI.

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

With the optional server-rendered Django adapter:

```bash
pip install "yaml-cfg-wizard[django]"
```

## Optional configuration editor

`yaml_cfg_wizard.editor` has no web-framework dependency. The host registers
fixed file IDs, approved non-secret scalar `Field` paths, a complete JSON
Schema, and a `resolve(file_id, candidate_layer)` callback. The callback must
**replace** that layer in the real resolution chain, including higher-priority
environment/credential layers, rather than merge onto an already resolved
configuration. It must not include database overrides in the editable layer:
the host should exclude DB-owned fields or explicitly explain their precedence.

```python
from pathlib import Path
from yaml_cfg_wizard.editor import Editor, Field

editor = Editor(
    files={"runtime": Path("/srv/my-app/config/runtime/runtime.yaml")},
    fields=[Field("node.public_url", "Public URL")],
    resolve=resolve_candidate,  # supplied by the application
    schema=effective_schema,    # complete application JSON Schema
)
snapshot = editor.snapshot("runtime")
snapshot = editor.save("runtime", snapshot.revision, {"node.public_url": ""})
snapshot = editor.save("runtime", snapshot.revision, {}, remove=["node.public_url"])
```

Snapshots contain only registered paths, their override presence/value and their
effective value. Secret-named fields cannot be registered; URL credentials,
queries/fragments and non-scalar values are hidden. Applications must allowlist
only genuinely public fields (a schema is not a secret detector). Never expose
the full resolved dictionary or raw YAML in a template. Empty string and null
are values; removal is a separate operation that restores layer inheritance.

Before writing, both submitted field values and the **full effective config**
are validated. Errors never contain offending values. A SHA-256 revision rejects
stale writes (`ConflictError`); the entire target file contributes to it.
Higher-layer changes are resolved again at save time, but are not part of this
file revision. Saves preserve unrelated values and existing permission bits
(new files use `0600`), fsync a same-directory temporary file, atomically replace
the target, and fsync the directory. YAML formatting/comments are not preserved.
Missing targets are created; symlinked paths are rejected; inputs are limited
to 1 MiB. The Unix advisory `.editor.lock` sidecar must be honored by other
writers to eliminate races with external file editors. Keep the directory
host-owned, not writable by untrusted users. Locks are intentionally persistent.

`yaml_cfg_wizard.django.render_editor(request, editor, template_name, context)`
supports GET and CSRF-protected POST with a host-owned HTML template. It is not
an endpoint or authentication system: **the host must enforce active admin
authorization before calling it** and use its existing Django middleware.
POST fields are `file`, `revision`, `path`, `action` (`set` or `remove`), and
`value` (YAML scalar, blank means empty string). Template context includes
`rows`, `snapshot`, `files`, `file_id`, `error`, and `saved`; supplied values are
never echoed after errors. Invalid requests return 400, stale writes 409.
No SPA, JavaScript build, or Node dependency is needed.

Host adapters currently live in ki-knowledge (`/settings/config/sync/`) and
ia3simworld (`ia3simworld/packages/yaml-cfg-wizard-ui/`, distribution
`yaml-cfg-wizard-ui`, import module `yaml_cfg_wizard_ui`, factory
`yaml_cfg_wizard_ui.create_editor`). Despite its reusable package name, the
current package implements **only the IA3 adapter for `node.master_url`**,
not a generic full-tree configuration UI. It provides an offline Python API
plus a gated gateway bridge at `/api/admin/config-editor`. The bridge requires local admin
authentication, transport/CSRF checks and an explicitly shared startup contract;
it rejects stages. This describes current code, not verified deployment.
See the sysadmin guide for its restricted scope and prerequisites.

Run the framework-free regression tests with
`python -m unittest discover -s tests`. ki-knowledge's
`tests/test_config_editor.py` additionally contains Django authorization, CSRF,
form-write and config-cache cases; their presence alone does not establish that
the current extensions have passed or are installed.

## CLI commands

The `yaml-cfg` command provides subcommands organized into four groups:

- `config` — inspect, validate, resolve, and scaffold single config files
- `profile` — list, inspect, activate, and create named config profiles
- `template` — scaffold a full config directory tree from a bundled template
- `env` — inspect environment variable overrides

### Optional ki-core integration

When `ki-core` is installed in the same environment, `yaml-cfg` automatically
delegates to `ki_core.commands` for consistency across the KI ecosystem:

```bash
# yaml-cfg config resolve → delegates to ki_core.commands.run_resolve if ki-core available
yaml-cfg config resolve --defaults-dir defaults

# yaml-cfg profile set → delegates to ki_core.commands.run_profile_set if ki-core available
yaml-cfg profile set local
```

If `ki-core` is not installed, `yaml-cfg` works standalone using its own implementations.
This optional integration means:

- **No dependency on ki-core** — yaml-cfg remains fully independent
- **Automatic consistency** — when both are present, same commands use shared logic
- **Zero breaking changes** — all commands work whether ki-core is installed or not

This is useful when deploying yaml-cfg alone (e.g., standalone config tool) or as part of
the KI ecosystem (where ki-core provides orchestration and shared commands).

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
Without an active profile this directory loads all profile files.
`--stages-dir` always loads all stage files; use explicit file paths with
`--stage` to select one. These generic commands do not reproduce ki-core's
selector/credentials contract automatically. `--schema` fills defaults, it does
not validate `resolve`; use `verify` separately. Inspection and resolution
output is not secret-redacted.

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

Inspect a single config file plus schema defaults (not all application layers):

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
