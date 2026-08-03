"""The shipped schemas must actually accept the shipped examples.

Other checkers re-declare required fields in Python, so a schema and its
examples can drift apart while both still pass. These tests pin the executable
relationship: every schema is declared with at least one instance, the
instances validate, and the checker fails rather than passing quietly when
something breaks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import schema_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HAVE_JSONSCHEMA = schema_check.Draft202012Validator is not None


class ManifestTests(unittest.TestCase):
    def test_every_schema_is_declared_with_an_instance(self) -> None:
        manifest = json.loads((ROOT / "validation/schema-instances.json").read_text("utf-8"))
        declared = manifest["instances"]
        on_disk = {p.name for p in (ROOT / "schemas").glob("*.schema.json")}
        self.assertEqual(
            on_disk,
            set(declared),
            "every schema needs an entry in validation/schema-instances.json",
        )
        for name, instances in declared.items():
            with self.subTest(schema=name):
                self.assertTrue(instances, f"{name} must declare at least one instance")
                for relative in instances:
                    self.assertTrue((ROOT / relative).exists(), f"missing instance {relative}")

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate object key"):
                schema_check.load_json(path)


@unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
class ExecutionTests(unittest.TestCase):
    def test_repository_passes(self) -> None:
        self.assertEqual(schema_check.check(ROOT), [])

    def _copy_repo(self, tmp: str) -> Path:
        dest = Path(tmp) / "repo"
        for part in ("schemas", "examples", "validation"):
            shutil.copytree(ROOT / part, dest / part)
        return dest

    def _probe_errors(self, schema: object, instance: object) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/probe.json").write_text(
                json.dumps(instance), encoding="utf-8"
            )
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {"instances": {"probe.schema.json": ["examples/probe.json"]}}
                ),
                encoding="utf-8",
            )
            return schema_check.check(repo)

    def test_example_violating_its_schema_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "examples/standalone-clip/project-state.json"
            data = json.loads(target.read_text("utf-8"))
            data["schema_version"] = 1  # declared as a string
            target.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("schema_version" in e for e in errors), errors)

    def test_schema_requiring_a_field_no_example_has_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            target = repo / "schemas/take-review.schema.json"
            schema = json.loads(target.read_text("utf-8"))
            schema["required"] = list(schema["required"]) + ["field_no_example_has"]
            target.write_text(json.dumps(schema), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("field_no_example_has" in e for e in errors), errors)

    def test_undeclared_schema_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            manifest = repo / "validation/schema-instances.json"
            data = json.loads(manifest.read_text("utf-8"))
            del data["instances"]["take-review.schema.json"]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("has no entry" in e for e in errors), errors)

    def test_declared_schema_that_does_not_exist_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._copy_repo(tmp)
            manifest = repo / "validation/schema-instances.json"
            data = json.loads(manifest.read_text("utf-8"))
            data["instances"]["ghost.schema.json"] = ["examples/standalone-clip/project-state.json"]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            errors = schema_check.check(repo)
            self.assertTrue(any("ghost.schema.json" in e for e in errors), errors)

    def test_external_schema_references_fail_without_opening_the_network(self) -> None:
        for keyword in ("$ref", "$dynamicRef"):
            with self.subTest(keyword=keyword), tempfile.TemporaryDirectory() as tmp:
                repo = self._copy_repo(tmp)
                target = repo / "schemas/take-review.schema.json"
                schema = json.loads(target.read_text("utf-8"))
                schema.setdefault("properties", {})["network_probe"] = {
                    keyword: "https://example.invalid/remote.schema.json"
                }
                target.write_text(json.dumps(schema), encoding="utf-8")
                with mock.patch("urllib.request.urlopen") as urlopen:
                    errors = schema_check.check(repo)
                self.assertTrue(
                    any("external or unresolved $ref/$dynamicRef" in e for e in errors),
                    errors,
                )
                urlopen.assert_not_called()

    def test_local_fragment_references_remain_supported(self) -> None:
        self.assertEqual(
            schema_check.external_reference_paths(
                {"$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/value"}
            ),
            [],
        )

    def test_opaque_local_target_must_pass_the_metaschema_before_activation(self) -> None:
        schema = {
            "type": "object",
            "properties": {"optional": {"$ref": "#/opaque/target"}},
            "opaque": {"target": {"type": 7}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        invalid_targets = schema_check.invalid_local_reference_targets(schema)
        self.assertEqual(len(invalid_targets), 1)
        self.assertIn("$/properties/optional/$ref", invalid_targets[0])
        self.assertIn("$/opaque/target", invalid_targets[0])

        # The root metaschema ignores the unknown `opaque` container, and the
        # fixture can omit the optional branch. The static reference audit must
        # still reject the invalid runtime target.
        schema_check.Draft202012Validator.check_schema(schema)
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception):
            list(validator.iter_errors({"optional": "activated"}))
        errors = self._probe_errors(schema, {})
        self.assertTrue(any("local $ref/$dynamicRef target" in error for error in errors))

    def test_opaque_local_target_rejects_primitives_and_lists_but_accepts_booleans(self) -> None:
        for target in (7, ["not", "a", "schema"]):
            schema = {
                "type": "object",
                "properties": {"optional": {"$ref": "#/opaque/target"}},
                "opaque": {"target": target},
            }
            with self.subTest(target=target):
                findings = schema_check.invalid_local_reference_targets(schema)
                self.assertEqual(len(findings), 1)
                self.assertIn("not an object or boolean schema", findings[0])
                self.assertTrue(
                    any(
                        "local $ref/$dynamicRef target" in error
                        for error in self._probe_errors(schema, {})
                    )
                )

        for target in (True, False):
            schema = {
                "type": "object",
                "properties": {"optional": {"$ref": "#/opaque/target"}},
                "opaque": {"target": target},
            }
            with self.subTest(target=target):
                self.assertEqual(schema_check.invalid_local_reference_targets(schema), [])
                self.assertEqual(self._probe_errors(schema, {}), [])
                validator = schema_check.Draft202012Validator(
                    schema,
                    registry=schema_check.Registry(
                        retrieve=schema_check.refuse_schema_retrieval
                    ),
                )
                activated_errors = list(
                    validator.iter_errors({"optional": "activated"})
                )
                self.assertEqual(len(activated_errors), 0 if target else 1)

    def test_opaque_invalid_target_is_checked_within_a_nested_id_resource(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "optional": {
                    "$id": "https://nested.invalid/resource",
                    "$ref": "#/opaque/target",
                    "opaque": {"target": {"type": 7}},
                }
            },
        }
        invalid_targets = schema_check.invalid_local_reference_targets(schema)
        self.assertEqual(len(invalid_targets), 1)
        self.assertIn("$/properties/optional/opaque/target", invalid_targets[0])
        self.assertTrue(
            any(
                "local $ref/$dynamicRef target" in error
                for error in self._probe_errors(schema, {})
            )
        )

    def test_every_nonlocal_reference_form_is_rejected_in_schema_positions(self) -> None:
        references = (
            "https://example.invalid/schema",
            "http://example.invalid/schema",
            "//example.invalid/schema",
            "?alternate-schema",
            "file:///tmp/schema.json",
            "urn:example:remote-schema",
            "relative/schema.json",
        )
        for keyword in ("$ref", "$dynamicRef"):
            for reference in references:
                with self.subTest(keyword=keyword, reference=reference):
                    self.assertEqual(
                        schema_check.external_reference_paths(
                            {"properties": {"value": {keyword: reference}}}
                        ),
                        [f"$/properties/value/{keyword}"],
                    )

    def test_invalid_reference_types_are_left_to_the_schema_metaschema(self) -> None:
        from jsonschema.exceptions import SchemaError

        for keyword in ("$ref", "$dynamicRef"):
            for invalid in (7, [], {}):
                schema = {"properties": {"value": {keyword: invalid}}}
                with self.subTest(keyword=keyword, invalid=invalid):
                    self.assertEqual(schema_check.external_reference_paths(schema), [])
                    with self.assertRaises(SchemaError):
                        schema_check.Draft202012Validator.check_schema(schema)

    def test_empty_reference_is_same_resource_and_recursive(self) -> None:
        schema = {
            "type": "object",
            "properties": {"child": {"$ref": ""}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({"child": {"child": {}}})), [])

    def test_local_dynamic_anchor_recursion_remains_supported(self) -> None:
        schema = {
            "$dynamicAnchor": "node",
            "type": "object",
            "properties": {"child": {"$dynamicRef": "#node"}},
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({"child": {"child": {}}})), [])

    def test_local_plain_anchor_resolution_remains_supported(self) -> None:
        schema = {
            "$defs": {
                "value": {
                    "$anchor": "value",
                    "type": "integer",
                }
            },
            "$ref": "#value",
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors(1)), [])

    def test_unresolved_optional_local_pointer_fails_static_audit(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "optional": {"$ref": "#/$defs/missing"},
            },
            "$defs": {},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/$ref"],
        )
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception) as unresolved:
            list(validator.iter_errors({"optional": 1}))
        self.assertIn("missing", str(unresolved.exception))

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_unresolved_plain_anchor_is_a_finding(self) -> None:
        schema = {
            "type": "object",
            "properties": {"optional": {"$dynamicRef": "#missing"}},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/$dynamicRef"],
        )

    def test_reference_shaped_literal_data_is_not_treated_as_a_subschema(self) -> None:
        literal = {
            "$ref": "https://example.invalid/literal-ref",
            "$dynamicRef": "relative-literal-ref",
        }
        schema = {
            "const": literal,
            "enum": [literal],
            "default": literal,
            "examples": [literal],
        }
        self.assertEqual(schema_check.external_reference_paths(schema), [])
        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors(literal)), [])

    def test_local_pointer_into_opaque_data_makes_that_target_an_active_schema(self) -> None:
        schema = {
            "$ref": "#/%63onst",
            "const": {"$ref": "https://example.invalid/active-via-pointer"},
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/const/$ref"],
        )

    def test_nested_id_pointer_uses_the_embedded_resource_root(self) -> None:
        """An optional property must not hide retrieval behind a nested resource scope."""
        schema = {
            "type": "object",
            "properties": {
                "optional": {
                    "$id": "https://example.invalid/embedded",
                    "$ref": "#/const",
                    "const": {"$ref": "https://example.invalid/remote"},
                }
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/properties/optional/const/$ref"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            # The property is deliberately absent: fixture execution alone
            # would never resolve the external reference.
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_outer_pointer_into_nested_resource_keeps_nested_scope(self) -> None:
        """Crossing a nested `$id` must rebase refs in an activated opaque value."""
        schema = {
            "$id": "https://outer.invalid/root",
            "type": "object",
            "properties": {
                "optional": {"$ref": "#/$defs/embedded/const"}
            },
            "$defs": {
                "embedded": {
                    "$id": "https://embedded.invalid/res",
                    "const": {
                        "$ref": "#/const/hidden",
                        "hidden": {"$ref": "https://remote.invalid/x"},
                    },
                }
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/$defs/embedded/const/hidden/$ref"],
        )

        validator = schema_check.Draft202012Validator(
            schema,
            registry=schema_check.Registry(retrieve=schema_check.refuse_schema_retrieval),
        )
        self.assertEqual(list(validator.iter_errors({})), [])
        with self.assertRaises(Exception) as retrieval:
            list(validator.iter_errors({"optional": 1}))
        self.assertIn("remote.invalid", str(retrieval.exception))

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schemas").mkdir()
            (repo / "examples").mkdir()
            (repo / "validation").mkdir()
            (repo / "schemas/probe.schema.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )
            (repo / "examples/omitted.json").write_text("{}", encoding="utf-8")
            (repo / "validation/schema-instances.json").write_text(
                json.dumps(
                    {
                        "instances": {
                            "probe.schema.json": ["examples/omitted.json"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors = schema_check.check(repo)
        self.assertTrue(
            any("external or unresolved $ref/$dynamicRef" in error for error in errors),
            errors,
        )

    def test_literal_id_on_pointer_path_is_not_a_resource_boundary(self) -> None:
        """A `$id` inside opaque instance data must not rebase an active schema."""
        schema = {
            "$id": "https://outer.invalid/root",
            "$ref": "#/const/target",
            "const": {
                "$id": "https://literal.invalid/not-a-schema-resource",
                "target": {"$ref": "#/default/hidden"},
            },
            "default": {
                "hidden": {"$ref": "https://remote.invalid/inverse"}
            },
        }
        self.assertEqual(
            schema_check.external_reference_paths(schema),
            ["$/default/hidden/$ref"],
        )

    def test_registry_retrieval_callback_always_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "external schema retrieval is disabled"):
            schema_check.refuse_schema_retrieval("https://example.invalid/schema")


class DependencyTests(unittest.TestCase):
    def test_missing_dependency_fails_rather_than_skipping(self) -> None:
        """A silent skip would let CI report success while validating nothing."""
        environment = {
            "PYTHONPATH": "",
            "PATH": os.environ.get("PATH", "") if os.name == "nt" else "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # CPython on Windows needs the OS root to initialize its secure random
        # provider; removing it tests process startup rather than dependency
        # handling (Fatal _Py_HashRandomization_Init, exit 1).
        for name in ("SYSTEMROOT", "WINDIR"):
            if name in os.environ:
                environment[name] = os.environ[name]
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/schema_check.py"), str(ROOT)],
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertIn(result.returncode, (0, 2), result.stdout + result.stderr)
        if result.returncode == 2:
            self.assertIn("requires jsonschema", result.stderr)


if __name__ == "__main__":
    unittest.main()
