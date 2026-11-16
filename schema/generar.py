"""Genera schema/pacai-0.3.schema.json y su copia en el SDK de Python.

La autoridad es spec/PACAI-0.3.md. El esquema de la 0.2 se conserva en schema/historico/.
"""
import json
from pathlib import Path

S = lambda **k: {'type': 'string', **k}
I = lambda **k: {'type': 'integer', **k}
O = lambda props, req=(), extra=True: {'type': 'object', 'properties': props, 'required': list(req),
                                        'additionalProperties': extra}
E = lambda *v: {'enum': list(v)}
REF = lambda n: {'$ref': '#/$defs/' + n}
BLOCKS = {'type': 'array', 'items': REF('block')}
ID = S(minLength=8)

defs = {
    'block': {'oneOf': [
        O({'type': {'const': 'text'}, 'text': S()}, ['type', 'text']),
        O({'type': {'const': 'file'}, 'name': S(), 'media_type': S(), 'data': S(), 'url': S()},
          ['type', 'name', 'media_type']),
        O({'type': {'const': 'structured'}, 'schema': S(), 'data': {'type': 'object'}}, ['type', 'schema', 'data']),
        O({'type': {'const': 'audio'}, 'media_type': S(), 'encoding': E('pcm16', 'opus', 'mp3'),
           'data': S(), 'url': S(), 'transcript': S()}, ['type', 'media_type', 'encoding']),
    ]},
    'client_tool': O({'name': S(minLength=1), 'description': S(), 'input_schema': {'type': 'object'}},
                     ['name', 'input_schema']),
    'run_state': {'allOf': [O({'run_id': ID, 'status': E('active', 'finished'),
                               'outcome': E('success', 'interrupted', 'failed', 'blocked'),
                               'parent_run_id': ID}, ['run_id', 'status']),
                            {'if': {'properties': {'status': {'const': 'finished'}}},
                             'then': {'required': ['outcome']}, 'else': {'not': {'required': ['outcome']}}}]},
}

