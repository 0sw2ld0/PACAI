"""Tipos del sobre y de cada mensaje de PACAI 0.2 (§2–§7).

Son ``TypedDict``: un mensaje sigue siendo un ``dict`` JSON normal, y los
tipos sirven para el editor y para mypy. Los campos desconocidos se conservan.
"""
from __future__ import annotations

from typing import Any, Literal, Required, TypedDict, Union

__all__ = [
    'VERSION', 'Sender', 'Envelope', 'Block', 'TextBlock', 'FileBlock', 'StructuredBlock', 'AudioBlock',
    'ClientTool', 'RunState', 'MESSAGE_TYPES', 'SENDER_OF', 'PROFILE_OF', 'RUN_SCOPED', 'REPLY_REQUIRED',
    'ERROR_CODES', 'APPROVAL_REASONS', 'PAYLOAD_TYPES',
]

VERSION = '0.2'
Sender = Literal['agent', 'client']
Outcome = Literal['success', 'interrupted', 'failed', 'blocked']
Scope = Literal['once', 'session']


class Envelope(TypedDict, total=False):
    """Sobre común (§2). ``reply_to`` es opcional; el resto, obligatorio."""
    pacai: Required[str]
    id: Required[str]
    type: Required[str]
    session: Required[str]
    sender: Required[Sender]
    seq: Required[int]
    time: Required[str]
    reply_to: str
    payload: Required[dict[str, Any]]


# -- bloques (§3) ---------------------------------------------------------
class TextBlock(TypedDict):
    type: Literal['text']
    text: str


class FileBlock(TypedDict, total=False):
    type: Required[Literal['file']]
    name: Required[str]
    media_type: Required[str]
    data: str
    url: str


class StructuredBlock(TypedDict):
    type: Literal['structured']
    schema: str
    data: dict[str, Any]


class AudioBlock(TypedDict, total=False):
    type: Required[Literal['audio']]
    media_type: Required[str]
    encoding: Required[Literal['pcm16', 'opus', 'mp3']]
    data: str
    url: str
    transcript: str


Block = Union[TextBlock, FileBlock, StructuredBlock, AudioBlock]


class ClientTool(TypedDict, total=False):
    name: Required[str]
    description: str
    input_schema: Required[dict[str, Any]]


class RunState(TypedDict, total=False):
    run_id: Required[str]
    status: Required[Literal['active', 'finished']]
    outcome: Outcome
    parent_run_id: str


# -- payloads (§4) --------------------------------------------------------
class Hello(TypedDict, total=False):
    versions: Required[list[str]]
    profiles: list[str]
    extensions: list[str]
    client_tools: list[ClientTool]
    limits: dict[str, int]
    resume_after_seq: int
    render: dict[str, Any]
    implementation: dict[str, str]


class SessionStarted(TypedDict, total=False):
    version: Required[str]
    profiles: Required[list[str]]
    extensions: Required[list[str]]
    agent: dict[str, str]
    resumed: bool
    resume_after_seq: int


class Input(TypedDict, total=False):
    blocks: Required[list[Block]]
    mode: Literal['new_run', 'steer']
    run_id: str


class RunStarted(TypedDict, total=False):
    input_id: str          # ejecución raíz
    parent_run_id: str     # subejecución (§4.9)
    tool_call_id: str
    agent: dict[str, str]


class RunFinished(TypedDict, total=False):
    run_id: Required[str]
    outcome: Required[Outcome]
    detail: str


class MessageStart(TypedDict, total=False):
    run_id: Required[str]
    role: Required[Literal['assistant', 'user', 'system', 'tool']]
    blocks: list[Block]


class MessageDelta(TypedDict):
    message_id: str
    blocks: list[Block]


class MessageEnd(TypedDict, total=False):
    message_id: Required[str]
    blocks: list[Block]


class ToolStart(TypedDict, total=False):
    run_id: Required[str]
    name: Required[str]
    arguments: Required[dict[str, Any]]
    side: Required[Sender]
    title: str
    approval_id: str


class ToolEnd(TypedDict, total=False):
    tool_call_id: Required[str]
    status: Required[Literal['success', 'error', 'cancelled']]
    output: list[Block]
    summary: str


