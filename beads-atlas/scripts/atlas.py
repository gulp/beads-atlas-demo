#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Build, inspect, validate, and stress-test Beads Atlas single-file DAG viewers."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_WRITE = 4
EXIT_VALIDATE = 5
EXIT_EXTERNAL = 6

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "beads-atlas-template.html"

D3_URL = "https://cdn.jsdelivr.net/npm/d3@7/+esm"
D3_DAG_URL = "https://cdn.jsdelivr.net/npm/d3-dag@1/+esm"

HELP_EPILOG = r"""
Examples:
  uv run scripts/atlas.py inspect .beads/issues.jsonl
  uv run scripts/atlas.py build .beads/issues.jsonl -o /tmp/beads-atlas.html
  uv run scripts/atlas.py build graph.json --name "Release graph" --dry-run
  uv run scripts/atlas.py validate /tmp/beads-atlas.html --source .beads/issues.jsonl
  uv run scripts/atlas.py fixture --shape layered --layers 12 --width 10 -o /tmp/stress.json
  uv run scripts/atlas.py fixture --shape layered --layers 8 --width 8 --cycle -o /tmp/cycle.json

Output:
  JSON objects go to stdout. Human diagnostics go to stderr.

Exit codes:
  0  success
  2  CLI usage error
  3  input graph is unreadable or invalid
  4  template/output/write error
  5  generated HTML failed Atlas validation
  6  requested external validator (for example Node) is unavailable or failed
"""


