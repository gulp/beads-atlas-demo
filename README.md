# Beads Atlas — repository-native ChatGPT demo

This repository is deliberately **uncompressed and text-addressable**. There is no Gist bootstrap, release download, archive extraction, or child URL to discover.

## Fresh ChatGPT test

Give a new ChatGPT conversation exactly this:

```text
Study https://github.com/gulp/beads-atlas-demo and follow instructions
```

## Instructions for ChatGPT

Treat this public repository as the complete clean-room task package.

1. Do not use prior conversations, projects, memory-derived artifacts, Gists, or release assets.
2. Stay inside ordinary files on this repository's default branch.
3. Read **[START_HERE.md](START_HERE.md)** completely.
4. Read **[beads-atlas/SKILL.md](beads-atlas/SKILL.md)** completely and follow it as the operative skill contract.
5. Use **[issues.jsonl](issues.jsonl)** at repository root as the demonstration input; it is the intended 41-issue corpus.
6. Use the skill's own bundled builder / graph logic / validator. Do not recreate that logic ad hoc.
7. Use **[SHA256SUMS](SHA256SUMS)** and **[verify.py](verify.py)** when the repository files are materialized locally.
8. Produce and validate the Beads Atlas HTML, then surface the finished HTML artifact.

If execution requires filesystem copies, create them only from ordinary repository file contents already obtained through the available GitHub/repository tools. If a repository file cannot be read exactly, stop and report that transport limitation.

Do **not** fall back to Gists, release ZIPs, shell `curl`/`wget`, guessed IPs, web-search reconstruction, or prior state.

## Repository layout

```text
README.md
START_HERE.md
SHA256SUMS
verify.py
issues.jsonl
beads-atlas/
  SKILL.md
  assets/
  references/
  scripts/
```

The point of this repository is to test the simplest possible bootstrap boundary: **one normal GitHub repository URL, then ordinary repository files only**.
