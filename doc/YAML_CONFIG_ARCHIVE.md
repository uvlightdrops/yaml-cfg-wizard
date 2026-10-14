# Archiv ueberholter YAML-Konfigurationsaussagen

Stand der Auswahl: 2026-10-14. **Keine Betriebsanleitung.**
Aktuell: [YAML_CONFIG_SYSADMIN.md](YAML_CONFIG_SYSADMIN.md);
Engineering: [YAML_CONFIG_CONCEPTS.md](YAML_CONFIG_CONCEPTS.md).

Nur konkrete ueberholte YAML-Fragmente sind hier archiviert. Nicht ganze
Navigations-/Deployment-Proposals oder aktuelle Anleitungen. Quellen aus `HEAD`
sind historische Git-Fassungen der lokalen Repos; bestehende geloeschte Dateien
und fremde Dokumentationsmigrationen wurden nicht wiederhergestellt.

## 1. ki-core: Rangfolge und Credential-Wrapper

Quelle: `ki-core/CONFIG_GUIDE.md`, Arbeitskopie vor dieser Dokumentationsaenderung.

```text
1. Environment variables (KI_CFG_* prefix)
2. Runtime files (config/runtime/runtime.yaml)
3. Stages (config/stages/*.yaml)
4. Profiles (config/profiles/*.yaml)
5. Defaults (config/defaults/*.yaml)
6. Main config (ki.yaml)
7. Schema defaults
```

Warum ueberholt: `src/ki_core/config.py` laedt `ki.yaml` **ueber** dem
Defaults-Verzeichnis, nur ausgewaehlte Stage/Profil-Dateien, und Credentials
zuletzt ueber Env. Die alte Datei zeigte ausserdem:

```yaml
creds:
  llm:
    providers:
      ki:
        api_key: "your-api-key"
```

Das ist ein historischer Platzhalter, kein Secret. Der aktuelle Merge hebt
`creds.llm` nicht nach `llm` an; Verbraucher lesen `llm.providers.ki.api_key`.
Auch die alte Zusage "All loaded config is validated against the merged JSON
Schema" ist zu stark: load_config prueft das Basisschema und fuellt App-
Schema-Defaults auf, ohne abschliessende Gesamtvalidierung.

## 2. yaml-cfg-wizard: alter API-Aufruf

Quelle: `yaml_cfg_wizard/docs/CONFIG_CLI.md`, Arbeitskopie vor dieser Aenderung.

```python
resolver = ConfigResolver(
    defaults=["config/defaults.yaml"],
    profiles=["config/profiles/production.yaml"],
    stages=["config/stages/prod.yaml"],
    env_prefix="KI_"
)
```

Warum ueberholt: Konstruktorargument heisst `stage`, nicht `stages`.
Dasselbe Dokument zeigte `from ki_core import Config` und
`Config.from_yaml("ki.yaml")`; der alte gemeinsame Config-Typ ist entfernt,
heute `load_config()` plus App-Accessor. Die alte allgemeine CLI-Behauptung
`KI_*` als Standardprefix ist falsch: Wizard standardmaessig `APP_`,
KI-Adapter explizit `KI_CFG_`. Schema-Defaults kommen aus Adapter/CLI-Helfern,
nicht automatisch aus `ConfigResolver`.

## 3. ki-knowledge: keine YAML-GUI / nur manuell und Neustart

Quelle: `ki-knowledge/doc/navigation-ia-proposal.md`, YAML-bezogener Auszug
der Arbeitskopie vor dieser Aenderung.

> Es gibt keine Flaeche fuer Config/YAML [...] es gibt aktuell keine GUI,
> um das anzuzeigen oder zu bearbeiten. Config-Aenderungen laufen heute
> nur ueber manuelles YAML-Editieren + Server-Neustart.

Zitat sprachlich ASCII-normalisiert und gekuerzt. Historische Phase-1-
Entscheidung: "Settings-Formulare sind in Phase 1 read-only".
Warum als genereller aktueller Status ueberholt: aktueller Code hat die
optionale `/settings/config/sync/`-Allowlist fuer zwei Runtime-Felder.
Dies widerlegt **nicht** die fehlende Vollbaum-GUI und bestaetigt keinen
getesteten Rollout. Der urspruengliche Vorschlag von Backup/Diff bleibt eine
nuetzliche Idee, ist aber nicht vom heutigen Editor implementiert.

## 4. kicli-code-assist: Env als abschliessende Schicht

Quelle: `kicli-code-assist/docs/KI_CORE_INTEGRATION.md` aus `HEAD`
(in der Arbeitskopie bereits geloescht).

```text
3. creds.yaml for secrets
4. schema validation + defaults from the merged YAML schema
5. environment variables (KI_CFG_*) as final overrides
```

Warum ueberholt: ki-core merged Credentials nach Env. Die Aussage zu
gemergter Gesamtvalidierung braucht die oben beschriebene Einschraenkung.
Der weiterhin richtige Gedanke "The assistant does not maintain its own
separate YAML merge system" bleibt im Betriebsguide erhalten.

## 5. ia3simworld: geplante universelle Runtime-Schicht

Quelle: `ia3simworld/docs/CONFIG_ARCHITECTURE.md` aus `HEAD`
(Arbeitskopie migriert nach `doc/`; dort bleiben nur Verweise).

```text
Merging Order (Highest -> Lowest Priority):
Environment Variables
Runtime State (state/domain_settings.json)
Stage Override
Simulation Profile
Defaults (config/defaults/*.yaml)
```

Quelle: `ia3simworld/docs/YAML_CONFIGURATION_PROPOSAL.md` aus `HEAD`.

```text
Proposed: Centralized YAML configuration system with:
- Single config/ directory
- 5 default YAML files
- 4 fixture files
- Dev/Prod separation
- 18 newly persistent settings

Precedence (Highest -> Lowest):
1. ENV vars
2. Runtime state
3. Environment override
4. Defaults
```

Warum historisch statt Betriebsanleitung: der zweite Auszug war ausdruecklich
ein **Vorschlag**, kein nachgewiesener Implementierungsstand. Go-koanf,
Python-Launcher, Auth-Runtime und Simulationszustand sind heute verschiedene
Verbraucher; `state/domain_settings.json` ist keine universelle YAML-Schicht.
Insbesondere flache Python-Stage-Dateien und Go-`stages/<name>/config.yaml`
sowie auth-only Runtime-Merges verhindern eine solche pauschale Anleitung.
Die Idee dauerhafter fachlicher Einstellungen bleibt im Konzept erhalten,
aber Zahlen und Vollintegrationsbehauptungen werden nicht als Status uebernommen.

## Bewusst nicht archiviert

Aktuelle `config/README.md`-Verweise und Editor-README in ia3simworld,
kicli-Profilskripte/-Examples und gueltige Skeleton-Kommandos sind nicht stale,
nur weil es einen neuen zentralen Guide gibt. ki-core
`docs/CONFIG_SCHEMA_REVIEW.md` kennzeichnet seinen historischen Entwurf bereits
explizit; nur ein Verweis auf das zentrale Konzept wird ergaenzt.
Nicht-YAML-Dokumente, Identity-Fachkonzepte und laufende Migrationen bleiben
an ihrem bisherigen Ort.
