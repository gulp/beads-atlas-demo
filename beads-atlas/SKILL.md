---
name: beads-atlas
description: >-
  Build and validate a powerful single-file HTML explorer for Beads issues.jsonl or generic directed graphs using D3 v7 and d3-dag Sugiyama layout. Use when the user asks to visualize, explore, inspect, map, trace, or analyze a Beads dependency graph, wants an interactive DAG HTML artifact, or asks for a reusable graph viewer from {nodes, edges} JSON.
license: MIT
compatibility: >-
  Helper scripts require Python 3.11+ and uv (stdlib only). Generated HTML imports D3 v7 and d3-dag 1.x from jsDelivr at runtime, so browser startup requires network access or cached modules.
---

# Beads Atlas

Generate an implementation-planning instrument, not a decorative graph. Preserve Beads execution semantics, fail loudly on malformed graph data, use bounded Sugiyama quality presets, and return one HTML artifact that can also accept new JSON/JSONL by drag/drop.

## Inputs

- **Source graph** — preferably the live `.beads/issues.jsonl`; also accepts a JSON array/single Beads record or generic `{nodes, edges}` JSON.
- **Output path** — default to a scratch/artifact path unless the user explicitly wants the viewer committed into a repo.
- **Customization request** — optional visual/product changes. If absent, reuse the bundled proven template rather than redesigning it.

Do not declare positional skill arguments for these inputs: source/output/customization are optional and may be free text. Infer an unambiguous source from the current repo or ask only when multiple plausible sources exist.

## Goal

A generated HTML file that:

- embeds the exact requested source graph;
- renders a directed Sugiyama DAG with D3;
- distinguishes hierarchy from execution blockers;
- supports search, filtering, focus tracing, ready/critical/bottleneck analysis, inspector, minimap, pan/zoom, and fit-to-screen;
- never uses global optimal decrossing as an ordinary quality preset;
- reports cycles or layout fallback explicitly rather than deleting edges or silently downgrading;
- passes source-integrity and static JavaScript validation;
- has browser-runtime smoke evidence when the environment can actually load the CDN modules.

## Bundled resources

### CLI

Use `scripts/atlas.py` for deterministic work. Resolve it from the loaded skill root; do not recreate its parsing/escaping pipeline in shell.

```bash
uv run <skill-root>/scripts/atlas.py --help
uv run <skill-root>/scripts/atlas.py inspect <source>
uv run <skill-root>/scripts/atlas.py build <source> -o <output>
uv run <skill-root>/scripts/atlas.py validate <output> --source <source>
```

The CLI emits JSON on stdout and diagnostics on stderr. It refuses destructive overwrite unless `--force` is explicit.

### Regression suite

```bash
uv run <skill-root>/scripts/test_atlas.py -v
```

Run this whenever the template or builder changes, not for every unchanged-template regeneration.

### Template and samples

- `assets/beads-atlas-template.html` — canonical viewer template.
- `assets/sample-beads.jsonl` — small Beads semantic fixture.
- `assets/sample-generic.json` — small generic DAG fixture.

## References

Load references at the point where they are useful rather than copying them into this file:

- `references/GRAPH-SEMANTICS.md` — **read before changing dependency direction, lenses, ready work, critical paths, or input normalization**.
- `references/D3-DAG-LAYOUT.md` — **read before changing d3-dag APIs, layout presets, routing, graph construction, or version assumptions**.
- `references/VIEWER-DESIGN.md` — **read when the user asks for a redesigned/custom viewer rather than a straight regeneration**.
- `references/GOTCHAS.md` — **read when layout/data/runtime behavior is surprising before replacing libraries or weakening checks**.
- `references/VALIDATION.md` — **read after changing deterministic logic/template, and for browser smoke/dogfood procedure**.

## Steps

### 1. Ground the source

If the source lives in a repository, use the live repository file rather than a stale Project Source copy. Read the repo's live `AGENTS.md` first if present before writing anything into that repo.

Resolve the source in this order:

1. path explicitly supplied by the user;
2. current repo `.beads/issues.jsonl` when there is exactly one obvious target;
3. attached/uploaded graph file;
4. ask only if the target remains genuinely ambiguous.

Do not mutate Beads to visualize them. This skill is read-only with respect to issue state.

**Artifacts**: exact source path or uploaded source bytes.

**Success criteria**:
- one source is identified;
- its bytes are available locally;
- any repo-specific instructions that govern output location are known.

### 2. Inspect before rendering

Run:

```bash
uv run <skill-root>/scripts/atlas.py inspect <source>
```

Read `references/GRAPH-SEMANTICS.md` when the input is Beads or the summary reports a cycle.

Treat these as hard failures, not warnings:

- empty input;
- duplicate IDs;
- generic edges referencing missing nodes;
- Beads dependencies referencing missing issues;
- malformed dependency structures.

A cyclic `All` lens can be legitimate when non-blocking relations exist; a cyclic execution (`blocks`) projection is a real graph problem and must be surfaced.

**Artifacts**: structured graph summary with format, node/edge/relation counts, source SHA-256, lens cycles, ready set, and blocking longest path.

**Success criteria**:
- inspection exits 0;
- source counts/hash are recorded;
- no structural incompleteness was silently dropped.