payloads = {
    'hello': O({'versions': {'type': 'array', 'items': S(), 'minItems': 1},
                'profiles': {'type': 'array', 'items': S()},
                'extensions': {'type': 'array', 'items': S(pattern='^[a-z][a-z0-9_]*$')},
                'client_tools': {'type': 'array', 'items': REF('client_tool')},
                'limits': O({'max_message_bytes': I(minimum=1024)}),
                'resume_after_seq': I(minimum=0), 'render': {'type': 'object'},
                'implementation': O({'name': S(), 'version': S()})}, ['versions']),
    'session_started': O({'version': S(), 'profiles': {'type': 'array', 'items': S()},
                          'extensions': {'type': 'array', 'items': S()},
                          'agent': O({'name': S(), 'version': S()}), 'resumed': {'type': 'boolean'},
                          'resume_after_seq': I(minimum=0)},
                         ['version', 'profiles', 'extensions']),
    'input': {'allOf': [O({'blocks': BLOCKS, 'mode': E('new_run', 'steer'), 'run_id': ID}, ['blocks']),
                        {'if': {'properties': {'mode': {'const': 'steer'}}, 'required': ['mode']},
                         'then': {'required': ['run_id']}}]},
    # Una ejecución raíz nace de un input; una subejecución (subagente), de su ejecución madre.
    'run_started': {'allOf': [O({'input_id': ID, 'parent_run_id': ID, 'tool_call_id': ID,
                                 'agent': O({'name': S(minLength=1), 'description': S()}, ['name'])}),
                              {'oneOf': [{'required': ['input_id']}, {'required': ['parent_run_id']}]},
                              {'dependentRequired': {'tool_call_id': ['parent_run_id']}}]},
    'run_finished': {'allOf': [O({'run_id': ID, 'outcome': E('success', 'interrupted', 'failed', 'blocked'),
                                  'detail': S()}, ['run_id', 'outcome']),
                               {'if': {'properties': {'outcome': E('failed', 'blocked')}},
                                'then': {'required': ['detail']}}]},
    'message_start': O({'run_id': ID, 'role': E('assistant', 'user', 'system', 'tool'), 'blocks': BLOCKS},
                       ['run_id', 'role']),
    'message_delta': O({'message_id': ID, 'blocks': BLOCKS}, ['message_id', 'blocks']),
    'message_end': O({'message_id': ID, 'blocks': BLOCKS}, ['message_id']),
    # Unos argumentos acortados no se pueden ejecutar en el cliente ni reutilizar una aprobación (§4.4).
    'tool_start': {'allOf': [O({'run_id': ID, 'name': S(minLength=1), 'arguments': {'type': 'object'},
                                'side': E('agent', 'client'), 'title': S(), 'approval_id': ID,
                                'truncated': {'type': 'boolean'}}, ['run_id', 'name', 'arguments', 'side']),
                             {'if': {'properties': {'truncated': {'const': True}}, 'required': ['truncated']},
                              'then': {'properties': {'side': {'const': 'agent'}},
                                       'not': {'required': ['approval_id']}}}]},
    'tool_end': O({'tool_call_id': ID, 'status': E('success', 'error', 'cancelled'), 'output': BLOCKS,
                   'summary': S()}, ['tool_call_id', 'status']),
    'approval_request': O({'run_id': ID, 'tool_call_id': ID, 'name': S(minLength=1),
                           'arguments': {'type': 'object'}, 'digest': S(pattern='^sha256:[0-9a-f]{64}$'),
                           'reason': S(pattern='^(dangerous|network|outside_sandbox|sandbox_denied_retry|'
                                               'external_tool|policy|[a-z][a-z0-9_]*\\.[a-z0-9_.]+)$'),
                           'scopes': {'type': 'array', 'items': E('once', 'session'), 'minItems': 1,
                                      'uniqueItems': True},
                           'expires': S(format='date-time')},
                          ['run_id', 'tool_call_id', 'name', 'arguments', 'digest', 'reason', 'scopes']),
    'approval_result': {'allOf': [O({'decision': E('approved', 'denied', 'expired', 'cancelled'),
                                     'scope': E('once', 'session'),
                                     'reason': S()}, ['decision']),
                                  {'if': {'properties': {'decision': {'const': 'approved'}}},
                                   'then': {'required': ['scope']}, 'else': {'not': {'required': ['scope']}}}]},
    'interrupt': O({'run_id': ID}, ['run_id']),
    'usage': O({'run_id': ID, 'input_tokens': I(minimum=0), 'output_tokens': I(minimum=0),
                'cached_tokens': I(minimum=0), 'context_tokens': I(minimum=0), 'context_limit': I(minimum=1),
                'cost': O({'amount': {'type': 'number', 'minimum': 0}, 'currency': S(pattern='^[A-Z]{3}$')},
                          ['amount', 'currency'])}),
    'heartbeat': O({'last_seq': I(minimum=0)}, ['last_seq']),
    'error': O({'code': S(pattern='^[a-z][a-z0-9_]*(\\.[a-z0-9_]+)*$'), 'message': S(), 'ref': ID},
               ['code', 'message']),
    'close': O({'reason': S()}),
    # Los mensajes incrustados son mensajes PACAI completos ('#' es la raíz de este esquema).
    'snapshot': O({'runs': {'type': 'array', 'items': REF('run_state')},
                   'pending_approvals': {'type': 'array', 'items': {
                       'allOf': [{'$ref': '#'}, {'properties': {'type': {'const': 'approval_request'}}}]}},
                   'last_messages': {'type': 'array', 'items': {'$ref': '#'}}},
                  ['runs', 'pending_approvals']),
    'voice_turn': O({'state': E('client_speaking', 'agent_listening', 'barge_in')}, ['state']),
    'state_snapshot': O({'agent': {'type': 'object'}, 'client': {'type': 'object'}}),
    'state_delta': O({'patch': {'type': 'array', 'items': O(
        {'op': E('add', 'remove', 'replace', 'move', 'copy', 'test'), 'path': S(pattern='^/(agent|client)(/.*)?$')},
        ['op', 'path'])}}, ['patch']),
    'plan_updated': O({'run_id': ID, 'steps': {'type': 'array', 'items': O(
        {'text': S(), 'status': E('pending', 'in_progress', 'completed')}, ['text', 'status'])}}, ['run_id', 'steps']),
    'diff_updated': O({'run_id': ID, 'files': {'type': 'array', 'items': O(
        {'path': S(), 'added': I(minimum=0), 'removed': I(minimum=0)}, ['path'])}, 'patch': S()}, ['run_id', 'files']),
    'expression': O({'run_id': ID, 'message_id': ID, 'emotion': S(), 'intensity': {'type': 'number', 'minimum': 0,
                     'maximum': 1}, 'gesture': S(), 'voice_style': S(), 'duration_ms': I(minimum=0),
                     'character': S()}),
}
SENDER = {'hello': None, 'session_started': 'agent', 'input': 'client', 'run_started': 'agent',
          'run_finished': 'agent', 'message_start': 'agent', 'message_delta': 'agent', 'message_end': 'agent',
          'tool_start': 'agent', 'tool_end': None, 'approval_request': 'agent', 'approval_result': None,
          'interrupt': 'client', 'usage': 'agent', 'heartbeat': None, 'error': None, 'close': None,
          'snapshot': 'agent', 'voice_turn': None, 'state_snapshot': None, 'state_delta': None,
          'plan_updated': 'agent', 'diff_updated': 'agent', 'expression': 'agent'}
