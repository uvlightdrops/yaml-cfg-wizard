# YAML-Konfiguration: Konzept und weitere Ideen

Stand: 2026-10-14. Kanonische Engineering-Dokumentation im Projekt
yaml-cfg-wizard. Betrieb: [YAML_CONFIG_SYSADMIN.md](YAML_CONFIG_SYSADMIN.md);
historische Quellen: [YAML_CONFIG_ARCHIVE.md](YAML_CONFIG_ARCHIVE.md).
Die folgende Trennung ist verbindlich: **vorhandener Code** ist nicht gleich
getestete Installation oder fertiger Rollout. Neue Editor-/Identity-Erweiterungen
in den Arbeitskopien sind in diesem Dokument nicht als freigegeben zertifiziert.

## Vorhandene Bausteine und Grenzen

| Baustein | Implementiert | Nicht daraus ableitbar |
| --- | --- | --- |
| `core.py` | Deep-Merge, YAML-Dateien/-Verzeichnisse, Env-Skalare, optional Draft-7-Validierung | App-Dateisuche, Credential-Policy, einzelne aktive Stage, allgemeines Format-Checking |
| `schema_utils.py` | Schema-Merge und Skeletons | Vollstaendige semantische App-Validierung; Listen-Schemaelemente werden ersetzt |
| `cli.py` | Inspection, Skeleton, Verify, explizites Resolve, Profile-Marker, Templates | Secret-Redaktion, identische ki-core-Aufloesung, fertige mitgelieferte App-Templates |
| `editor.py` (neuer Code) | `Field`, `Snapshot`, `Editor.snapshot/save`, feste Datei-IDs und skalare Allowlist, Set/Remove, Schema-/Konfliktpruefung, atomare Unix-Schreibvorgaenge | Vollbaum-Editor, Listen-/Objektbearbeitung, Kommentarerhalt, Backup-/Diff-UI, Transaktion ueber alle Schichten |
| `django.py` (optional, neuer Code) | `render_editor`, GET/CSRF-POST, hosteigenes Template, 400/409 | Eigene Auth, URL-Registrierung, fertige Web-App, SPA |
| ki-core | KI-Dateisuche, eine Stage/ein Profil, Credentials zuletzt, Basisschema und App-Skeleton | DB-Vererbung, universelle App- oder Go-Integration, abschliessende Gesamtvalidierung |

Aktuelle Adapter: ki-knowledge mit zwei Runtime-Feldern und Superuser-Grenze;
ia3simworld mit `node.master_url`, Offline-API und streng begrenzter Gateway-
Bridge. kicli-code-assist hat einen eigenen Textual-Dialog. kicli ist noch auf
einem separaten Alt-Loader. Go koanf und Python-Launcher in ia3simworld haben
abweichende Pfade und konsumierte Schichten. Diese Unterschiede sind
Integrationsluecken, keine durch Dokumentation behobene Vereinheitlichung.

## Architektur: generischer Core, explizite Host-Vertraege

Der Core sollte unabhaengig von App-Namen, Django, Textual, React, DB und
Transport bleiben. Schemas definieren Form/Defaults; Apps verantworten
fachliche Semantik, sichere Feldfreigabe, Laufzeitverbrauch und Neustart.
ki-core ist ein KI-spezifischer Resolver-Adapter, nicht Besitzer aller App-Domaenen.
Web-/Terminal-Adapter sollen dieselben Bearbeitungsoperationen verwenden,
ohne eine Framework-Abhaengigkeit in den Core einzuschleusen.

Schon heute muss der Host `resolve(file_id, candidate_layer)` liefern:
die geaenderte Schicht **ersetzen**, dann die reale Aufloesung erneut ausfuehren,
einschliesslich hoeherer Env-/Credential-Schichten. Auf ein bereits effektives
Dictionary mergen waere falsch: Remove wuerde die Vererbung nicht wiederherstellen.
DB-owned Felder ausschliessen oder gesondert und klar priorisiert anzeigen.
Beispiel ki-knowledge: NodeConfig-Administration bleibt ausserhalb des YAML-Editors.

## Herkunft, Schreiben und Konflikte

**Heute:** Snapshot enthaelt registrierten Pfad, Label, Beschreibung,
Override-Praesenz/-Wert und effektiven Wert; keine komplette Origins-Tabelle.
Leerer String/null und Remove sind verschieden. Kandidat und geaenderte Felder
werden validiert, damit ein hoeherer Override keinen ungueltigen gespeicherten
Wert maskiert. Dateirevision erfasst den gesamten Zielinhalt; Lock serialisiert
kooperierende Schreiber, temp-Datei/fsync/replace schuetzen die Persistenz.
YAML-Kommentare gehen verloren. Fremde Schreiber ohne Lock und Aenderungen
anderer Schichten bleiben Grenzen.

**Geplant/Ideen, nicht implementierte Zusagen:** expliziter Resolution-Plan mit
allen Quellen und pro Pfad Origin/Winner/Shadowing; UI waehlt eine freigegebene
Schreibschicht statt willkuerlicher Dateipfade. Quellenfingerprints fuer den
gesamten Plan, serverseitige Preview/Diff vor Apply, geschuetzte Backup-/Rollback-
Historie, nachvollziehbare Audit-Ereignisse ohne Werte/Secrets und definierte
Mehrdatei-Transaktionen. Kommentarerhalt nur mit bewusst gewaehltetem Roundtrip-
Parser; keine stillschweigende Zusage bei `safe_dump`.

