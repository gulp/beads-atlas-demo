#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

errors = []

for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    expected, rel = line.split("  ", 1)
    p = ROOT / rel
    if not p.is_file():
        errors.append(f"MISSING {rel}")
    elif sha256(p) != expected:
        errors.append(f"HASH {rel}")

count = 0
for lineno, raw in enumerate((ROOT / "issues.jsonl").read_bytes().splitlines(), 1):
    if not raw.strip():
        continue
    try:
        json.loads(raw)
    except Exception as e:
        errors.append(f"JSON issues.jsonl:{lineno} {e}")
    count += 1

if count != 41:
    errors.append(f"COUNT expected=41 actual={count}")

if errors:
    print("BEADS_ATLAS_DEMO_VERIFY=FAIL", file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    raise SystemExit(1)

print("BEADS_ATLAS_DEMO_VERIFY=PASS")
print("records=41")
print("issues_sha256=832655f821891bcfb460bd0914b70427a17d5cd9f2169bc689e748713a3c10fb")
print("skill_archive_sha256=a6f52ba7e6df39166d6686f4d7553f0c21165dc4be82f51dba79e0ed68d40c69")
