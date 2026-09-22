"""Every fixture and example uses a synthetic persona, never a real one.

Principle VIII, SC-008, T021.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from miraveja_studiolink.contract import contract_path

FIXTURES_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = contract_path().parent / "examples"

_PUBLIC_NAME_KEYS = ("publicName",)


def _public_names(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _PUBLIC_NAME_KEYS and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_public_names(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_public_names(item))
    return found


def test_every_scripting_fixture_uses_synthetic_persona_names() -> None:
    yaml_files = list(FIXTURES_DIR.glob("*.yaml"))
    assert yaml_files, "expected at least one scripting fixture"
    for path in yaml_files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name in _public_names(data):
            assert re.search(r"synthetic", name, re.IGNORECASE), (
                f"{path.name}: publicName {name!r} does not read as synthetic"
            )


def test_every_hub_example_uses_synthetic_persona_names() -> None:
    example_files = list((EXAMPLES_DIR / "valid").glob("*.json")) + list(
        (EXAMPLES_DIR / "invalid").glob("*.json")
    )
    assert example_files, "expected at least one hub example"
    for path in example_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for name in _public_names(data):
            assert re.search(r"synthetic", name, re.IGNORECASE), (
                f"{path.name}: publicName {name!r} does not read as synthetic"
            )
