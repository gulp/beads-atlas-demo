# Beads Atlas — repository-native ChatGPT demo

This repository is deliberately **uncompressed and text-addressable**.
There is no Gist bootstrap, release download, archive extraction, or child URL to discover.

## Fresh ChatGPT test

Give a new ChatGPT conversation exactly this:

```text
Study https://github.com/gulp/beads-atlas-demo and follow instructions
```

## Instructions for ChatGPT

Treat this public repository as the complete clean-room task package.

1. Do not use prior conversations, projects, memory-derived artifacts, Gists, or release assets.
2. Stay inside the ordinary files on the repository's default branch.
3. Read `START_HERE.md`.
4. Read `beads-atlas/SKILL.md` completely and follow it as the operative skill contract.
5. Use the repository-root `issues.jsonl` as the demonstration input; it contains the intended 41-issue corpus.
6. Use the skill's own bundled builder / graph logic / validator. Do not recreate that logic ad hoc.
7. Verify integrity using `SHA256SUMS` / `verify.py` where your environment permits.
8. Produce and validate the Beads Atlas HTML, then surface the finished HTML artifact.

If a repository file cannot be read through the available GitHub/repository tools, stop and report that exact transport limitation. Do not fall back to Gists, release ZIPs, `curl`, guessed IPs, web-search reconstruction, or prior state.

## Repository layout

```text
README.md
START_HERE.md
SHA256SUMS
verify.py
issues.jsonl
beads-atlas/
  SKILL.md
  ...the complete skill bundle...
```

The point of this repository is to test the simplest possible bootstrap boundary: **one normal GitHub repository URL, then ordinary repository files only**.
