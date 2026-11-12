"""Genera los ejemplos de conformance/. Cada archivo .jsonl es una sesión completa."""
import hashlib, json
from pathlib import Path

D = Path(__file__).parent
SES = 's_ejemplo_0123456789abcdef'


def digest(args):
    canon = json.dumps(args, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return 'sha256:' + hashlib.sha256(canon.encode()).hexdigest()


class Sesion:
    def __init__(self):
        self.msgs, self.seq, self.n = [], {'agent': 0, 'client': 0}, 0

    def __call__(self, sender, type, payload, reply_to=None, **sobre):
        self.seq[sender] += 1
        self.n += 1
        m = {'pacai': '0.2', 'id': f'm_{self.n:08d}', 'type': type, 'session': SES, 'sender': sender,
             'seq': self.seq[sender], 'time': f'2026-11-12T10:00:{self.n:02d}Z', 'payload': payload}
        if reply_to:
            m['reply_to'] = reply_to
        m.update(sobre)
        self.msgs.append(m)
        return m['id']

    def write(self, ruta):
        (D / ruta).write_text(''.join(json.dumps(m, ensure_ascii=False) + '\n' for m in self.msgs))


def inicio(s, perfiles=(), ext=(), **hello):
    h = s('client', 'hello', {'versions': ['0.2'], 'profiles': list(perfiles), 'extensions': list(ext), **hello})
    s('agent', 'hello', {'versions': ['0.2'], 'profiles': list(perfiles), 'extensions': list(ext)})
    s('agent', 'session_started', {'version': '0.2', 'profiles': list(perfiles), 'extensions': list(ext),
                                   'agent': {'name': 'ejemplo', 'version': '0.0.1'}}, reply_to=h)


def texto(t):
    return [{'type': 'text', 'text': t}]


# 01: una pregunta y una respuesta en streaming.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('¿Qué hora es en Lima?'), 'mode': 'new_run'})
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant'})
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('Son las ')})
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('5:00.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'usage', {'run_id': r, 'input_tokens': 120, 'output_tokens': 8, 'context_tokens': 128,
                     'context_limit': 128000})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s('client', 'close', {'reason': 'fin'})
s.write('valid/01-texto.jsonl')

# 02: herramienta peligrosa aprobada una vez, perfil work.
s = Sesion(); inicio(s, ['work'])
e = s('client', 'input', {'blocks': texto('Borra la carpeta build.')})
r = s('agent', 'run_started', {'input_id': e})
s('agent', 'plan_updated', {'run_id': r, 'steps': [{'text': 'Borrar build/', 'status': 'in_progress'}]})
args = {'argv': ['rm', '-rf', 'build']}
t = s('agent', 'tool_start', {'run_id': r, 'name': 'run_command', 'arguments': args, 'side': 'agent',
                              'title': 'rm -rf build'})
a = s('agent', 'approval_request', {'run_id': r, 'tool_call_id': t, 'name': 'run_command', 'arguments': args,
                                    'digest': digest(args), 'reason': 'dangerous', 'scopes': ['once', 'session'],
                                    'expires': '2026-11-12T14:00:00Z'})
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': 'build/ borrada'})
s('agent', 'diff_updated', {'run_id': r, 'files': [{'path': 'build/app', 'added': 0, 'removed': 12}]})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/02-aprobacion.jsonl')

# 03: herramienta del cliente (cierra el hueco 3 del 0.1) y steer.
herr = [{'name': 'clipboard_read', 'description': 'Lee el portapapeles', 'input_schema': {'type': 'object'}}]
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('client', 'tool_end', {'tool_call_id': t, 'status': 'success', 'output': texto('Hello world')}, reply_to=t)
s('client', 'input', {'blocks': texto('Al portugués, mejor.'), 'mode': 'steer', 'run_id': r})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Olá, mundo.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/03-herramienta-del-cliente.jsonl')

# 04: Chiyo saluda; expresión y estado compartido con raíz del cliente.
s = Sesion(); inicio(s, ['expression', 'shared_state'],
                     render={'expression': {'emotions': ['happy', 'neutral'], 'gestures': ['wave']}})
s('client', 'state_delta', {'patch': [{'op': 'add', 'path': '/client/surface', 'value': 'widget'}]})
e = s('client', 'input', {'blocks': texto('Hola, Chiyo.')})
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant',
                                 'blocks': texto('¡Hola! ¿Ya terminaste de programar?')})
s('agent', 'expression', {'run_id': r, 'message_id': m, 'emotion': 'happy', 'intensity': 0.8, 'gesture': 'wave',
                          'voice_style': 'cheerful', 'duration_ms': 4000})
s('agent', 'message_end', {'message_id': m})
s('agent', 'state_delta', {'patch': [{'op': 'replace', 'path': '/agent/mood', 'value': 'happy'}]})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/04-expresion.jsonl')

# 05: extensión con nombre e interrupción.
s = Sesion(); inicio(s, ext=['alfalfa'])
e = s('client', 'input', {'blocks': texto('Ejecuta las pruebas.')})
r = s('agent', 'run_started', {'input_id': e})
s('agent', 'alfalfa.budget', {'spent': 0.12, 'limit': 2.0, 'currency': 'USD'})
s('client', 'interrupt', {'run_id': r})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s.write('valid/05-extension-e-interrupcion.jsonl')

# Inválidos: una línea por caso; el campo "x_motivo" dice qué debe detectar el verificador.
def malo(motivo, **cambios):
    base = {'pacai': '0.2', 'id': 'm_99999999', 'session': SES, 'sender': 'client', 'seq': 1,
            'time': '2026-11-12T10:00:00Z', 'reply_to': 'm_00000001'}
    base.update(cambios)
    base['x_motivo'] = motivo
    return json.dumps(base, ensure_ascii=False) + '\n'

(D / 'invalid/mensajes.jsonl').write_text(''.join([
    malo('aprobada sin alcance', type='approval_result', payload={'decision': 'approved'}),
    malo('alcance en una negación', type='approval_result', payload={'decision': 'denied', 'scope': 'once'}),
    malo('decisión como cadena true', type='approval_result', payload={'decision': 'true', 'scope': 'once'}),
    malo('respuesta sin reply_to', type='approval_result', payload={'decision': 'denied'}, reply_to=None),
    malo('steer sin run_id', type='input', payload={'blocks': texto('x'), 'mode': 'steer'}),
    malo('versión equivocada', pacai='0.1', type='close', payload={}),
    malo('seq cero', seq=0, type='close', payload={}),
    malo('input enviado por el agente', sender='agent', type='input', payload={'blocks': texto('x')}),
    malo('fallo sin detalle', sender='agent', type='run_finished', payload={'run_id': 'm_00000002', 'outcome': 'failed'}),
    malo('digest mal formado', sender='agent', type='approval_request', payload={
        'run_id': 'm_00000002', 'tool_call_id': 'm_00000003', 'name': 'x', 'arguments': {}, 'digest': 'md5:abc',
        'reason': 'dangerous', 'scopes': ['once'], 'expires': '2026-11-12T11:00:00Z'}),
    malo('parche fuera de las raíces', type='state_delta', payload={'patch': [{'op': 'add', 'path': '/otro'}]}),
]).replace('"reply_to": null, ', ''))
print('ejemplos escritos')
