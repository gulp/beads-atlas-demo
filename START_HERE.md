# START HERE — Beads Atlas Demonstration

This ZIP is the complete demonstration package.

## Hard boundary

Everything required is already inside this directory.

After the ZIP itself has been downloaded, **do not use the network**:
do not browse, search, fetch URLs, invoke GitHub/Gist connectors, run curl/wget,
or recover files from prior conversations/projects.

If a local step fails, stop and report that local failure. Do not attempt a
network workaround.

## 1. Verify the package

Run:

```bash
python3 verify.py
```

Expected result:

```text
BEADS_ATLAS_DEMO_VERIFY=PASS
records=41
```

## 2. Read the skill

Read `beads-atlas/SKILL.md` completely and treat it, together with its bundled
support files, as the operative task specification.

## 3. Demonstrate it

Use the **top-level `issues.jsonl` in this package** as the demonstration input.

Do not substitute bundled samples, another project, prior conversation state,
or reconstructed graph logic.

Use the skill's own deterministic builder / graph logic / validator.

If the skill permits choosing the output location, prefer:

```text
/mnt/data/beads-atlas-demo.html
```

Run the skill's validator on the produced HTML, then surface the finished HTML
as a downloadable artifact and report validation concisely.

## Source integrity

Source skill archive SHA-256:

```text
a6f52ba7e6df39166d6686f4d7553f0c21165dc4be82f51dba79e0ed68d40c69
```

Demonstration corpus:

```text
records=41
sha256=832655f821891bcfb460bd0914b70427a17d5cd9f2169bc689e748713a3c10fb
```
