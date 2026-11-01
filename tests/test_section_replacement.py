import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from yaml_cfg_wizard import (
    ConfigResolver,
    deep_merge,
    merge_with_replacement,
    strip_replace_markers,
)


class TestSectionReplacement(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def resolver(self, **kwargs):
        return ConfigResolver(
            replace_sections=True, env={"IGNORED": "true"}, **kwargs,
        )

    def test_replacement_is_opt_in_and_inputs_are_not_mutated(self):
        base = {"stack": {"services": {"old": {}}}, "other": 1}
        override = {"stack": {"__replace__": True, "services": {"new": {}}}}
        original = deepcopy((base, override))
        self.assertIn("old", deep_merge(base, override)["stack"]["services"])
        result = strip_replace_markers(merge_with_replacement(base, override))
        self.assertEqual(result, {"stack": {"services": {"new": {}}}, "other": 1})
        self.assertEqual((base, override), original)
        path = self.write("ordinary.yaml", "section:\n  __replace__: true\n")
        self.assertEqual(
            ConfigResolver(defaults=[path], env={"IGNORED": "true"}).resolve(),
            {"section": {"__replace__": True}},
        )

    def test_replacement_across_files_in_every_layer_group(self):
        for group in ("defaults", "profiles", "stage", "runtime"):
            with self.subTest(group=group):
                a = self.write("a.yaml", "stack:\n  services:\n    old: {}\n")
                b = self.write(
                    "b.yml", "stack:\n  __replace__: true\n  services:\n    new: {}\n",
                )
                result = self.resolver(**{group: [a, b]}).resolve()
                self.assertEqual(result, {"stack": {"services": {"new": {}}}})

    def test_replacement_across_files_in_every_directory(self):
        for group in ("defaults_dir", "profiles_dir", "stages_dir"):
            with self.subTest(group=group):
                self.write(f"{group}/a.yaml", "stack:\n  services:\n    old: {}\n")
                self.write(
                    f"{group}/b.yml",
                    "stack:\n  __replace__: true\n  services:\n    new: {}\n",
                )
                result = self.resolver(**{group: self.root / group}).resolve()
                self.assertEqual(result, {"stack": {"services": {"new": {}}}})

    def test_later_runtime_and_environment_add_values_after_replacement(self):
        defaults = self.write("defaults.yaml", "stack:\n  services:\n    old: {}\n")
        stage = self.write("stage.yaml", "stack:\n  __replace__: true\n  services: {}\n")
        runtime = self.write("runtime.yaml", "stack:\n  services:\n    worker: {}\n")
        result = ConfigResolver(
            defaults=[defaults], stage=[stage], runtime_file=runtime,
            replace_sections=True, env={"APP_STACK__TARGET": "local"},
        ).resolve()
        self.assertEqual(result, {"stack": {"services": {"worker": {}}, "target": "local"}})

    def test_markers_survive_composition_but_not_validation_or_output(self):
        path = self.write("override.yaml", "stack:\n  __replace__: true\n  services: {}\n")
        schema = self.write(
            "schema.yaml",
            "type: object\nproperties:\n  stack:\n    type: object\n"
            "    additionalProperties: false\n    properties:\n      services:\n"
            "        type: object\n",
        )
        resolver = self.resolver(defaults=[path], schema_file=schema)
        intermediate = resolver.resolve(preserve_replace_markers=True)
        self.assertTrue(intermediate["stack"]["__replace__"])
        self.assertEqual(resolver.resolve(), {"stack": {"services": {}}})
        composed = merge_with_replacement({"stack": {"old": 1}}, intermediate)
        self.assertEqual(strip_replace_markers(composed), {"stack": {"services": {}}})

    def test_nested_markers_empty_sections_lists_and_false(self):
        base = {"section": {"old": 1}, "other": {"old": 2}, "items": [1]}
        override = {
            "section": {"__replace__": True},
            "other": {"__replace__": False, "new": 3},
            "items": [{"nested": {"__replace__": True, "value": 4}}],
        }
        self.assertEqual(strip_replace_markers(merge_with_replacement(base, override)), {
            "section": {}, "other": {"old": 2, "new": 3},
            "items": [{"nested": {"value": 4}}],
        })

    def test_non_boolean_markers_fail_even_in_new_subtrees(self):
        for value in ("true", 1, None):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "__replace__ must be a boolean"),
            ):
                merge_with_replacement({}, {"new": {"__replace__": value}})

    def test_root_and_nested_replacement_keep_unrelated_sections(self):
        base = {"section": {"nested": {"old": 1}, "keep": 2}, "other": 3}
        result = strip_replace_markers(merge_with_replacement(base, {
            "section": {"nested": {"__replace__": True, "new": 4}},
        }))
        self.assertEqual(result, {
            "section": {"nested": {"new": 4}, "keep": 2}, "other": 3,
        })
        self.assertEqual(
            strip_replace_markers(merge_with_replacement(base, {"__replace__": True})),
            {},
        )

    def test_runtime_candidate_hook_and_type_boundaries_are_preserved(self):
        class CandidateResolver(ConfigResolver):
            def _runtime_layers(self):
                return [{"stack": {"__replace__": True, "services": {"candidate": {}}}}]

        defaults = self.write("defaults.yaml", "stack:\n  services:\n    old: {}\n")
        result = CandidateResolver(
            defaults=[defaults], replace_sections=True,
            env={"APP_STACK__TARGET": "local"},
        ).resolve()
        self.assertEqual(result, {
            "stack": {"services": {"candidate": {}}, "target": "local"},
        })
        runtime = self.write("runtime.yaml", "stack: replaced\n")
        extra = self.write("extra.yaml", "stack:\n  services:\n    rebuilt: {}\n")
        result = self.resolver(
            defaults=[defaults], runtime_file=runtime, runtime=[extra],
        ).resolve()
        self.assertEqual(result, {"stack": {"services": {"rebuilt": {}}}})
