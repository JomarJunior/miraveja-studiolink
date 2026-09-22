"""CI guard: fail the build if a secret or a non-synthetic persona name leaks in.

This repository is public (Constitution Principle VIII). It must never carry a real
persona definition, a real persona name, or a credential. Persona definitions have no
fixed shape we can pattern-match from a public repo, so this guard checks what it can:
common secret formats, and that every "publicName" used in tests and fixtures reads as
synthetic (SC-008).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Slack token", re.compile(r"xox[abp]-[A-Za-z0-9-]{10,}")),
    ("OpenAI-style key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("PEM private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]

# Text files worth scanning; binary and lock files are skipped.
SCANNABLE_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".cfg", ".ini"}

PUBLIC_NAME_RE = re.compile(r'"publicName"\s*:\s*"([^"]+)"|publicName:\s*"?([^",\n]+)"?')


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


def scan_for_secrets(files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        if path.suffix not in SCANNABLE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{path.relative_to(REPO_ROOT)}: looks like a {label}")
    return problems


def scan_for_real_persona_names(files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        if path.suffix not in {".json", ".yaml", ".yml"}:
            continue
        if "tests" not in path.parts and "examples" not in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in PUBLIC_NAME_RE.finditer(text):
            name = (match.group(1) or match.group(2) or "").strip()
            if name and "synthetic" not in name.lower():
                problems.append(
                    f"{path.relative_to(REPO_ROOT)}: publicName {name!r} does not read as synthetic"
                )
    return problems


def main() -> int:
    files = tracked_files()
    problems = scan_for_secrets(files) + scan_for_real_persona_names(files)
    if problems:
        print("Public repository guard failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"Public repository guard passed ({len(files)} tracked files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
