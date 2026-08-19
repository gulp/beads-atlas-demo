# Validation and dogfood

Load this after modifying `assets/beads-atlas-template.html`, `scripts/atlas.py`, or when a generated artifact is important enough to ship rather than merely preview.

## Fast gate for every generated artifact

```bash
uv run scripts/atlas.py inspect <source>
uv run scripts/atlas.py build <source> -o <output>
uv run scripts/atlas.py validate <output> --source <source>
```

`build` validates automatically unless `--no-validate` is explicitly requested. Do not use `--no-validate` for a final deliverable.

The validator checks at minimum:

- requested D3 v7 and d3-dag 1.x ESM imports;
- Sugiyama + graphConnect viewer contract;
- bounded Precise preset (`decrossTwoLayer().passes(64)`);
- no standard `dag.decrossOpt()` call;
- Precise -> Balanced -> Fast fallback marker;
- no unexpanded template tokens;
- embedded graph parses structurally;
- optional source is byte-identical after JS embedding/unescaping;
- JavaScript module syntax with `node --check` when Node is available/requested.

## Regression suite after skill/template changes

```bash
uv run scripts/test_atlas.py -v
```

The suite includes positive and negative cases for edge direction, duplicates, dangling dependencies, cycles, ready work, script-terminator escaping, layout preset safeguards, source matching, and a >100-node fixture.

## Stress fixtures

Generate rather than hand-writing wide/deep cases:

```bash
uv run scripts/atlas.py fixture --shape layered --layers 12 --width 10 -o /tmp/atlas-120.json
uv run scripts/atlas.py build /tmp/atlas-120.json -o /tmp/atlas-120.html
uv run scripts/atlas.py validate /tmp/atlas-120.html --source /tmp/atlas-120.json
```

Negative cycle case:

```bash
uv run scripts/atlas.py fixture --shape layered --layers 8 --width 8 --cycle -o /tmp/atlas-cycle.json
uv run scripts/atlas.py inspect /tmp/atlas-cycle.json
```

`inspect` should report the cycle. Building is still allowed because Atlas itself is responsible for surfacing cyclic projections interactively.

## Browser smoke when available

A static gate cannot prove CDN/browser runtime. When a browser with network access is available:

1. open the generated file;
2. wait until the "Loading the DAG engine…" notice disappears;
3. switch Fast -> Balanced -> Precise and confirm all render;
4. switch LR/TB and fit-to-screen;
5. click a node, inspect upstream/downstream, then double-click focus;
6. exercise Plan/Execute/Structure/All lenses;
7. load the 120-node fixture and repeat Precise;
8. load a cycle fixture and verify a visible cycle diagnostic rather than a missing edge;
9. paste/drop generic JSON and verify direct source->target arrows.

Record browser/version and whether modules were loaded from network/cache.

If the environment cannot reach jsDelivr, say **runtime smoke unavailable**. Do not call static syntax validation a browser pass.

## Dogfood against a known-good hand-built artifact

When changing the generator/template:

1. preserve the previous accepted HTML at a literal `/tmp` path;
2. regenerate from the exact same source using the documented command;
3. compare the outer HTML/template frame separately from the embedded `BUNDLED_JSONL` data line;
4. explain every frame difference;
5. fix the generator/template rather than hand-patching generated HTML.

For embedded source, compare via `atlas.py validate --source` rather than a textual diff of the giant JS string.
