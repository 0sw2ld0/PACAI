# PACAI

[Español](README.md) · English

**Protocol for Agent Communication And Interfaces.** PACAI defines how an
agent and its client exchange messages, track runs, call tools, and ask for
approval. A client can use those events to present the same agent in a
desktop app, a terminal, or another interface.

Website: <https://docs.pacai.dev/> (in Spanish).

This repository covers PACAI 0.3 and includes the protocol specification, a
JSON Schema, conformance examples, and SDKs for Python and Swift. The
specification is written in Spanish and uses English identifiers on the wire.

## Try it with AlfalfaCode

Install [AlfalfaCode](https://github.com/0sw2ld0/AlfalfaCode/releases/latest),
configure a model provider, and make sure the `alfalfa` command is on your
`PATH`. The [Python example](sdk/python/ejemplos/sesion_con_alfalfa.py) starts
`alfalfa --pacai --modo plan` in the current directory. It validates the
exchange as it goes and denies any approval requests it receives.

Run these commands from a workspace with sibling directories named `PACAI`
and `my-project`:

```sh
python3 -m pip install jsonschema
cd my-project
PYTHONPATH=../PACAI/sdk/python python3 ../PACAI/sdk/python/ejemplos/sesion_con_alfalfa.py \
  --guardar session.jsonl "Summarize this project's files in one sentence."
python3 ../PACAI/conformance/verificar.py session.jsonl
```

The example prints a summary and saves messages from both sides with
`--guardar`. Use `--todo` to show usage and extension messages as well.

## A session on the wire

Here is the opening of an illustrative session. Send messages with
`sender: "client"` to stdin and read messages with `sender: "agent"` from
stdout. The two sides share a session ID and maintain separate sequence numbers.

```jsonl
{"pacai":"0.3","id":"m_00000001","type":"hello","session":"s_example_0123456789abcdef","sender":"client","seq":1,"time":"2026-11-12T10:00:01Z","payload":{"versions":["0.3"]}}
{"pacai":"0.3","id":"m_00000002","type":"hello","session":"s_example_0123456789abcdef","sender":"agent","seq":1,"time":"2026-11-12T10:00:02Z","payload":{"versions":["0.3"],"profiles":["work"],"extensions":["alfalfa"]}}
{"pacai":"0.3","id":"m_00000003","type":"session_started","session":"s_example_0123456789abcdef","sender":"agent","seq":2,"time":"2026-11-12T10:00:03Z","reply_to":"m_00000001","payload":{"version":"0.3","profiles":[],"extensions":[]}}
{"pacai":"0.3","id":"m_00000004","type":"input","session":"s_example_0123456789abcdef","sender":"client","seq":2,"time":"2026-11-12T10:00:04Z","payload":{"blocks":[{"type":"text","text":"What is in this folder?"}]}}
{"pacai":"0.3","id":"m_00000005","type":"run_started","session":"s_example_0123456789abcdef","sender":"agent","seq":3,"time":"2026-11-12T10:00:05Z","payload":{"input_id":"m_00000004"}}
```

- A run streams text and tool events before `run_finished`. The ID of
  `run_started` is the run ID. See [a complete text session](conformance/valid/01-texto.jsonl).
- An `approval_request` ties the decision to the tool arguments with a
  SHA-256 digest of their canonical JSON. The client replies with
  `approval_result` and uses `reply_to` to identify the request. An approval
  can apply once or to the session, according to the offered scopes. See
  [approval and cancellation examples](conformance/valid/).
- On stdio, each UTF-8 JSON message ends in a line feed. The
  `max_message_bytes` limit includes that byte. Logs go to stderr.

AlfalfaCode implements the PACAI core over stdio and supports the optional
`work` profile and `alfalfa` extension. PACAI 0.3 also specifies WebSocket and
SSE transport. See the [AlfalfaCode integration guide](https://github.com/0sw2ld0/AlfalfaCode/blob/main/docs/USO.md#control-con-pacai-alfalfa---pacai).

## SDKs and conformance

| Resource | Use |
| --- | --- |
| [PACAI 0.3 specification](spec/PACAI-0.3.md) | Message types, state transitions, negotiation, and transports |
| [`ui` profile (draft, Spanish)](spec/perfiles/ui.md) | Let the agent draw screens in the chat; schema in `schema/pacai-ui-1.schema.json` |
| [JSON Schema](schema/pacai-0.3.schema.json) | Validate the structure of individual messages |
| [Conformance suite](conformance/) | Check sample transcripts and verify your own sessions |
| [Python SDK](sdk/python/README.md) | Build messages, read and write JSONL, and validate session rules |
| [Swift package](sdk/swift/Package.swift) | Encode and decode typed messages on macOS 14 and iOS 17 or later |

From the PACAI repository root, use Python 3.11 or later to install the SDK and
run its tests:

```sh
python3 -m pip install -e 'sdk/python[test]'
python3 conformance/verificar.py
python3 -m pytest sdk/python/tests
swift test --package-path sdk/swift
```

Use the Swift package as a local dependency with
`.package(path: "../PACAI/sdk/swift")` and add
`.product(name: "PACAI", package: "swift")` to your target. The Swift SDK handles
message encoding and decoding. Use the Python verifier for schema and
session validation.

PACAI is released under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE)
for attribution.
