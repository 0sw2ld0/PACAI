"""Genera los ejemplos de conformance/. Cada archivo .jsonl es una sesión completa.

Los ejemplos inválidos de sesión escritos a mano antes de 0.2 final (alcance no
ofrecido, digest, ejecución sin cerrar, raíz ajena y extensión) se conservan
tal cual; este script genera el resto.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

D = Path(__file__).parent
sys.path.insert(0, str(D.parent / 'sdk/python'))
from pacai.jcs import digest  # noqa: E402  (JCS, RFC 8785)

SES = 's_ejemplo_0123456789abcdef'
BASE = datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc)


class Sesion:
    def __init__(self):
        self.msgs, self.seq, self.n = [], {'agent': 0, 'client': 0}, 0
        self.t = BASE

    def crear(self, sender, type, payload, reply_to=None, **sobre):
        """Construye el mensaje siguiente sin añadirlo (un mensaje que se perdió por el camino)."""
        self.seq[sender] += 1
        self.n += 1
        self.t = datetime.fromisoformat(sobre['time'].replace('Z', '+00:00')) if 'time' in sobre \
            else self.t + timedelta(seconds=1)
        m = {'pacai': '0.2', 'id': f'm_{self.n:08d}', 'type': type, 'session': SES, 'sender': sender,
             'seq': self.seq[sender], 'time': self.t.strftime('%Y-%m-%dT%H:%M:%SZ'), 'payload': payload}
        if reply_to:
            m['reply_to'] = reply_to
        m.update(sobre)
        return m

    def __call__(self, sender, type, payload, reply_to=None, **sobre):
        m = self.crear(sender, type, payload, reply_to, **sobre)
        self.msgs.append(m)
        return m['id']

    def ultimo(self):
        return self.msgs[-1]

    def write(self, ruta, motivo=None):
        lineas = ([json.dumps({'x_motivo': motivo}, ensure_ascii=False) + '\n'] if motivo else []) + \
            [json.dumps(m, ensure_ascii=False) + '\n' for m in self.msgs]
        (D / ruta).write_text(''.join(lineas))


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


def herramienta(s, run, args, name='run_command', **extra):
    return s('agent', 'tool_start', {'run_id': run, 'name': name, 'arguments': args, 'side': 'agent', **extra})


def pedir(s, run, tool, args, scopes=('once', 'session'), name='run_command', reason='dangerous',
          expires='2026-11-12T14:00:00Z'):
    return s('agent', 'approval_request', {'run_id': run, 'tool_call_id': tool, 'name': name, 'arguments': args,
                                           'digest': digest(args), 'reason': reason, 'scopes': list(scopes),
                                           'expires': expires})


def subagente(s, madre, tarea, nombre='revisor'):
    """La ejecución madre lanza un subagente con una herramienta y este abre su subejecución (§4.9)."""
    t = herramienta(s, madre, {'task': tarea}, name='spawn_agent', title=f'Subagente: {tarea}')
    c = s('agent', 'run_started', {'parent_run_id': madre, 'tool_call_id': t,
                                   'agent': {'name': nombre, 'description': 'Revisa un módulo'}})
    return t, c


# 06: dos subagentes en paralelo; uno pide permiso con alcance session y el otro lo reutiliza.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Revisa los módulos api y web en paralelo.')})
r = s('agent', 'run_started', {'input_id': e})
t1, c1 = subagente(s, r, 'Revisar api/')
t2, c2 = subagente(s, r, 'Revisar web/')
m1 = s('agent', 'message_start', {'run_id': c1, 'role': 'assistant', 'blocks': texto('Leyendo api/… ')})
m2 = s('agent', 'message_start', {'run_id': c2, 'role': 'assistant', 'blocks': texto('Leyendo web/… ')})
args = {'argv': ['npm', 'test']}
k1 = herramienta(s, c1, args, title='npm test')
a = pedir(s, c1, k1, args, reason='policy')
s('client', 'approval_result', {'decision': 'approved', 'scope': 'session'}, reply_to=a)
s('agent', 'message_delta', {'message_id': m2, 'blocks': texto('sin cambios pendientes.')})
k2 = herramienta(s, c2, args, title='npm test', approval_id=a)
s('agent', 'tool_end', {'tool_call_id': k1, 'status': 'success', 'summary': '41 pruebas en verde'})
s('agent', 'tool_end', {'tool_call_id': k2, 'status': 'success', 'summary': '12 pruebas en verde'})
s('agent', 'message_end', {'message_id': m2})
s('agent', 'message_delta', {'message_id': m1, 'blocks': texto('todo correcto.')})
s('agent', 'message_end', {'message_id': m1})
s('agent', 'run_finished', {'run_id': c2, 'outcome': 'success'})
s('agent', 'tool_end', {'tool_call_id': t2, 'status': 'success', 'summary': 'web/ revisado'})
s('agent', 'run_finished', {'run_id': c1, 'outcome': 'success'})
s('agent', 'tool_end', {'tool_call_id': t1, 'status': 'success', 'summary': 'api/ revisado'})
T = '_tok' + 'ens'  # se arma así para que las herramientas de registro no lo confundan con un secreto
USO = {'run_id': r}
USO['input' + T] = 3200
USO['output' + T] = 410
s('agent', 'usage', USO)
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Los dos módulos están bien.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/06-subagentes-en-paralelo.jsonl')

# 07: aprobación con alcance session; repetir lo mismo no pregunta, otros argumentos sí.
s = Sesion(); inicio(s, ['work'])
e = s('client', 'input', {'blocks': texto('Formatea Sources y Tests.')})
r = s('agent', 'run_started', {'input_id': e})
args = {'argv': ['swift', 'format', '-i', '-r', 'Sources']}
t = herramienta(s, r, args, title='swift format Sources')
a = pedir(s, r, t, args, reason='outside_sandbox')
s('client', 'approval_result', {'decision': 'approved', 'scope': 'session'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
t = herramienta(s, r, {'argv': ['swift', 'format', '-i', '-r', 'Sources']}, title='otra vez', approval_id=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
otros = {'argv': ['swift', 'format', '-i', '-r', 'Tests']}
t = herramienta(s, r, otros, title='swift format Tests')
a = pedir(s, r, t, otros, scopes=['once'], reason='outside_sandbox')
s('client', 'approval_result', {'decision': 'denied', 'reason': 'Tests no'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'error', 'summary': 'Permiso denegado'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/07-aprobacion-de-sesion.jsonl')

# 08: reanudación sin reenvío: el agente salta seq y lo explica con snapshot.
s = Sesion(); inicio(s, ['work'])
e = s('client', 'input', {'blocks': texto('Actualiza las dependencias.')})
r = s('agent', 'run_started', {'input_id': e})
args = {'argv': ['npm', 'update']}
t = herramienta(s, r, args, title='npm update')
recibida = s.seq['agent']
# Se corta la conexión: estos mensajes del agente no llegan al cliente.
perdidos = [s.crear('agent', 'message_start', {'run_id': r, 'role': 'assistant',
                                               'blocks': texto('Necesito permiso para npm update.')})]
perdidos.append(s.crear('agent', 'message_end', {'message_id': perdidos[0]['id']}))
pedida = s.crear('agent', 'approval_request', {'run_id': r, 'tool_call_id': t, 'name': 'run_command',
                                               'arguments': args, 'digest': digest(args), 'reason': 'network',
                                               'scopes': ['once'], 'expires': '2026-11-12T14:00:00Z'})
h = s('client', 'hello', {'versions': ['0.2'], 'profiles': ['work'], 'extensions': [],
                          'resume_after_seq': recibida})
s('agent', 'session_started', {'version': '0.2', 'profiles': ['work'], 'extensions': [], 'resumed': True,
                               'resume_after_seq': s.seq['client'] - 1}, reply_to=h)
s('agent', 'snapshot', {'runs': [{'run_id': r, 'status': 'active'}], 'pending_approvals': [pedida],
                        'last_messages': perdidos}, reply_to=h)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=pedida['id'])
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': '3 paquetes actualizados'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/08-reanudacion-con-snapshot.jsonl')

# 09: reanudación con reenvío: el agente repite lo retenido y luego confirma.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Resume el capítulo.')})
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant'})
recibida = s.seq['agent']
h = s('client', 'hello', {'versions': ['0.2'], 'profiles': [], 'extensions': [], 'resume_after_seq': recibida})
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('Trata de un cuy viajero.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'session_started', {'version': '0.2', 'profiles': [], 'extensions': [], 'resumed': True,
                               'resume_after_seq': s.seq['client'] - 1}, reply_to=h)
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/09-reanudacion-con-reenvio.jsonl')

# 10: aprobación caducada: el agente la declara expired y un sí tardío no cuenta.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Publica la versión.')})
r = s('agent', 'run_started', {'input_id': e})
args = {'argv': ['git', 'push', '--tags']}
t = herramienta(s, r, args, title='git push --tags')
a = pedir(s, r, t, args, scopes=['once'], reason='network', expires='2026-11-12T10:05:00Z')
s('agent', 'approval_result', {'decision': 'expired'}, reply_to=a, time='2026-11-12T10:05:00Z')
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled', 'summary': 'Permiso caducado'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'blocked', 'detail': 'Sin permiso para publicar'})
s.write('valid/10-aprobacion-caducada.jsonl')

# 11: interrumpir la raíz interrumpe antes a sus subejecuciones.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Investiga tres librerías.')})
r = s('agent', 'run_started', {'input_id': e})
t1, c1 = subagente(s, r, 'Investigar A', 'investigador')
t2, c2 = subagente(s, r, 'Investigar B', 'investigador')
s('client', 'interrupt', {'run_id': r})
s('agent', 'run_finished', {'run_id': c1, 'outcome': 'interrupted'})
s('agent', 'tool_end', {'tool_call_id': t1, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': c2, 'outcome': 'interrupted'})
s('agent', 'tool_end', {'tool_call_id': t2, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s.write('valid/11-interrupcion-en-cascada.jsonl')

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
    # Subagentes (§4.9).
    malo('run_started sin input_id ni parent_run_id', sender='agent', type='run_started', payload={}),
    malo('run_started con input_id y parent_run_id', sender='agent', type='run_started',
         payload={'input_id': 'm_00000004', 'parent_run_id': 'm_00000005'}),
    malo('tool_call_id sin parent_run_id', sender='agent', type='run_started',
         payload={'input_id': 'm_00000004', 'tool_call_id': 'm_00000006'}),
    malo('subagente sin nombre', sender='agent', type='run_started',
         payload={'parent_run_id': 'm_00000005', 'agent': {'description': 'x'}}),
    # Reanudación (§6).
    malo('snapshot sin reply_to', sender='agent', type='snapshot', reply_to=None,
         payload={'runs': [], 'pending_approvals': []}),
    malo('snapshot sin pending_approvals', sender='agent', type='snapshot', payload={'runs': []}),
    malo('ejecución terminada sin outcome', sender='agent', type='snapshot',
         payload={'runs': [{'run_id': 'm_00000005', 'status': 'finished'}], 'pending_approvals': []}),
    malo('ejecución activa con outcome', sender='agent', type='snapshot',
         payload={'runs': [{'run_id': 'm_00000005', 'status': 'active', 'outcome': 'success'}],
                  'pending_approvals': []}),
    malo('pending_approvals con otro tipo', sender='agent', type='snapshot', payload={
        'runs': [], 'pending_approvals': [{'pacai': '0.2', 'id': 'm_00000009', 'type': 'close', 'session': SES,
                                           'sender': 'agent', 'seq': 4, 'time': '2026-11-12T10:00:00Z',
                                           'payload': {}}]}),
    malo('last_messages con un mensaje inválido', sender='agent', type='snapshot',
         payload={'runs': [], 'pending_approvals': [], 'last_messages': [{'type': 'message_end'}]}),
    malo('snapshot enviado por el cliente', type='snapshot', payload={'runs': [], 'pending_approvals': []}),
    # Aprobaciones (§4.5).
    malo('expired enviado por el cliente', type='approval_result', payload={'decision': 'expired'}),
    malo('aprobación enviada por el agente', sender='agent', type='approval_result',
         payload={'decision': 'approved', 'scope': 'once'}),
    malo('alcance desconocido', type='approval_result', payload={'decision': 'approved', 'scope': 'forever'}),
    malo('scopes vacío', sender='agent', type='approval_request', payload={
        'run_id': 'm_00000002', 'tool_call_id': 'm_00000003', 'name': 'x', 'arguments': {},
        'digest': digest({}), 'reason': 'dangerous', 'scopes': [], 'expires': '2026-11-12T11:00:00Z'}),
    malo('approval_id demasiado corto', sender='agent', type='tool_start', payload={
        'run_id': 'm_00000002', 'name': 'x', 'arguments': {}, 'side': 'agent', 'approval_id': 'a1'}),
    # Coherencia del núcleo.
    malo('tool_end del cliente sin reply_to', type='tool_end', reply_to=None,
         payload={'tool_call_id': 'm_00000003', 'status': 'success'}),
    malo('código de error con mayúsculas', type='error', payload={'code': 'Unknown_Run', 'message': 'x'}),
    malo('heartbeat sin last_seq', type='heartbeat', payload={}),
    malo('session_started sin reply_to', sender='agent', type='session_started', reply_to=None,
         payload={'version': '0.2', 'profiles': [], 'extensions': []}),
]).replace('"reply_to": null, ', ''))


# Inválidos de sesión: la primera línea lleva x_motivo, un trozo del problema esperado.
def raiz(s, perfiles=(), **hello):
    inicio(s, perfiles, **hello)
    e = s('client', 'input', {'blocks': texto('Haz el trabajo.')})
    return s('agent', 'run_started', {'input_id': e})


def cerrar(s, *runs):
    for r in runs:
        s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})


S = 'invalid/sesiones/'

s = Sesion(); r = raiz(s)
c = s('agent', 'run_started', {'parent_run_id': 'm_77777777'})
cerrar(s, c, r)
s.write(S + 'subagente-sin-madre.jsonl', 'parent_run_id no es una ejecución activa')

s = Sesion(); r = raiz(s)
t, c = subagente(s, r, 'Revisar api/')
cerrar(s, r, c)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
s.write(S + 'madre-termina-antes-que-el-subagente.jsonl', 'termina antes que sus subejecuciones')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, {'task': 'x'}, name='spawn_agent')
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
c = s('agent', 'run_started', {'parent_run_id': r, 'tool_call_id': t})
cerrar(s, c, r)
s.write(S + 'subagente-de-herramienta-cerrada.jsonl', 'tool_call_id no es una herramienta abierta')

s = Sesion(); r = raiz(s)
e = s('client', 'input', {'blocks': texto('Y otra cosa.')})
r2 = s('agent', 'run_started', {'input_id': e})
cerrar(s, r, r2)
s.write(S + 'dos-ejecuciones-raiz-a-la-vez.jsonl', 'abre una ejecución raíz con')

s = Sesion(); r = raiz(s)
cerrar(s, r)
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Tarde.')})
s('agent', 'message_end', {'message_id': m})
s.write(S + 'mensaje-de-ejecucion-terminada.jsonl', 'no es una ejecución activa')

args = {'argv': ['npm', 'test']}
s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'session'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
t = herramienta(s, r, {'argv': ['npm', 'publish']}, approval_id=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
cerrar(s, r)
s.write(S + 'aprobacion-de-sesion-con-otros-argumentos.jsonl', 'approval_id no autoriza: otra herramienta u otros argumentos')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
t = herramienta(s, r, args, approval_id=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
cerrar(s, r)
s.write(S + 'aprobacion-once-reutilizada.jsonl', 'approval_id no autoriza: no es una aprobación session vigente')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args)
s('client', 'approval_result', {'decision': 'denied'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
cerrar(s, r)
s.write(S + 'ejecutada-tras-negacion.jsonl', 'herramienta ejecutada sin aprobación vigente')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, expires='2026-11-12T11:00:00Z')
s('agent', 'approval_result', {'decision': 'expired'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
cerrar(s, r)
s.write(S + 'caducada-antes-de-tiempo.jsonl', 'declara caducada una petición antes de expires')

s = Sesion(); r = raiz(s)
t = s('agent', 'tool_start', {'run_id': r, 'name': 'camera_photo', 'arguments': {}, 'side': 'client'})
s('client', 'tool_end', {'tool_call_id': t, 'status': 'error'}, reply_to=t)
cerrar(s, r)
s.write(S + 'herramienta-del-cliente-no-declarada.jsonl', 'no declarada en client_tools')


def reconectar(s, perfiles=(), salto=0):
    """El cliente vuelve con hello + resume_after_seq; el agente contesta resumed (con salto de seq)."""
    h = s('client', 'hello', {'versions': ['0.2'], 'profiles': list(perfiles), 'extensions': [],
                              'resume_after_seq': s.seq['agent']})
    s.seq['agent'] += salto
    s('agent', 'session_started', {'version': '0.2', 'profiles': list(perfiles), 'extensions': [],
                                   'resumed': True}, reply_to=h)
    return h


s = Sesion(); r = raiz(s)
h = reconectar(s, salto=3)
cerrar(s, r)
s.write(S + 'salto-de-seq-sin-snapshot.jsonl', 'salto de seq sin snapshot')

s = Sesion(); r = raiz(s)
cerrar(s, r)
h = reconectar(s, salto=2)
s('agent', 'snapshot', {'runs': [{'run_id': r, 'status': 'active'}], 'pending_approvals': []}, reply_to=h)
s.write(S + 'snapshot-relanza-ejecucion-terminada.jsonl', 'relanza la ejecución terminada')

s = Sesion(); r = raiz(s)
h = reconectar(s, salto=2)
s('agent', 'snapshot', {'runs': [], 'pending_approvals': []}, reply_to=h)
cerrar(s, r)
s.write(S + 'snapshot-omite-ejecucion-activa.jsonl', 'el snapshot omite la ejecución activa')

s = Sesion(); r = raiz(s)
s('agent', 'snapshot', {'runs': [{'run_id': r, 'status': 'active'}], 'pending_approvals': []},
  reply_to='m_00000001')
cerrar(s, r)
s.write(S + 'snapshot-fuera-de-reanudacion.jsonl', 'snapshot fuera de una reanudación')

s = Sesion(); r = raiz(s, ['work'])
h = reconectar(s, perfiles=['work', 'expression'])
cerrar(s, r)
s.write(S + 'reanudacion-cambia-perfiles.jsonl', 'la reanudación cambia perfiles o extensiones')

# Sustituye al archivo escrito a mano, que además tenía los seq desordenados.
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'output': texto('Hello world')})
cerrar(s, r)
s.write(S + 'tool-end-del-lado-equivocado.jsonl', 'lo cierra agent y la herramienta es del lado client')
print('ejemplos escritos')
