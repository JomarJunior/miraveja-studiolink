"""Reads the Studio Link contract from the hub checkout this library sits inside.

The hub (`miraveja-ecosystem`) is the single source of truth for the contract (FR-008).
This library never vendors a copy: it reads
`specs/001-studiolink-contract/contracts/studiolink-v1.yaml` from the hub checkout that
contains this library at `components/miraveja-studiolink/`, or from
`STUDIOLINK_CONTRACT_PATH` when that layout does not hold (R-13).
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml

_RELATIVE_TO_LIBRARY_ROOT = Path("../../specs/001-studiolink-contract/contracts/studiolink-v1.yaml")


class ContractNotFound(RuntimeError):
    """The Studio Link contract document could not be located."""


def _library_root() -> Path:
    # src/miraveja_studiolink/contract.py -> src/miraveja_studiolink -> src -> library root
    return Path(__file__).resolve().parents[2]


def contract_path() -> Path:
    """The path to `studiolink-v1.yaml`, honoring `STUDIOLINK_CONTRACT_PATH`."""
    override = os.environ.get("STUDIOLINK_CONTRACT_PATH")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = (_library_root() / _RELATIVE_TO_LIBRARY_ROOT).resolve()
    if not path.is_file():
        raise ContractNotFound(
            f"Studio Link contract not found at {path}. Check out this library at "
            "components/miraveja-studiolink/ inside a miraveja-ecosystem hub checkout, "
            "or set STUDIOLINK_CONTRACT_PATH."
        )
    return path


@functools.lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    """The parsed OpenAPI document, cached for the process lifetime."""
    with contract_path().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def schema(name: str) -> dict[str, Any]:
    """The raw JSON Schema for `components.schemas.<name>` in the contract."""
    document = load_contract()
    try:
        return document["components"]["schemas"][name]
    except KeyError as exc:
        raise ContractNotFound(f"No schema named {name!r} in the Studio Link contract") from exc


def contract_version() -> str:
    """The contract's published version, e.g. "1.0.0"."""
    return load_contract()["info"]["version"]
