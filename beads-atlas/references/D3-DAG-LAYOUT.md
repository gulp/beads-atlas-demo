# d3-dag layout contract

Load this before changing the layout engine, quality presets, graph construction, routing, or d3-dag version assumptions.

## Known-good upstream shape

Verified 2026-08-19 against `erikbrinkman/d3-dag` 1.2.2 (MIT). Primary sources:

- repository: `https://github.com/erikbrinkman/d3-dag`
- package metadata: `https://github.com/erikbrinkman/d3-dag/blob/main/package.json`
- current examples: `docs-src/examples-app.tsx`
- optimal decross implementation: `src/sugiyama/decross/opt.ts`
- two-layer decross implementation: `src/sugiyama/decross/two-layer.ts`

The viewer imports:

```js
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
import * as dag from "https://cdn.jsdelivr.net/npm/d3-dag@1/+esm";
```

`@1` intentionally tracks the compatible d3-dag major requested for this viewer. If a future 1.x release breaks the known-good calls, verify against the primary repository before changing the template; do not reconstruct API names from memory.

## Graph construction

Current d3-dag uses `graphConnect()` cleanly for edge data:

```js
const connect = dag.graphConnect()
  .sourceId(d => d.source)
  .targetId(d => d.target)
  .nodeDatum(id => id)
  .single(true);
```

Atlas adds a self-pair carrying `__single` for every visible node so isolated nodes exist in the graph. `single(true)` turns equal source/target pairs into single nodes instead of self-loop errors. Those synthetic links are discarded when drawing edges.

## Sugiyama presets

The standard presets must be bounded and usable on ordinary Beads graphs:

### Fast

```js
sugiyama()
  .layering(layeringLongestPath())
  .decross(decrossDfs())
  .coord(coordGreedy())
```

Use for large graphs or rapid interaction.

### Balanced

```js
sugiyama()
  .layering(layeringSimplex())
  .decross(decrossTwoLayer())
  .coord(coordSimplex())
```

Default.

### Precise

```js
sugiyama()
  .layering(layeringSimplex())
  .decross(decrossTwoLayer().passes(64))
  .coord(coordQuad())
```

"Precise" means **more bounded heuristic work**, not global optimal crossing minimization.

## Why standard presets must not use `decrossOpt()`

`decrossOpt()` solves an NP-complete crossing-minimization problem with an integer/LP model. d3-dag intentionally estimates the generated optimization variables/constraints and throws when the layered graph is likely too expensive.

Visible issue count is not a valid guard. Sugiyama inserts internal nodes for long edges, so a modest-looking 40-node issue graph can generate an optimization model beyond the safety threshold.

Do not fix this by using:

```js
decrossOpt().check("slow")
decrossOpt().check("oom")
```

Those settings weaken the library's protection and can turn a visible error into a browser freeze or crash.

If a future user explicitly asks for an experimental optimal mode, make it a separate, clearly dangerous opt-in for tiny graphs, retain d3-dag's default safety check, catch its failure, and never call it "Precise".

## Fallback invariant

Quality fallback is:

```text
Precise -> Balanced -> Fast
Balanced -> Fast
Fast -> fail visibly
```

Every attempt must reconstruct a **fresh graph** with `connect(linksData)`. Layout operators mutate graph coordinates; retrying a cheaper operator on a graph partially touched by a failed expensive operator makes fallback state-dependent and difficult to trust.

If fallback occurs, report the effective mode in the status bar/toast. Never silently label a Balanced result as Precise.

## Direction and node size

Atlas supports LR and TB orientation by transforming coordinates after layout. Node-size accessors must remain consistent with orientation and the viewer's actual card dimensions, or routing will clip through nodes.

## Runtime limitations

`d3-dag` is a layout engine, not a graph viewer. D3 owns SVG rendering, arrows, pan/zoom, minimap, hover, selection, and fit-to-screen.