REPLY = {'session_started', 'approval_result', 'snapshot'}
# Restricciones que dependen a la vez del sobre y del payload.
CROSS = {
    # El cliente aprueba o niega; solo el agente declara caducada o cancelada su propia petición.
    'approval_result': [{'if': {'properties': {'sender': {'const': 'agent'}}},
                         'then': {'properties': {'payload': {'properties': {
                             'decision': E('expired', 'cancelled')}}}},
                         'else': {'properties': {'payload': {'properties': {
                             'decision': E('approved', 'denied')}}}}}],
    # La herramienta del cliente se contesta con reply_to al tool_start (§4.4). Del agente, el
    # tool_end de una herramienta del cliente solo puede ser cancelled: eso lo comprueba Session.
    'tool_end': [{'if': {'properties': {'sender': {'const': 'client'}}}, 'then': {'required': ['reply_to']}}],
}

variants = []
for name, payload in payloads.items():
    props = {'type': {'const': name}, 'payload': payload}
    if SENDER[name]:
        props['sender'] = {'const': SENDER[name]}
    v = {'properties': props}
    if name in REPLY:
        v['required'] = ['reply_to']
    if name in CROSS:
        v['allOf'] = CROSS[name]
    variants.append(v)
variants.append({'properties': {'type': S(pattern='^[a-z][a-z0-9_]*\\.[a-z0-9_.]+$'),
                                'payload': {'type': 'object'}}})

schema = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'pacai-0.3.schema.json',
    'title': 'Mensaje PACAI 0.3',
    'type': 'object',
    'required': ['pacai', 'id', 'type', 'session', 'sender', 'seq', 'time', 'payload'],
    'properties': {'pacai': {'const': '0.3'}, 'id': ID, 'type': S(), 'session': S(minLength=16),
                   'sender': E('agent', 'client'), 'seq': I(minimum=1),
                   'time': S(format='date-time'), 'reply_to': ID, 'payload': {'type': 'object'}},
    'oneOf': variants,
    '$defs': defs,
}
texto = json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
raiz = Path(__file__).resolve().parent.parent
for out in (raiz / 'schema/pacai-0.3.schema.json', raiz / 'sdk/python/pacai/pacai-0.3.schema.json'):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(texto)
    print('escrito', out.relative_to(raiz), len(variants), 'variantes')