class AtlasError(Exception):
    def __init__(self, code: int, message: str, *, expected: str | None = None, example: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.expected = expected
        self.example = example


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str


@dataclass
class GraphModel:
    format: str
    nodes: list[dict[str, Any]]
    edges: list[Edge]
    raw_text: str
    sha256: str

    @property
    def ids(self) -> set[str]:
        return {str(n["id"]) for n in self.nodes}


def fail(error: AtlasError) -> int:
    print(f"atlas: error: {error.message}", file=sys.stderr)
    print(f"atlas: expected: {error.expected or 'valid input/output for the selected subcommand'}", file=sys.stderr)
    print(f"atlas: example: {error.example or 'uv run scripts/atlas.py --help'}", file=sys.stderr)
    return error.code


def read_text(path: str) -> tuple[str, str]:
    if path == "-":
        text = sys.stdin.read()
        return text, "stdin"
    p = Path(path)
    if not p.is_file():
        raise AtlasError(EXIT_INPUT, f"input file does not exist: {p}", expected="a Beads JSONL/JSON file or generic graph JSON", example="uv run scripts/atlas.py inspect .beads/issues.jsonl")
    try:
        return p.read_text(encoding="utf-8"), p.name
    except OSError as exc:
        raise AtlasError(EXIT_INPUT, f"cannot read {p}: {exc}") from exc


def nonempty_id(value: Any, context: str) -> str:
    if value is None or not str(value).strip():
        raise AtlasError(EXIT_INPUT, f"{context} is missing a non-empty id")
    return str(value)


def duplicates(items: Iterable[str]) -> list[str]:
    counts = collections.Counter(items)
    return sorted(k for k, n in counts.items() if n > 1)


def parse_jsonl(text: str) -> list[Any]:
    rows: list[Any] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AtlasError(EXIT_INPUT, f"JSONL line {lineno} is invalid: {exc.msg}", expected="one complete JSON object per non-empty line") from exc
    return rows


def parse_graph(text: str) -> GraphModel:
    raw = text
    stripped = text.strip()
    if not stripped:
        raise AtlasError(EXIT_INPUT, "input is empty")

    parsed: Any = None
    parsed_ok = False
    try:
        parsed = json.loads(stripped)
        parsed_ok = True
    except json.JSONDecodeError:
        pass

    if parsed_ok and isinstance(parsed, dict) and isinstance(parsed.get("nodes"), list) and isinstance(parsed.get("edges"), list):
        nodes: list[dict[str, Any]] = []
        ids: list[str] = []
        for i, node in enumerate(parsed["nodes"], 1):
            if not isinstance(node, dict):
                raise AtlasError(EXIT_INPUT, f"generic node {i} is not an object")
            nid = nonempty_id(node.get("id"), f"generic node {i}")
            ids.append(nid)
            nodes.append(node)
        dup = duplicates(ids)
        if dup:
            raise AtlasError(EXIT_INPUT, f"duplicate generic node id(s): {', '.join(dup[:8])}")
        known = set(ids)
        edges: list[Edge] = []
        for i, edge in enumerate(parsed["edges"], 1):
            if not isinstance(edge, dict):
                raise AtlasError(EXIT_INPUT, f"generic edge {i} is not an object")
            source = nonempty_id(edge.get("source"), f"generic edge {i} source")
            target = nonempty_id(edge.get("target"), f"generic edge {i} target")
            missing = [x for x in (source, target) if x not in known]
            if missing:
                raise AtlasError(EXIT_INPUT, f"generic edge {i} references missing node id(s): {', '.join(missing)}")
            edges.append(Edge(source, target, str(edge.get("type") or "generic")))
        return GraphModel("generic", nodes, edges, raw, hashlib.sha256(raw.encode()).hexdigest())

    if parsed_ok and isinstance(parsed, list):
        records = parsed
    elif parsed_ok and isinstance(parsed, dict) and parsed.get("id") is not None:
        records = [parsed]
    elif parsed_ok:
        raise AtlasError(EXIT_INPUT, "JSON input is neither generic {nodes, edges} nor a Beads record/array")
    else:
        records = parse_jsonl(stripped)

    if not records:
        raise AtlasError(EXIT_INPUT, "no Beads records were found")
    if not all(isinstance(r, dict) for r in records):
        raise AtlasError(EXIT_INPUT, "every Beads JSONL/array entry must be an object")

    ids = [nonempty_id(r.get("id"), f"Beads record {i}") for i, r in enumerate(records, 1)]
    dup = duplicates(ids)
    if dup:
        raise AtlasError(EXIT_INPUT, f"duplicate Beads issue id(s): {', '.join(dup[:8])}")
    known = set(ids)
    edges: list[Edge] = []
    dangling: list[str] = []

    for record in records:
        issue_id = str(record["id"])
        deps = record.get("dependencies") or []
        if not isinstance(deps, list):
            raise AtlasError(EXIT_INPUT, f"issue {issue_id} has a non-array dependencies field")
        for j, dep in enumerate(deps, 1):
            if not isinstance(dep, dict):
                raise AtlasError(EXIT_INPUT, f"issue {issue_id} dependency {j} is not an object")
            other = nonempty_id(dep.get("depends_on_id"), f"issue {issue_id} dependency {j}")
            typ = str(dep.get("type") or "generic")
            if other not in known:
                dangling.append(f"{issue_id} -> {other} ({typ})")
                continue
            # Beads stores the issue on the left and what it depends on on the right.
            # Atlas renders useful flow direction: prerequisite/origin/parent -> issue.
            edges.append(Edge(other, issue_id, typ))

    if dangling:
        preview = "; ".join(dangling[:6]) + ("…" if len(dangling) > 6 else "")
        raise AtlasError(EXIT_INPUT, f"Beads dependencies reference missing issue id(s): {preview}", expected="a complete issues.jsonl export with every referenced issue present")

    return GraphModel("beads", records, edges, raw, hashlib.sha256(raw.encode()).hexdigest())


def edge_types(model: GraphModel) -> collections.Counter[str]:
    return collections.Counter(e.type for e in model.edges)


def lens_edges(model: GraphModel, lens: str) -> list[Edge]:
    if model.format == "generic" or lens == "all":
        return list(model.edges)
    if lens == "plan":
        return [e for e in model.edges if e.type in {"blocks", "parent-child"}]
    if lens == "execution":
        return [e for e in model.edges if e.type == "blocks"]
    if lens == "structure":
        return [e for e in model.edges if e.type == "parent-child"]
    raise AtlasError(EXIT_USAGE, f"unknown lens: {lens}", expected="plan, execution, structure, or all")


def find_cycle(ids: set[str], edges: list[Edge]) -> list[str] | None:
    """Return one directed cycle path without recursion-depth dependence."""
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in edges:
        if e.source in ids and e.target in ids:
            if e.source == e.target:
                return [e.source, e.target]
            adj[e.source].append(e.target)
    for values in adj.values():
        values.sort()

    color: dict[str, int] = {i: 0 for i in ids}
    for start in sorted(ids):
        if color[start] != 0:
            continue
        color[start] = 1
        path = [start]
        positions = {start: 0}
        frames: list[list[Any]] = [[start, 0]]
        while frames:
            node, index = frames[-1]
            neighbors = adj[node]
            if index >= len(neighbors):
                frames.pop()
                color[node] = 2
                positions.pop(node, None)
                path.pop()
                continue
            nxt = neighbors[index]
            frames[-1][1] += 1
            if color[nxt] == 0:
                color[nxt] = 1
                positions[nxt] = len(path)
                path.append(nxt)
                frames.append([nxt, 0])
            elif color[nxt] == 1:
                return path[positions[nxt] :] + [nxt]
    return None


def longest_path(ids: set[str], edges: list[Edge]) -> list[str]:
    indeg = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in edges:
        adj[e.source].append(e.target)
        indeg[e.target] += 1
    q = collections.deque(sorted(i for i in ids if indeg[i] == 0))
    topo: list[str] = []
    while q:
        n = q.popleft()
        topo.append(n)
        for nxt in adj[n]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)
    if len(topo) != len(ids):
        return []
    dist = {i: 0 for i in ids}
    prev: dict[str, str] = {}
    for n in topo:
        for nxt in adj[n]:
            if dist[n] + 1 > dist[nxt]:
                dist[nxt] = dist[n] + 1
                prev[nxt] = n
    end = max(topo, key=lambda i: dist[i], default=None)
    if end is None:
        return []
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def ready_ids(model: GraphModel) -> list[str]:
    if model.format != "beads":
        return []
    by_id = {str(n["id"]): n for n in model.nodes}
    incoming_blockers: dict[str, list[str]] = collections.defaultdict(list)
    for e in model.edges:
        if e.type == "blocks":
            incoming_blockers[e.target].append(e.source)
    ready: list[str] = []
    for nid, node in by_id.items():
        if str(node.get("status", "open")) != "open":
            continue
        blockers = incoming_blockers.get(nid, [])
        unresolved = [b for b in blockers if str(by_id[b].get("status", "open")) not in {"closed", "rejected"}]
        if not unresolved:
            ready.append(nid)
    return sorted(ready)


