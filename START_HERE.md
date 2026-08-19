# START HERE — Beads Atlas repository demo

This repository is the complete clean-room demonstration package.

There is **no bootstrap archive and no second transport layer**. Do not use the old Gist or GitHub Release asset. Work only from the ordinary files on this repository's default branch.

## Hard boundary

Use repository/GitHub reading tools to obtain the files below. If your execution environment needs filesystem copies, create those copies from the repository file contents you already fetched. Do not switch to shell `curl`, `wget`, guessed IPs, release downloads, Gist lookups, web-search reconstruction, prior conversations, or project caches.

If you cannot obtain an exact repository file through the available repository tools, stop and report that specific transport limitation instead of improvising another retrieval path.

## Required repository files

- `issues.jsonl` — the intended 41-issue Beads demonstration corpus.
- `SHA256SUMS` — integrity manifest for the materialized package.
- `verify.py` — local package verifier when the repository files are available on disk.
- `beads-atlas/SKILL.md` — the operative skill contract.
- `beads-atlas/scripts/atlas.py` — deterministic inspector / builder / validator.
- the remaining files under `beads-atlas/` — template, references, fixtures, and regression support used by the skill.

Do not substitute the small sample files under `beads-atlas/assets/` for the repository-root `issues.jsonl`.

## 1. Read the skill first

Read `beads-atlas/SKILL.md` completely before running the demo. Follow its requirements and stop gates. In particular, use its own CLI rather than recreating graph parsing, escaping, dependency semantics, layout logic, or validation ad hoc.

## 2. Verify locally when files are materialized

From the repository root:

```bash
python3 verify.py
```

Expected package result includes:

```text
BEADS_ATLAS_DEMO_VERIFY=PASS
records=41
```

A failed integrity check is a hard stop.

## 3. Inspect the real demo corpus

```bash
uv run beads-atlas/scripts/atlas.py inspect issues.jsonl
```

Record the source format, node/edge/relation counts, SHA-256, cycle status, ready set, and blocking longest path reported by the skill.

## 4. Build with the bundled deterministic implementation

Prefer the normal ChatGPT artifact location:

```bash
uv run beads-atlas/scripts/atlas.py build issues.jsonl \
  --name "Beads Atlas demo" \
  -o /mnt/data/beads-atlas-demo.html
```

Do not hand-edit the generated HTML.

## 5. Validate explicitly

```bash
uv run beads-atlas/scripts/atlas.py validate \
  /mnt/data/beads-atlas-demo.html \
  --source issues.jsonl
```

Static validation must pass before delivery. If the environment cannot load the generated viewer's jsDelivr modules in a browser, report exactly what the skill specifies: static validation passed; browser-runtime smoke unavailable. Do not weaken or replace the renderer merely to manufacture a browser-green result.

## 6. Deliver

Surface `/mnt/data/beads-atlas-demo.html` as the finished artifact. Report concisely:

- source format/counts/hash;
- artifact hash;
- static validation status;
- browser-runtime status.

The purpose of this repository is to test one simple bootstrap boundary: **one normal public GitHub repository URL, then ordinary repository files only**.
