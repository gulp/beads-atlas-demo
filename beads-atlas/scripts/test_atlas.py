#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Regression tests for the Beads Atlas builder and graph semantics."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("atlas.py")
spec = importlib.util.spec_from_file_location("beads_atlas_cli", SCRIPT)
assert spec and spec.loader
atlas = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = atlas
spec.loader.exec_module(atlas)

ROOT = SCRIPT.parent.parent
ASSETS = ROOT / "assets"


class GraphParsingTests(unittest.TestCase):
    def test_generic_edges_keep_declared_direction(self) -> None:
        text = (ASSETS / "sample-generic.json").read_text()
        model = atlas.parse_graph(text)
        self.assertEqual(model.format, "generic")
        self.assertIn(atlas.Edge("spec", "api", "generic"), model.edges)

    def test_beads_blocks_and_hierarchy_render_prerequisite_to_dependent(self) -> None:
        text = (ASSETS / "sample-beads.jsonl").read_text()
        model = atlas.parse_graph(text)
        self.assertIn(atlas.Edge("demo", "demo.1", "parent-child"), model.edges)
        self.assertIn(atlas.Edge("demo.1", "demo.2", "blocks"), model.edges)
        self.assertNotIn(atlas.Edge("demo.2", "demo.1", "blocks"), model.edges)

    def test_duplicate_ids_fail_loudly(self) -> None:
        text = json.dumps({"nodes": [{"id": "x"}, {"id": "x"}], "edges": []})
        with self.assertRaises(atlas.AtlasError) as ctx:
            atlas.parse_graph(text)
        self.assertEqual(ctx.exception.code, atlas.EXIT_INPUT)
        self.assertIn("duplicate", ctx.exception.message.lower())

    def test_dangling_beads_dependency_fails_loudly(self) -> None:
        text = '{"id":"a","dependencies":[{"depends_on_id":"missing","type":"blocks"}]}\n'
        with self.assertRaises(atlas.AtlasError) as ctx:
            atlas.parse_graph(text)
        self.assertIn("missing issue", ctx.exception.message.lower())

    def test_cycle_is_detected_without_deleting_edges(self) -> None:
        payload = atlas.layered_fixture(3, 2, True)
        model = atlas.parse_graph(json.dumps(payload))
        summary = atlas.graph_summary(model)
        self.assertTrue(summary["cycles"]["all"]["cyclic"])
        self.assertGreaterEqual(len(summary["cycles"]["all"]["path"]), 3)

    def test_long_chain_and_long_cycle_do_not_depend_on_python_recursion_limit(self) -> None:
        chain = atlas.parse_graph(json.dumps(atlas.chain_fixture(5000, False)))
        self.assertIsNone(atlas.find_cycle(chain.ids, chain.edges))
        cyclic = atlas.parse_graph(json.dumps(atlas.chain_fixture(1500, True)))
        cycle = atlas.find_cycle(cyclic.ids, cyclic.edges)
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])

    def test_ready_work_uses_blocks_not_parent_child(self) -> None:
        model = atlas.parse_graph((ASSETS / "sample-beads.jsonl").read_text())
        self.assertEqual(atlas.ready_ids(model), ["demo.1"])


class BuildValidationTests(unittest.TestCase):
    def test_build_escapes_script_terminator_without_changing_runtime_source(self) -> None:
        source = json.dumps({
            "nodes": [{"id": "a", "label": "</script><script>alert(1)</script>"}],
            "edges": [],
        }) + "\n"
        model = atlas.parse_graph(source)
        html = atlas.build_html(model, template=atlas.DEFAULT_TEMPLATE, source_name="x")
        self.assertNotIn('"</script><script>alert(1)</script>"', html)
        embedded = atlas.extract_js_constant(html, "BUNDLED_JSONL")
        self.assertEqual(embedded, source)

    def test_template_precise_preset_is_bounded_and_has_fallback(self) -> None:
        template = atlas.DEFAULT_TEMPLATE.read_text()
        self.assertIn("dag.decrossTwoLayer().passes(64)", template)
        self.assertNotRegex(template, r"\bdag\.decrossOpt\s*\(")
        self.assertIn("['precise','balanced','fast']", template)
        self.assertIn("const candidate=connect(linksData)", template)
        self.assertNotIn("function dfs(u)", template)
        self.assertIn("frames=[[start,0]]", template)

    def test_build_and_validate_sample(self) -> None:
        source_path = ASSETS / "sample-beads.jsonl"
        model = atlas.parse_graph(source_path.read_text())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "atlas.html"
            out.write_text(atlas.build_html(model, template=atlas.DEFAULT_TEMPLATE, source_name="sample"))
            result = atlas.validate_html(out, str(source_path), "no")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["source_match"])
        self.assertEqual(result["embedded"]["nodes"], 4)

    def test_unexpanded_template_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "template.html"
            out.write_text(atlas.DEFAULT_TEMPLATE.read_text())
            with self.assertRaises(atlas.AtlasError) as ctx:
                atlas.validate_html(out, None, "no")
        self.assertEqual(ctx.exception.code, atlas.EXIT_VALIDATE)


class FixtureTests(unittest.TestCase):
    def test_layered_fixture_size(self) -> None:
        payload = atlas.layered_fixture(12, 10, False)
        self.assertEqual(len(payload["nodes"]), 120)
        model = atlas.parse_graph(json.dumps(payload))
        self.assertFalse(atlas.graph_summary(model)["cycles"]["all"]["cyclic"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Run Beads Atlas regression tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:\n  uv run scripts/test_atlas.py\n  uv run scripts/test_atlas.py -v\n\nExit codes:\n  0  all tests pass\n  1  one or more tests fail\n  2  CLI usage error\n""",
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="show each test name")
    args = ap.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