def graph_summary(model: GraphModel) -> dict[str, Any]:
    ids = model.ids
    lenses = ["all"] if model.format == "generic" else ["plan", "execution", "structure", "all"]
    cycles: dict[str, Any] = {}
    for lens in lenses:
        cycle = find_cycle(ids, lens_edges(model, lens))
        cycles[lens] = {"cyclic": bool(cycle), "path": cycle or []}
    block_path = longest_path(ids, [e for e in model.edges if e.type == "blocks"])
    return {
        "format": model.format,
        "nodes": len(model.nodes),
        "edges": len(model.edges),
        "edge_types": dict(sorted(edge_types(model).items())),
        "sha256": model.sha256,
        "cycles": cycles,
        "ready_count": len(ready_ids(model)) if model.format == "beads" else None,
        "ready_ids": ready_ids(model)[:25] if model.format == "beads" else [],
        "blocking_longest_path_edges": max(0, len(block_path) - 1),
        "blocking_longest_path": block_path[:50],
        "blocking_longest_path_truncated": len(block_path) > 50,
    }


def js_string_literal(value: str) -> str:
    # JSON strings are valid JS strings. Escape HTML-sensitive code points so an
    # issue containing </script> can never terminate the module script early.
    return (
        json.dumps(value, ensure_ascii=True)
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("&", r"\u0026")
    )


def default_output(input_path: str) -> Path:
    if input_path == "-":
        return Path.cwd() / "beads-atlas.html"
    p = Path(input_path)
    stem = p.stem
    if stem == "issues":
        stem = "beads"
    return Path.cwd() / f"{stem}-atlas.html"


