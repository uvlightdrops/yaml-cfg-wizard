# YAML Config Wizard: CLI reference

Current operation, secrets precautions and actual application differences:
[YAML_CONFIG_SYSADMIN.md](../doc/YAML_CONFIG_SYSADMIN.md).
Generic API/design: [YAML_CONFIG_CONCEPTS.md](../doc/YAML_CONFIG_CONCEPTS.md).
Superseded excerpts from the previous reference:
[YAML_CONFIG_ARCHIVE.md](../doc/YAML_CONFIG_ARCHIVE.md).

Install the `cli` extra; Python >=3.10. The declared package version is 0.2.0
in the current working tree, not proof of an installed release.
Run `yaml-cfg --help` or `yaml-cfg config resolve --help` for options.

```bash
yaml-cfg config skeleton base.schema.yaml -o config.generated.yaml --schema app.schema.yaml
yaml-cfg config verify config.generated.yaml base.schema.yaml
yaml-cfg config list --config config.generated.yaml
yaml-cfg config show llm --config config.generated.yaml
yaml-cfg profile list config/profiles
yaml-cfg profile set local --profiles-dir config/profiles
yaml-cfg profile create staging --profiles-dir config/profiles --from local
yaml-cfg config resolve --defaults-dir config/defaults \
  --profile config/profiles/local.yaml --stage config/stages/dev.yaml \
  --runtime-file config/runtime/runtime.yaml --env-prefix APP_
yaml-cfg template list
```

Paths/names are examples, not guaranteed bundled fixtures. No templates are
bundled. `skeleton` can discover optional ki-core plus cwd app schemas when
the base argument is omitted; its output may overwrite an existing file.
`show` accepts a top-level key, not dotted-path lookup. `show/list` inspect
one file plus schema defaults, not the application's effective layered config.

`resolve` order is defaults -> profiles -> stages -> runtime -> env; default
prefix is `APP_`. Explicit profile/stage arguments are file paths.
`--profiles-dir` uses its active profile marker if available, otherwise loads
all profiles. `--stages-dir` loads all stages; it does not consume `KI_STAGE`.
`--schema` supplies defaults, not validation. `--output` currently writes
resolver layers without the schema defaults subsequently added to stdout.
`verify` checks one file/schema; no automatic credentials merge occurs.
Neither config output, env inspection nor generic validation errors are
guaranteed secret-redacted.

Python entry points:

```python
from yaml_cfg_wizard import ConfigResolver
from yaml_cfg_wizard.schema_utils import merge_schemas, scaffold_skeleton_from_schema

resolver = ConfigResolver(
    defaults=["config/defaults.yaml"],
    profiles=["config/profiles/local.yaml"],
    stage=["config/stages/dev.yaml"],
    runtime_file="config/runtime/runtime.yaml",
    env_prefix="APP_",
    schema_file="schema/app.schema.yaml",
)
config = resolver.resolve()
```

`stage` is singular. `resolve_to_file()` writes resolved layers. The generic
resolver optionally validates against `schema_file` with Draft 7 without
format checking and does not inject schema defaults itself. Schema composition
and skeleton generation are separate utilities.