### 3. Choose straight regeneration vs viewer change

**Straight regeneration** — use the bundled template unchanged when the user wants the proven Atlas experience on new data.

**Viewer change** — before editing the template:

1. read `references/VIEWER-DESIGN.md`;
2. read `references/D3-DAG-LAYOUT.md` for any layout/edge-routing change;
3. read `references/GOTCHAS.md` for the failure pattern nearest the requested change.

Preserve the user's actual graph-exploration goal. Do not turn a small request into a dashboard rewrite.

**Rules**:
- `blocks` ready/critical semantics never inherit from hierarchy.
- Issue text remains escaped/untrusted.
- No standard preset may call `dag.decrossOpt()`.
- Precise remains bounded two-layer decrossing with fresh-graph fallback.
- No-silent-cycle and no-silent-fallback behavior remain visible.

**Success criteria**:
- the intended template behavior is explicit;
- any changed invariant has a corresponding reference/test update.

### 4. Build the artifact

Run the documented builder; prefer a scratch path such as `/tmp/...` or the environment's artifact directory:

```bash
uv run <skill-root>/scripts/atlas.py build <source> \
  --name "<human dataset name>" \
  -o <output.html>
```

Use `--dry-run` first when output location/overwrite is uncertain. Use `--force` only when replacing an output is intentional.

The builder escapes HTML-sensitive characters inside the embedded JavaScript string while preserving byte-identical runtime source data. Do not replace this with hand-built interpolation.

**Artifacts**: one HTML file plus the builder's JSON report.

**Success criteria**:
- build exits 0;
- post-build validation reports `PASS`;
- embedded source summary matches Step 2.

### 5. Validate deterministic correctness

For a final deliverable, run validation explicitly even though build already performs it:

```bash
uv run <skill-root>/scripts/atlas.py validate <output.html> --source <source>
```

This gate checks source-byte identity, required CDN imports, Sugiyama/graphConnect contract, bounded Precise configuration, fallback marker, absence of a `dag.decrossOpt()` call, template expansion, and JavaScript module syntax when Node is available.

If the template or CLI changed in this task, also run:

```bash
uv run <skill-root>/scripts/test_atlas.py -v
uv run <skill-root>/scripts/atlas.py fixture --shape layered --layers 12 --width 10 -o /tmp/atlas-stress.json --force
uv run <skill-root>/scripts/atlas.py build /tmp/atlas-stress.json -o /tmp/atlas-stress.html --force
uv run <skill-root>/scripts/atlas.py validate /tmp/atlas-stress.html --source /tmp/atlas-stress.json
```

Read `references/VALIDATION.md` for negative-cycle and dogfood checks.

**Rules**:
- a missing validator is not a pass;
- do not hand-patch generated HTML to make validation green—fix the template/builder;
- if Node is unavailable under `auto`, report that syntax validation was skipped by environment rather than claiming it ran.

**Success criteria**:
- generated artifact validation is PASS;
- changed deterministic logic has a green regression suite and >100-node stress build;
- source hash/count integrity is preserved.

### 6. Browser smoke when capability exists

Static checks do not prove the jsDelivr modules can load or the SVG interaction works. When a browser with network access is available, follow `references/VALIDATION.md` and exercise at least:

- Balanced and Precise;
- LR/TB + fit-to-screen;
- node selection/focus;
- Plan/Execute/Structure/All lenses;
- one >100-node fixture;
- a deliberate cycle projection.

If the environment cannot load jsDelivr, stop claiming at **static validation passed; browser-runtime smoke unavailable**. Do not substitute a different renderer/library merely to manufacture a local green run unless the user asks to change the architecture.

**Success criteria**:
- runtime smoke passes with environment/version noted; **or**
- the exact runtime limitation is disclosed without weakening static gates.

### 7. Deliver

Return the HTML artifact directly. Include a short verification summary: source format/counts/hash, artifact hash, static validation status, and browser-runtime status.

Do not bury the file link under implementation notes.

**Success criteria**:
- the user has a direct artifact link/path;
- verification claims distinguish what actually ran from what was unavailable.

## Non-negotiable invariants

1. **Visual direction is semantic.** Beads dependency storage direction is not automatically the useful display direction; see `GRAPH-SEMANTICS.md`.
2. **No silent edge deletion.** Cycles and dangling references are surfaced.
3. **No `decrossOpt()` in standard quality modes.** "Precise" is bounded, not exponential.
4. **Fresh graph per fallback attempt.** Failed layout state never contaminates the next attempt.
5. **Source text is untrusted.** Escape before HTML rendering and before embedding inside a script element.
6. **Single-file does not mean offline-vendored.** The standard artifact still loads D3/d3-dag from jsDelivr.
7. **Static validation is not browser validation.** Report them separately.
8. **Generated output is disposable; generator/template are authoritative.** Fix those, then regenerate.

## Maintenance trigger

If a future d3-dag 1.x change breaks Atlas:

1. reproduce with the regression/stress commands;
2. read `references/D3-DAG-LAYOUT.md`;
3. verify the current API against the upstream repository/official docs;
4. update the template and the regression test that pins the changed contract;
5. dogfood against a known-good source before releasing the new skill/archive.

Do not guess new operator names or suppress upstream safety checks from memory.