def build_html(model: GraphModel, *, template: Path, source_name: str) -> str:
    try:
        text = template.read_text(encoding="utf-8")
    except OSError as exc:
        raise AtlasError(EXIT_WRITE, f"cannot read template {template}: {exc}") from exc
    tokens = {
        "__BEADS_ATLAS_BUNDLED_JSONL__": js_string_literal(model.raw_text),
        "__BEADS_ATLAS_BUNDLED_NAME__": js_string_literal(source_name),
    }
    for token, replacement in tokens.items():
        count = text.count(token)
        if count != 1:
            raise AtlasError(EXIT_WRITE, f"template token {token} occurs {count} times; expected exactly once")
        text = text.replace(token, replacement)
    return text


def extract_js_constant(html: str, name: str) -> str:
    prefix = f"const {name} = "
    for line in html.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped.endswith(";"):
            literal = stripped[len(prefix) : -1]
            try:
                value = json.loads(literal)
            except json.JSONDecodeError as exc:
                raise AtlasError(EXIT_VALIDATE, f"{name} is not a JSON-decodable JS string literal: {exc.msg}") from exc
            if not isinstance(value, str):
                raise AtlasError(EXIT_VALIDATE, f"{name} did not decode to a string")
            return value
    raise AtlasError(EXIT_VALIDATE, f"HTML does not define {name}")


def extract_module_script(html: str) -> str:
    match = re.search(r'<script\s+type=["\']module["\']\s*>(.*?)</script>', html, flags=re.S | re.I)
    if not match:
        raise AtlasError(EXIT_VALIDATE, "HTML has no <script type=\"module\"> block")
    return match.group(1)


def validate_html(html_path: Path, source_path: str | None, node_check: str) -> dict[str, Any]:
    if not html_path.is_file():
        raise AtlasError(EXIT_VALIDATE, f"HTML file does not exist: {html_path}")
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AtlasError(EXIT_VALIDATE, f"cannot read HTML {html_path}: {exc}") from exc

    findings: list[str] = []
    required_snippets = [
        f'import * as d3 from "{D3_URL}";',
        f'import * as dag from "{D3_DAG_URL}";',
        "dag.sugiyama()",
        "dag.graphConnect()",
        "dag.decrossTwoLayer().passes(64)",
        "['precise','balanced','fast']",
        "d3.zoom()",
        "fitGraph(false)",
    ]
    for snippet in required_snippets:
        if snippet not in html:
            findings.append(f"missing required snippet: {snippet}")
    if re.search(r"\bdag\.decrossOpt\s*\(", html):
        findings.append("standard viewer code still calls dag.decrossOpt(); precise mode must remain bounded")
    if "__BEADS_ATLAS_BUNDLED_JSONL__" in html or "__BEADS_ATLAS_BUNDLED_NAME__" in html:
        findings.append("unexpanded template token remains")

    embedded = extract_js_constant(html, "BUNDLED_JSONL")
    source_name = extract_js_constant(html, "BUNDLED_NAME")
    embedded_model = parse_graph(embedded)

    source_match = None
    if source_path is not None:
        source_text, _ = read_text(source_path)
        source_match = embedded == source_text
        if not source_match:
            findings.append("embedded source is not byte-identical to --source")

    node_result: dict[str, Any] = {"requested": node_check, "ran": False, "ok": None}
    if node_check != "no":
        node = shutil.which("node")
        if node is None:
            if node_check == "yes":
                raise AtlasError(EXIT_EXTERNAL, "Node.js was requested for syntax validation but is not on PATH", expected="node >= 18 or use --node-check no")
            node_result.update({"ran": False, "ok": None, "reason": "node not found"})
        else:
            script = extract_module_script(html)
            with tempfile.TemporaryDirectory(prefix="beads-atlas-check-") as td:
                p = Path(td) / "viewer.mjs"
                p.write_text(script, encoding="utf-8")
                proc = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
            node_result.update({"ran": True, "ok": proc.returncode == 0})
            if proc.returncode != 0:
                findings.append(f"node --check failed: {(proc.stderr or proc.stdout).strip()[:500]}")

    result = {
        "status": "PASS" if not findings else "FAIL",
        "html": str(html_path),
        "html_bytes": html_path.stat().st_size,
        "html_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
        "source_name": source_name,
        "embedded": graph_summary(embedded_model),
        "source_match": source_match,
        "node_check": node_result,
        "findings": findings,
    }
    if findings:
        raise AtlasError(EXIT_VALIDATE, json.dumps(result, ensure_ascii=False))
    return result


