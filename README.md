# 🔗 miraveja-studiolink

A Python library for the **Studio Link**: the single contract between the Studio (the team's
GPU machine, which keeps hours and may be offline) and the Museum side of **🖼️ MiraVeja**.

The contract itself — the OpenAPI 3.1 document, its JSON Schema messages and its example
fixtures — is **not** kept here. It lives in the hub, as the single source of truth:

- [`specs/001-studiolink-contract/`](https://github.com/JomarJunior/miraveja-ecosystem/tree/main/specs/001-studiolink-contract)
- [`specs/001-studiolink-contract/contracts/studiolink-v1.yaml`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/001-studiolink-contract/contracts/studiolink-v1.yaml)

This library ships the runnable parts built against that contract:

- `miraveja_studiolink.messages` — Pydantic v2 models for every message, checked against the
  hub's schemas by a drift test.
- `miraveja_studiolink.client` — the Studio end: sends, collects, acknowledges, and validates
  every Museum response strictly (an unknown field refuses the whole message).
- `miraveja_studiolink.standin` — a conforming, scriptable, in-memory Museum end, so the Studio
  can be built and tested with no **🏛️ MuseuMusa** or **🛡️ PortaGuarda** anywhere.
- `miraveja_studiolink.conformance` — a scripted Studio that checks any Museum end (the real one
  or the stand-in) without a Studio running.

## Development

Requires this library checked out inside a `miraveja-ecosystem` hub checkout, at
`components/miraveja-studiolink/`, so the contract can be read from
`../../specs/001-studiolink-contract/contracts/studiolink-v1.yaml` (override with
`STUDIOLINK_CONTRACT_PATH`).

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

## Usage

```bash
# Run the reference stand-in, seeded from a scripting fixture:
uv run miraveja-studiolink standin --port 8080 --script tests/fixtures/one-visitor-comment.yaml

# Check any Museum end against the contract's conformance suite:
uv run miraveja-studiolink conformance --target http://localhost:8080 --credential $STUDIOLINK_TOKEN
```

See [`docs/usage.md`](./docs/usage.md) for how a Studio component talks to the Museum
side with `StudioLinkClient`, how refusals work, and how to check a Museum end you're
building against the conformance suite. See
[`specs/001-studiolink-contract/quickstart.md`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/001-studiolink-contract/quickstart.md)
in the hub for the full walkthrough.

## License

Apache-2.0. See [`LICENSE`](./LICENSE).
