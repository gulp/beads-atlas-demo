# Gotchas and failure patterns

Load this when Atlas behaves strangely, before replacing the layout library or simplifying validation.

## Layout

### Precise throws "size of dag to decrossOpt is too large"

Cause: `decrossOpt()` was used as a normal quality preset. It is a global optimal solver with a safety check based on generated optimization complexity, not visible node count.

Fix: use `decrossTwoLayer().passes(64)` + `coordQuad()` for Precise. Preserve the fallback chain and fresh graph per attempt. See `references/D3-DAG-LAYOUT.md`.

### A 40-node graph can be "too large" for an optimal solver

Sugiyama creates internal long-edge nodes. Do not use issue count as a proxy for solver variables/constraints.

### Fallback produces bizarre coordinates

Likely cause: reusing the graph object after a failed layout attempt. Recreate it before every quality attempt.

## Data integrity

### Graph looks easier than the Beads plan

Check for silently missing dependency targets. The builder and viewer must fail on dangling references, not drop them.

### Related edges make All cyclic

Not necessarily a Beads defect. Related is non-blocking association; use Plan/Execute/Structure for DAG projections. Atlas should name the All-lens cycle rather than delete it.

### Ready count is wrong

Ready work is based only on unresolved incoming `blocks` edges. A structural parent is not a blocker. Closed/rejected blockers are resolved.

## Single-file embedding

### Issue text contains `</script>`

A JSON string embedded directly in a `<script>` can terminate the script in the HTML parser even though it is syntactically inside a JS string. `scripts/atlas.py build` escapes `<`, `>`, and `&` as JS unicode escapes while preserving the exact runtime source string. Do not replace this with naive string interpolation.

### "Self-contained" but the page is blank offline

The artifact is **single-file**, but D3 and d3-dag are intentionally ESM imports from jsDelivr. It therefore needs network access (or already-cached modules) at viewer startup. The persistent CDN notice is the diagnostic. Do not claim full offline self-containment unless dependencies are actually vendored/inlined in a future variant.

## Rendering/security

### An issue label or description creates markup

Treat this as a security defect. Escape issue text before applying limited presentation formatting. Do not use raw HTML rendering for source-controlled or user-supplied issue content.

### Arrow direction appears backwards

For Beads, stored dependency direction and visual execution direction differ. Read `references/GRAPH-SEMANTICS.md` before changing arrows.

## Validation

### HTML parses but runtime still fails

Static validation proves template shape/source integrity and JavaScript syntax, not CDN reachability or browser DOM behavior. Run a browser smoke when the environment allows CDN access. If it does not, disclose that limitation; a missing runtime validator is not a passing runtime test.

### Headless browser hangs in a sandbox

First distinguish browser failure from external-module fetch failure. Do not weaken the artifact to a different library just to make an isolated sandbox pass if the user explicitly requested the CDN architecture.

## Scope drift

### Rebuilding Atlas turns into a dashboard rewrite

Start from the bundled template and make the smallest change that serves the user's graph-exploration question. Preserve the proven semantics/layout safeguards unless the user deliberately changes the product goal.
