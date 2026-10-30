"""Framework-free editor regression tests."""

import os
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import yaml

from yaml_cfg_wizard import deep_merge
from yaml_cfg_wizard.editor import ConflictError, Editor, EditorError, Field, ValidationError


SCHEMA = {"type": "object", "properties": {"node": {
    "type": "object", "properties": {
        "name": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "url": {"type": "string"},
    },
}}}


class TestConfigEditing(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.target = self.root / "runtime" / "runtime.yaml"
        self.upper = {}
        self.lower = {"node": {"name": "inherited", "port": 8000}}
        self.editor = Editor(
            {"runtime": self.target},
            [Field("node.name", "Name"), Field("node.port", "Port"), Field("node.url", "URL")],
            lambda _file, candidate: deep_merge(deep_merge(self.lower, candidate), self.upper),
            SCHEMA,
        )

    def save(self, changes=None, remove=()):
        return self.editor.save("runtime", self.editor.snapshot("runtime").revision, changes or {}, remove)

    def write(self, text):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(text, encoding="utf-8")

    def row(self, snapshot, path):
        return next(row for row in snapshot.rows if row["path"] == path)

    def test_create_private_file_and_empty_vs_removal(self):
        snapshot = self.save({"node.name": ""})
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        self.assertEqual(self.row(snapshot, "node.name")["override"], "")
        snapshot = self.editor.save("runtime", snapshot.revision, {}, remove=["node.name"])
        self.assertFalse(self.row(snapshot, "node.name")["overridden"])
        self.assertEqual(self.row(snapshot, "node.name")["effective"], "inherited")

    def test_private_mode_hook_reuses_atomic_transaction(self):
        class PrivateEditor(Editor):
            def _file_mode(self, target, raw):
                return 0o600

        self.write("node:\n  name: old\n")
        self.target.chmod(0o644)
        private_editor = PrivateEditor(
            self.editor.files, self.editor.fields, self.editor.resolve, self.editor.schema,
        )
        private_editor.save(
            "runtime", private_editor.snapshot("runtime").revision, {"node.name": "private"},
        )
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        self.assertEqual(yaml.safe_load(self.target.read_text())["node"]["name"], "private")

    def test_secret_values_never_exposed_and_unrelated_keys_preserved(self):
        self.write("secret: private\nnode:\n  password: private\n  name: old\n")
        snapshot = self.save({"node.port": 8001})
        self.assertNotIn("private", repr(snapshot))
        self.assertEqual(yaml.safe_load(self.target.read_text())["node"]["password"], "private")

    def test_unsafe_url_hidden_and_rejected(self):
        self.write("node:\n  url: https://user:private@host/path?token=private\n")
        self.assertNotIn("private", repr(self.editor.snapshot("runtime")))
        with self.assertRaises(ValidationError):
            self.save({"node.url": "https://user:private@host"})

    def test_raw_and_effective_validation(self):
        self.upper = {"node": {"port": 9000}}
        with self.assertRaises(ValidationError):
            self.save({"node.port": "wrong"})
        self.assertFalse(self.target.exists())
        self.upper = {"node": {"port": 0}}
        with self.assertRaises(ValidationError):
            self.save({"node.name": "valid"})
        self.assertFalse(self.target.exists())

    def test_higher_layer_unsafe_url_rejects_unrelated_save(self):
        self.upper = {"node": {"url": "https://user:private@host"}}
        with self.assertRaises(ValidationError):
            self.save({"node.name": "valid"})
        self.assertFalse(self.target.exists())

    def test_field_schema_root_references_are_validated(self):
        schema = {"definitions": {"port": {"type": "integer", "minimum": 1}},
                  "properties": {"node": {"properties": {"port": {"$ref": "#/definitions/port"}}}}}
        self.editor = Editor(
            {"runtime": self.target}, [Field("node.port", "Port")],
            lambda _f, c: deep_merge(c, {"node": {"port": 10}}), schema,
        )
        with self.assertRaises(ValidationError):
            self.save({"node.port": 0})
        self.save({"node.port": 12})

    def test_null_is_a_value_not_removal(self):
        schema = {"properties": {"node": {"properties": {"name": {"type": ["string", "null"]}}}}}
        self.editor = Editor(
            {"runtime": self.target}, [Field("node.name", "Name")],
            lambda _f, c: deep_merge(self.lower, c), schema,
        )
        snapshot = self.save({"node.name": None})
        self.assertTrue(self.row(snapshot, "node.name")["overridden"])
        self.assertIsNone(self.row(snapshot, "node.name")["override"])

    def test_removal_validates_inherited_value(self):
        self.write("node:\n  port: 9000\n")
        self.lower["node"]["port"] = 0
        before = self.target.read_bytes()
        with self.assertRaises(ValidationError):
            self.save(remove=["node.port"])
        self.assertEqual(self.target.read_bytes(), before)

    def test_file_and_field_allowlists(self):
        for file_id in ("../creds.yaml", str(self.target), "creds"):
            with self.assertRaises(EditorError):
                self.editor.snapshot(file_id)
        with self.assertRaises(EditorError):
            self.save({"node.password": "x"})
        with self.assertRaises(EditorError):
            self.editor.save("runtime", "", {"node.name": "x"}, ["node.name"])
        with self.assertRaises(ValidationError):
            self.save({"node.name": {"password": "private"}})
        for path in ("node.sync_shared_secret", "node.api_key", "node.postgres_dsn"):
            with self.assertRaises(ValueError):
                Editor({"runtime": self.target}, [Field(path, path)], lambda _f, c: c, {})

    def test_file_parent_and_lock_symlinks_rejected(self):
        outside = self.root / "outside.yaml"
        outside.write_text("node: {}\n")
        self.target.parent.mkdir()
        self.target.symlink_to(outside)
        with self.assertRaises(EditorError):
            self.editor.snapshot("runtime")
        self.target.unlink()
        lock = self.target.with_name(self.target.name + ".editor.lock")
        lock.symlink_to(outside)
        with self.assertRaises(EditorError):
            self.save({"node.name": "x"})
        lock.unlink()
        self.target.parent.rmdir()
        self.target.parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(EditorError):
            self.editor.snapshot("runtime")

    def test_stale_revision_and_external_edits(self):
        revision = self.editor.snapshot("runtime").revision
        self.write("node:\n  name: external\n")
        with self.assertRaises(ConflictError):
            self.editor.save("runtime", revision, {"node.name": "lost"})
        self.assertIn("external", self.target.read_text())

    def test_parallel_saves_have_one_winner(self):
        revision = self.editor.snapshot("runtime").revision

        def attempt(name):
            try:
                self.editor.save("runtime", revision, {"node.name": name})
                return "saved"
            except ConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("one", "two")))
        self.assertCountEqual(results, ["saved", "conflict"])

    def test_replace_failure_keeps_original_and_cleans_temporary(self):
        self.write("node:\n  name: old\n")
        before = self.target.read_bytes()
        with patch("yaml_cfg_wizard.editor.os.replace", side_effect=OSError("private")):
            with self.assertRaises(EditorError) as error:
                self.save({"node.name": "new"})
        self.assertNotIn("private", str(error.exception))
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(list(self.target.parent.glob(".runtime.yaml.*")), [])

    def test_existing_permissions_preserved(self):
        self.write("node: {}\n")
        os.chmod(self.target, 0o640)
        self.save({"node.name": "new"})
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)

    def test_aliases_do_not_modify_unlisted_paths(self):
        self.write("node: &node\n  name: old\nother: *node\n")
        self.save({"node.name": "new"})
        data = yaml.safe_load(self.target.read_text())
        self.assertEqual(data["other"]["name"], "old")
        self.assertEqual(data["node"]["name"], "new")

    def test_safe_parser_and_resolver_errors(self):
        self.write("password: [private\n")
        with self.assertRaises(EditorError) as error:
            self.editor.snapshot("runtime")
        self.assertNotIn("private", str(error.exception))
        self.target.unlink()
        self.editor.resolve = lambda _f, _c: (_ for _ in ()).throw(ValueError("private"))
        with self.assertRaises(ValidationError) as error:
            self.save({"node.name": "valid"})
        self.assertNotIn("private", str(error.exception))

    def test_size_and_root_mapping_limits(self):
        self.write("[]")
        with self.assertRaises(EditorError):
            self.editor.snapshot("runtime")
        self.write("x" * (1024 * 1024 + 1))
        with self.assertRaises(EditorError):
            self.editor.snapshot("runtime")


if __name__ == "__main__":
    unittest.main()