def cmd_inspect(args: argparse.Namespace) -> dict[str, Any]:
    text, _ = read_text(args.input)
    model = parse_graph(text)
    return graph_summary(model)


def cmd_build(args: argparse.Namespace) -> dict[str, Any]:
    text, inferred_name = read_text(args.input)
    model = parse_graph(text)
    template = Path(args.template) if args.template else DEFAULT_TEMPLATE
    output = Path(args.output) if args.output else default_output(args.input)
    source_name = args.name or inferred_name
    html = build_html(model, template=template, source_name=source_name)

    result = {
        "status": "DRY_RUN" if args.dry_run else "BUILT",
        "output": str(output),
        "source_name": source_name,
        "source": graph_summary(model),
        "html_bytes": len(html.encode()),
        "template": str(template),
    }
    if args.dry_run:
        return result
    desired_bytes = html.encode("utf-8")
    if output.exists() and not args.force:
        try:
            existing = output.read_bytes()
        except OSError as exc:
            raise AtlasError(EXIT_WRITE, f"cannot read existing output {output}: {exc}") from exc
        if existing == desired_bytes:
            result["status"] = "UNCHANGED"
            result["html_sha256"] = hashlib.sha256(existing).hexdigest()
            if not args.no_validate:
                result["validation"] = validate_html(output, args.input if args.input != "-" else None, args.node_check)
            return result
        raise AtlasError(EXIT_WRITE, f"refusing to overwrite different existing output: {output}", expected="a new output path or explicit --force", example=f"uv run scripts/atlas.py build {args.input} -o {output} --force")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(desired_bytes)
    except OSError as exc:
        raise AtlasError(EXIT_WRITE, f"cannot write {output}: {exc}") from exc
    result["html_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    if not args.no_validate:
        result["validation"] = validate_html(output, args.input if args.input != "-" else None, args.node_check)
    return result


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    return validate_html(Path(args.html), args.source, args.node_check)


def layered_fixture(layers: int, width: int, cycle: bool) -> dict[str, Any]:
    if layers < 1 or width < 1:
        raise AtlasError(EXIT_USAGE, "--layers and --width must both be >= 1")
    nodes = []
    edges = []
    for layer in range(layers):
        for col in range(width):
            nid = f"L{layer:02d}N{col:02d}"
            nodes.append({"id": nid, "label": f"Layer {layer} / Node {col}", "status": "open"})
    for layer in range(layers - 1):
        for col in range(width):
            src = f"L{layer:02d}N{col:02d}"
            for delta in (0, 1):
                tgt = f"L{layer+1:02d}N{(col + delta) % width:02d}"
                edges.append({"source": src, "target": tgt, "type": "generic"})
    if cycle and layers > 1:
        edges.append({"source": f"L{layers-1:02d}N00", "target": "L00N00", "type": "generic"})
    return {"nodes": nodes, "edges": edges}


def chain_fixture(nodes_count: int, cycle: bool) -> dict[str, Any]:
    if nodes_count < 1:
        raise AtlasError(EXIT_USAGE, "--nodes must be >= 1")
    nodes = [{"id": f"N{i:03d}", "label": f"Node {i}"} for i in range(nodes_count)]
    edges = [{"source": f"N{i:03d}", "target": f"N{i+1:03d}"} for i in range(nodes_count - 1)]
    if cycle and nodes_count > 1:
        edges.append({"source": f"N{nodes_count-1:03d}", "target": "N000"})
    return {"nodes": nodes, "edges": edges}


def cmd_fixture(args: argparse.Namespace) -> dict[str, Any]:
    if args.shape == "chain":
        payload = chain_fixture(args.nodes, args.cycle)
    else:
        payload = layered_fixture(args.layers, args.width, args.cycle)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    output = Path(args.output)
    desired = text.encode("utf-8")
    status = "WROTE"
    if output.exists() and not args.force:
        existing = output.read_bytes()
        if existing == desired:
            status = "UNCHANGED"
        else:
            raise AtlasError(EXIT_WRITE, f"refusing to overwrite different existing fixture: {output}", expected="a new path or --force")
    if status != "UNCHANGED":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(desired)
    model = parse_graph(text)
    return {"status": status, "output": str(output), **graph_summary(model)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="atlas.py",
        description="Inspect graph inputs and build/validate the single-file Beads Atlas DAG viewer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "inspect", help="validate and summarize Beads JSONL/JSON or generic graph JSON",
        description="Validate graph structure and report semantics before rendering.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  atlas.py inspect .beads/issues.jsonl\n  cat graph.json | atlas.py inspect -\n\nExit codes: 0 success · 2 usage · 3 invalid input",
    )
    p.add_argument("input", help="input file, or - for stdin")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser(
        "build", help="embed a graph into the Atlas HTML template",
        description="Build one Atlas HTML file and validate it unless --no-validate is explicit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  atlas.py build .beads/issues.jsonl -o /tmp/beads-atlas.html\n  atlas.py build graph.json --name 'Release graph' --dry-run\n\nExit codes: 0 success/unchanged · 2 usage · 3 invalid input · 4 write/template · 5 validation · 6 requested external check unavailable",
    )
    p.add_argument("input", help="input file, or - for stdin")
    p.add_argument("-o", "--output", help="HTML output path (default: <input>-atlas.html in cwd)")
    p.add_argument("--name", help="human-readable dataset name shown in the viewer")
    p.add_argument("--template", help="override the bundled HTML template")
    p.add_argument("--force", action="store_true", help="allow overwriting an existing output file")
    p.add_argument("--dry-run", action="store_true", help="validate and report what would be written without creating a file")
    p.add_argument("--no-validate", action="store_true", help="skip post-build Atlas validation (not recommended)")
    p.add_argument("--node-check", choices=("auto", "yes", "no"), default="auto", help="post-build JavaScript syntax check with Node (default: auto)")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser(
        "validate", help="validate a generated Atlas HTML, optionally byte-checking its source",
        description="Check Atlas template invariants, embedded graph integrity, and optional JS syntax.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  atlas.py validate /tmp/beads-atlas.html --source .beads/issues.jsonl\n  atlas.py validate /tmp/beads-atlas.html --node-check no\n\nExit codes: 0 pass · 2 usage · 3 invalid embedded/source graph · 5 artifact validation · 6 requested Node check unavailable",
    )
    p.add_argument("html", help="Atlas HTML file")
    p.add_argument("--source", help="original graph source; embedded text must match byte-for-byte")
    p.add_argument("--node-check", choices=("auto", "yes", "no"), default="auto", help="JavaScript syntax check with Node (default: auto)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser(
        "fixture", help="generate deterministic generic DAG/cycle fixtures for smoke testing",
        description="Generate repeatable generic graph fixtures for positive and negative layout tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  atlas.py fixture --shape layered --layers 12 --width 10 -o /tmp/stress.json\n  atlas.py fixture --shape chain --nodes 40 --cycle -o /tmp/cycle.json\n\nExit codes: 0 success/unchanged · 2 usage · 4 write error",
    )
    p.add_argument("--shape", choices=("chain", "layered"), default="layered")
    p.add_argument("--nodes", type=int, default=50, help="chain node count (default: 50)")
    p.add_argument("--layers", type=int, default=10, help="layered fixture layer count (default: 10)")
    p.add_argument("--width", type=int, default=10, help="layered fixture width (default: 10)")
    p.add_argument("--cycle", action="store_true", help="add a deliberate back-edge for negative cycle testing")
    p.add_argument("-o", "--output", required=True, help="fixture JSON output path")
    p.add_argument("--force", action="store_true", help="allow overwriting an existing fixture")
    p.set_defaults(func=cmd_fixture)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = parser()
    args = ap.parse_args(argv)
    try:
        result = args.func(args)
    except AtlasError as exc:
        # validate failures may carry a structured report in message; keep stdout clean.
        return fail(exc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