## Optionale Oberflaechen

**Heute:** schema-gestuetzte Allowlist-Formulare, keine Vollbaum-Oberflaeche.
Ein generisches Feldschema macht einen Wert nicht automatisch oeffentlich.
Secret-Namen und unsichere URLs werden im neuen Core eingeschraenkt, aber
fachliche Secret-Klassifizierung bleibt Host-Aufgabe.

**Weitere Ideen:** navigierbarer Configbaum mit Herkunft/Restart-Hinweisen,
Suchfunktion, Gruppen, bedingten Feldern und explizitem Override-Reset.
Listen/Objekte brauchen getrennte, sichere Editieroperationen; rohes YAML nur
bei eigenstaendig geklaerter Secret-/Autorisierungsgrenze. Django-HTML zuerst
moeglich, spaeter Textual oder andere UI-Adapter; keine verpflichtende SPA/
Node-Toolchain. Accessibility, Lokalisierung und sichere Fehlertexte gehoeren
zum Vertrag. UI-Features erst dokumentieren, wenn Code und Tests vorhanden sind.

## Identitaet, Sicherheit und Offline-Betrieb

Konfiguration, menschliche Identitaet und Maschine/Federation sind getrennte
Verantwortungen. Der Core implementiert keine Login- oder Rollenverwaltung.
Django-Hosts erzwingen aktive Adminrechte und CSRF; ia3-Gateway erzwingt lokale
Session, Transport und CSRF, isoliert seine Python-Bridge und lehnt ungeklaerte
Stage-/Startup-Konstellationen ab. Proxy-Vertrauen nicht aus Forwarded-Headern
erfinden. Offline-Dateibedienung bleibt moeglich, nicht gleichbedeutend mit
unauthentifiziertem Webzugriff.

**Vorhandene Identity-Arbeit:** getrennte App-Endpunkte und ia3-Bestands-Outbox
mit periodischem Versand zum Master. Das ist keine generische Config-
Synchronisation, keine vollstaendige Eventqueue und kein Nachweis sicherer
Produktionsintegration.

**Zukuenftig zu klaeren:** lokale Admin-Bootstrap-/Recovery-Regeln,
Widerruf/Rotation, Herkunft und Signaturen, Offline-Aenderungsjournal mit
expliziter Konfliktentscheidung, minimaler Sync-Umfang und Abgrenzung lokaler
Rollen vom Master. Passwoerter/Tokens/DSNs nicht automatisch federieren;
Identitaets-Sync nicht als Ersatz fuer Transport-/Serviceauth verwenden.

## Federation und dienstuebergreifender Vertrag

**Heute:** kein Wizard-Federationsprotokoll. Secrets, Host-Ports, private Pfade
und DB-Node-Einstellungen bleiben lokal. Eine gemeinsame Federation-ID
transportiert keine Config und authentifiziert allein keine Identitaet.

**Idee:** versionierte, nicht geheime Config-Artefakte mit klarer Eigentuemerschaft
(zentraler Default vs Host-Override), kompatiblem Schema, Provenienz, signierter
Freigabe, Dry-run und Opt-in-Apply. Offline-Konflikte explizit, nie last-write-wins
fuer Sicherheits-/Node-Felder. Go-/Python-Loader sollten erst durch gemeinsame
Konformitaetsfixtures (Merge, Listen, null, Selector, Env, Schema, Runtime)
angeglichen werden; parallel laufende Dienste muessen denselben Vertrag
nachweislich konsumieren. Ein Betreiber-Flag ist kein Konformitaetstest.

## Packaging- und Integrationsroadmap (offen)

1. Aktuellen Core/Editor-Vertrag und Fehlersemantik stabilisieren; unit- und
   Host-Integrationstests einschliesslich Auth, CSRF, Permissions, Konflikten,
   Maskierung, Remove und tatsaechlicher Laufzeitwirkung nachweisen.
2. Extras `cli` und `django` getrennt halten; saubere Installations-/Wheel-Tests
   ohne zufaellige editable Imports. Eine lokal deklarierte 0.2.0 ist kein
   Nachweis einer veroeffentlichten oder auf allen Hosts installierten Version.
3. Host-Resolution-Plaene und Schema-Validierungsgrenzen vereinheitlichen;
   ki-core-Gesamtvalidierung sowie ia3-Pfad-/Env-Divergenzen bewusst migrieren.
4. Bestehende Textual-Settings und Alt-kicli nur mit Migrations-/Kompatibilitaets-
   Tests anschliessen; keine implizite Umstellung bestehender Credentials.
5. Danach Origins/Preview/Backup, optionale groessere UI und erst nach eigener
   Sicherheits-/Konsistenzkonzeption Federation/Offline-Apply ausbauen.

Diese Reihenfolge ist ein Konzept, keine zugesagte Releaseplanung.
App-Repos behalten Betriebshinweise und projektspezifische Auth-/Deployment-
Anleitungen; generische YAML-Engineering-Ideen werden hier zentral gepflegt.