class ApprovalRequest(TypedDict):
    run_id: str
    tool_call_id: str
    name: str
    arguments: dict[str, Any]
    digest: str
    reason: str
    scopes: list[Scope]
    expires: str


class ApprovalResult(TypedDict, total=False):
    decision: Required[Literal['approved', 'denied', 'expired']]
    scope: Scope
    reason: str


class Interrupt(TypedDict):
    run_id: str


class Usage(TypedDict, total=False):
    run_id: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    context_tokens: int
    context_limit: int
    cost: dict[str, Any]


class Heartbeat(TypedDict):
    last_seq: int


class Error(TypedDict, total=False):
    code: Required[str]
    message: Required[str]
    ref: str


class Close(TypedDict, total=False):
    reason: str


class Snapshot(TypedDict, total=False):
    runs: Required[list[RunState]]
    pending_approvals: Required[list[dict[str, Any]]]
    last_messages: list[dict[str, Any]]


# -- perfiles (§7) --------------------------------------------------------
class VoiceTurn(TypedDict):
    state: Literal['client_speaking', 'agent_listening', 'barge_in']


class StateSnapshot(TypedDict, total=False):
    agent: dict[str, Any]
    client: dict[str, Any]


class StateDelta(TypedDict):
    patch: list[dict[str, Any]]


class PlanUpdated(TypedDict):
    run_id: str
    steps: list[dict[str, str]]


class DiffUpdated(TypedDict, total=False):
    run_id: Required[str]
    files: Required[list[dict[str, Any]]]
    patch: str


class Expression(TypedDict, total=False):
    run_id: str
    message_id: str
    emotion: str
    intensity: float
    gesture: str
    voice_style: str
    duration_ms: int
    character: str


PAYLOAD_TYPES: dict[str, type] = {
    'hello': Hello, 'session_started': SessionStarted, 'input': Input, 'run_started': RunStarted,
    'run_finished': RunFinished, 'message_start': MessageStart, 'message_delta': MessageDelta,
    'message_end': MessageEnd, 'tool_start': ToolStart, 'tool_end': ToolEnd,
    'approval_request': ApprovalRequest, 'approval_result': ApprovalResult, 'interrupt': Interrupt,
    'usage': Usage, 'heartbeat': Heartbeat, 'error': Error, 'close': Close, 'snapshot': Snapshot,
    'voice_turn': VoiceTurn, 'state_snapshot': StateSnapshot, 'state_delta': StateDelta,
    'plan_updated': PlanUpdated, 'diff_updated': DiffUpdated, 'expression': Expression,
}
MESSAGE_TYPES = frozenset(PAYLOAD_TYPES)

# Quién puede enviar cada tipo; None = ambos.
SENDER_OF: dict[str, Sender | None] = {
    'hello': None, 'session_started': 'agent', 'input': 'client', 'run_started': 'agent',
    'run_finished': 'agent', 'message_start': 'agent', 'message_delta': 'agent', 'message_end': 'agent',
    'tool_start': 'agent', 'tool_end': None, 'approval_request': 'agent', 'approval_result': None,
    'interrupt': 'client', 'usage': 'agent', 'heartbeat': None, 'error': None, 'close': None,
    'snapshot': 'agent', 'voice_turn': None, 'state_snapshot': None, 'state_delta': None,
    'plan_updated': 'agent', 'diff_updated': 'agent', 'expression': 'agent',
}
PROFILE_OF = {'voice_turn': 'voice', 'state_snapshot': 'shared_state', 'state_delta': 'shared_state',
              'plan_updated': 'work', 'diff_updated': 'work', 'expression': 'expression'}
# Mensajes del agente cuyo payload.run_id debe nombrar una ejecución activa.
RUN_SCOPED = frozenset({'message_start', 'tool_start', 'approval_request', 'usage', 'plan_updated',
                        'diff_updated', 'expression'})
REPLY_REQUIRED = frozenset({'session_started', 'approval_result', 'snapshot'})
ERROR_CODES = frozenset({
    'version_incompatible', 'not_negotiated', 'seq_unrecoverable', 'unknown_run', 'unknown_approval',
    'unknown_tool_call', 'message_too_large', 'invalid_message', 'retention_expired',
})
APPROVAL_REASONS = frozenset({'dangerous', 'network', 'outside_sandbox', 'sandbox_denied_retry',
                              'external_tool', 'policy'})
