"""Constructor de mensajes: rellena el sobre, lleva ``seq`` e inventa ids (§2)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .jcs import digest
from .types import VERSION, Sender

__all__ = ['MessageBuilder', 'new_session_id', 'new_message_id', 'utc_now']


def new_session_id() -> str:
    """Id de sesión con 128 bits aleatorios (§2)."""
    return 's_' + secrets.token_hex(16)


def new_message_id() -> str:
    return 'm_' + secrets.token_hex(8)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def _text(blocks: str | Iterable[dict]) -> list[dict]:
    return [{'type': 'text', 'text': blocks}] if isinstance(blocks, str) else list(blocks)


class MessageBuilder:
    """Fabrica los mensajes de un emisor con ``seq`` correlativo.

    ``clock`` y ``ids`` se pueden sustituir para obtener salidas deterministas.
    """

    def __init__(self, sender: Sender, session: str | None = None, *, start_seq: int = 0,
                 clock: Callable[[], str] = utc_now, ids: Callable[[], str] = new_message_id):
        if sender not in ('agent', 'client'):
            raise ValueError('sender debe ser "agent" o "client"')
        self.sender, self.session = sender, session or new_session_id()
        self.seq, self.clock, self.ids = start_seq, clock, ids

    def message(self, type: str, payload: dict[str, Any] | None = None, *, reply_to: str | None = None,
                **envelope: Any) -> dict[str, Any]:
        self.seq += 1
        m = {'pacai': VERSION, 'id': self.ids(), 'type': type, 'session': self.session, 'sender': self.sender,
             'seq': self.seq, 'time': self.clock(), 'payload': dict(payload or {})}
        if reply_to is not None:
            m['reply_to'] = reply_to
        m.update(envelope)
        return m

    __call__ = message

    # -- atajos del núcleo -------------------------------------------------
    def hello(self, versions=(VERSION,), profiles=(), extensions=(), **extra) -> dict:
        return self.message('hello', {'versions': list(versions), 'profiles': list(profiles),
                                      'extensions': list(extensions), **extra})

    def session_started(self, hello_id: str, profiles=(), extensions=(), **extra) -> dict:
        return self.message('session_started', {'version': VERSION, 'profiles': list(profiles),
                                                'extensions': list(extensions), **extra}, reply_to=hello_id)

    def input(self, blocks, mode: str = 'new_run', run_id: str | None = None) -> dict:
        p = {'blocks': _text(blocks), 'mode': mode}
        if run_id:
            p['run_id'] = run_id
        return self.message('input', p)

    def run_started(self, input_id: str | None = None, *, parent_run_id: str | None = None,
                    tool_call_id: str | None = None, agent: dict | None = None) -> dict:
        p = {k: v for k, v in (('input_id', input_id), ('parent_run_id', parent_run_id),
                               ('tool_call_id', tool_call_id), ('agent', agent)) if v is not None}
        return self.message('run_started', p)

    def run_finished(self, run_id: str, outcome: str = 'success', detail: str | None = None) -> dict:
        p = {'run_id': run_id, 'outcome': outcome}
        if detail is not None:
            p['detail'] = detail
        return self.message('run_finished', p)

    def text_message(self, run_id: str, text: str, role: str = 'assistant') -> list[dict]:
        """Un mensaje completo sin streaming: ``message_start`` y ``message_end``."""
        inicio = self.message('message_start', {'run_id': run_id, 'role': role, 'blocks': _text(text)})
        return [inicio, self.message('message_end', {'message_id': inicio['id']})]

    def tool_start(self, run_id: str, name: str, arguments: dict, side: str = 'agent', **extra) -> dict:
        return self.message('tool_start', {'run_id': run_id, 'name': name, 'arguments': arguments,
                                           'side': side, **extra})

    def tool_end(self, tool_call_id: str, status: str = 'success', **extra) -> dict:
        reply = tool_call_id if self.sender == 'client' else None
        return self.message('tool_end', {'tool_call_id': tool_call_id, 'status': status, **extra}, reply_to=reply)

    def approval_request(self, tool_start: dict, *, reason: str, expires: str | None = None,
                         scopes=('once',)) -> dict:
        """Pide permiso para un ``tool_start`` ya emitido; calcula el digest JCS.

        Sin ``expires`` la petición no caduca (§4.5).
        """
        p = tool_start['payload']
        if p.get('truncated'):
            raise ValueError('una llamada con truncated no se puede aprobar (§4.4)')
        payload = {'run_id': p['run_id'], 'tool_call_id': tool_start['id'], 'name': p['name'],
                   'arguments': p['arguments'], 'digest': digest(p['arguments']), 'reason': reason,
                   'scopes': list(scopes)}
        if expires is not None:
            payload['expires'] = expires
        return self.message('approval_request', payload)

    def approval_result(self, request_id: str, decision: str, scope: str | None = None,
                        reason: str | None = None) -> dict:
        p = {'decision': decision}
        if scope is not None:
            p['scope'] = scope
        if reason is not None:
            p['reason'] = reason
        return self.message('approval_result', p, reply_to=request_id)

    def cancel_approval(self, request_id: str) -> dict:
        """El agente resuelve una petición pendiente porque la ejecución termina o se interrumpe (§4.5)."""
        return self.approval_result(request_id, 'cancelled')

    def cancel_client_tool(self, tool_call_id: str) -> dict:
        """El agente da por cancelada una herramienta del cliente al terminar o interrumpir (§4.4).

        Va sin ``reply_to``: no es una respuesta.
        """
        if self.sender != 'agent':
            raise ValueError('solo el agente cancela una herramienta del cliente')
        return self.message('tool_end', {'tool_call_id': tool_call_id, 'status': 'cancelled'})

    def interrupt(self, run_id: str) -> dict:
        return self.message('interrupt', {'run_id': run_id})

    def error(self, code: str, message: str, ref: str | None = None) -> dict:
        p = {'code': code, 'message': message}
        if ref is not None:
            p['ref'] = ref
        return self.message('error', p)

    def close(self, reason: str = '') -> dict:
        return self.message('close', {'reason': reason})
