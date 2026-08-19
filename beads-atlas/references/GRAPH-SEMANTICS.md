# Graph semantics

Load this before changing input normalization, edge direction, readiness, critical-path logic, or lens definitions.

## Accepted inputs

Atlas intentionally accepts two families:

1. **Beads exports** — `issues.jsonl`, a JSON array of issue records, or one issue object.
2. **Generic DAG JSON** — exactly the useful interoperable shape:

```json
{
  "nodes": [{"id": "node1", "label": "Node 1"}],
  "edges": [{"source": "node1", "target": "node2"}]
}
```

Generic edges preserve the caller's declared `source -> target` direction. Missing, empty, or duplicate node IDs are input errors. An edge naming a missing node is an input error; never fabricate a node to make the graph render.

## Beads storage direction vs visual direction

A Beads dependency row is stored on the issue and names `depends_on_id`. The stored shape is therefore conceptually:

```text
issue -> depends on -> other issue
```

That direction is useful for mutation APIs, but backwards for an execution visualization. Atlas projects each dependency as:

```text
depends_on_id -> issue_id
```

This makes prerequisite/parent/origin flow left-to-right or top-to-bottom.

Relationship semantics:

- **`blocks`** — the issue is blocked by `depends_on_id`; render **blocker -> blocked issue**. This is the only relationship that determines ready work and execution critical paths.
- **`parent-child`** — the issue is a child of `depends_on_id`; render **parent -> child**. This is hierarchy only and never makes a leaf unready.
- **`discovered-from`** — work/verification was derived from another issue; render **origin -> discovered issue** for provenance flow.
- **`related`** — a meaningful non-blocking association. Atlas renders the same dependency projection for consistency, but the arrow is not an execution prerequisite. Related edges may legitimately make the `All` projection cyclic.
- **unknown types** — preserve the dependency projection and type label. Do not silently coerce to `blocks`.

## Lenses

For Beads:

- **Plan** = `blocks` + `parent-child`.
- **Execute** = `blocks` only.
- **Structure** = `parent-child` only.
- **All** = every relation type.

For generic graphs, **All** is the primary lens and all edges keep declared direction.

## Cycles

`d3-dag` requires a DAG. Atlas must not obtain one by deleting edges.

For each selected projection:

1. detect a cycle before layout;
2. show the cycle path in the UI/error state;
3. refuse that projection until the user changes lens/filter/data.

A cyclic `All` lens does not imply the Beads execution graph is wrong; `related` or provenance relations can introduce cycles while `blocks` remains acyclic.

## Ready work

An issue is ready when:

- its status is `open`; and
- every incoming `blocks` edge comes from a blocker whose status is resolved (`closed` or `rejected`).

Hierarchy, related, and discovered-from edges do not affect readiness.

## Critical paths

Execution critical-path analysis uses **`blocks` only**. Do not mix hierarchy depth into execution criticality; a deeply nested epic is not automatically a bottleneck.

## Data-integrity philosophy

Fail loudly on structural incompleteness:

- duplicate issue/node IDs;
- missing node references;
- malformed dependency arrays;
- dependencies missing `depends_on_id`.

A viewer that silently drops malformed edges produces a beautiful false plan.
