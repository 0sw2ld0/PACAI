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
        m = {'pacai': '0.3', 'id': f'm_{self.n:08d}', 'type': type, 'session': SES, 'sender': sender,
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
    h = s('client', 'hello', {'versions': ['0.3'], 'profiles': list(perfiles), 'extensions': list(ext), **hello})
    s('agent', 'hello', {'versions': ['0.3'], 'profiles': list(perfiles), 'extensions': list(ext)})
    s('agent', 'session_started', {'version': '0.3', 'profiles': list(perfiles), 'extensions': list(ext),
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
    """approval_request de un tool_start abierto. Con expires=None no caduca (§4.5)."""
    p = {'run_id': run, 'tool_call_id': tool, 'name': name, 'arguments': args, 'digest': digest(args),
         'reason': reason, 'scopes': list(scopes)}
    if expires is not None:
        p['expires'] = expires
    return s('agent', 'approval_request', p)


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
h = s('client', 'hello', {'versions': ['0.3'], 'profiles': ['work'], 'extensions': [],
                          'resume_after_seq': recibida})
s('agent', 'session_started', {'version': '0.3', 'profiles': ['work'], 'extensions': [], 'resumed': True,
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
h = s('client', 'hello', {'versions': ['0.3'], 'profiles': [], 'extensions': [], 'resume_after_seq': recibida})
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('Trata de un cuy viajero.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'session_started', {'version': '0.3', 'profiles': [], 'extensions': [], 'resumed': True,
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

# -- 0.3 ----------------------------------------------------------------
# 12: subagentes en segundo plano: spawn_agent vuelve en el acto y el subagente sigue (§4.9).
#     La raíz espera a uno e interrumpe al otro; su herramienta ya terminó, así que no hay más que cerrar.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Revisa api/ y web/ en segundo plano.')})
r = s('agent', 'run_started', {'input_id': e})
t1, c1 = subagente(s, r, 'Revisar api/')
s('agent', 'tool_end', {'tool_call_id': t1, 'status': 'success', 'summary': 'Lanzado en segundo plano'})
t2, c2 = subagente(s, r, 'Revisar web/')
s('agent', 'tool_end', {'tool_call_id': t2, 'status': 'success', 'summary': 'Lanzado en segundo plano'})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Espero a los revisores.')})
s('agent', 'message_end', {'message_id': m})
m1 = s('agent', 'message_start', {'run_id': c1, 'role': 'assistant', 'blocks': texto('api/ está bien.')})
s('agent', 'message_end', {'message_id': m1})
s('agent', 'run_finished', {'run_id': c1, 'outcome': 'success'})
s('client', 'interrupt', {'run_id': c2})
s('agent', 'run_finished', {'run_id': c2, 'outcome': 'interrupted'})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('api/ revisado; web/ lo paraste.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/12-subagentes-en-segundo-plano.jsonl')

# 13: interrumpir con una herramienta del cliente abierta: el agente la cancela y el resultado tardío se ignora (§4.4).
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('client', 'interrupt', {'run_id': r})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s('client', 'tool_end', {'tool_call_id': t, 'status': 'success', 'output': texto('Hello world')}, reply_to=t)
e = s('client', 'input', {'blocks': texto('Déjalo, gracias.')})
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('De acuerdo.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/13-cancelar-herramienta-del-cliente.jsonl')

# 14: el cliente encadena su primera entrada tras el hello, sin esperar a session_started (§4.1).
s = Sesion()
h = s('client', 'hello', {'versions': ['0.3', '0.2'], 'profiles': [], 'extensions': []})
e = s('client', 'input', {'blocks': texto('¿Qué hora es en Lima?')})
s('agent', 'hello', {'versions': ['0.3'], 'profiles': [], 'extensions': []})
s('agent', 'session_started', {'version': '0.3', 'profiles': [], 'extensions': []}, reply_to=h)
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Son las 5:00.')})
s('agent', 'message_end', {'message_id': m})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/14-encadenar-tras-el-hello.jsonl')

# 15: aprobación sin expires; al interrumpir, el agente la cancela de forma explícita y un sí tardío no cuenta (§4.5).
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Publica la versión.')})
r = s('agent', 'run_started', {'input_id': e})
args = {'argv': ['git', 'push', '--tags']}
t = herramienta(s, r, args, title='git push --tags')
a = pedir(s, r, t, args, scopes=['once'], reason='network', expires=None)
s('client', 'interrupt', {'run_id': r})
s('agent', 'approval_result', {'decision': 'cancelled'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s.write('valid/15-aprobacion-sin-caducidad-cancelada.jsonl')

# 16: argumentos reales con un secreto tachado (el digest cubre lo que se ve), argumentos acortados sin
#     aprobación y diff acumulado de la ejecución (§4.4, §7.3).
s = Sesion(); inicio(s, ['work'])
e = s('client', 'input', {'blocks': texto('Despliega y guarda el informe.')})
r = s('agent', 'run_started', {'input_id': e})
args = {'argv': ['deploy', '--target', 'staging'], 'env': {'DEPLOY_TOKEN': '[redacted]'}}
t = herramienta(s, r, args, title='deploy --target staging')
a = pedir(s, r, t, args, scopes=['once'], reason='network', expires=None)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': 'Desplegado en staging'})
s('agent', 'diff_updated', {'run_id': r, 'files': [{'path': 'deploy.log', 'added': 3, 'removed': 0}]})
t = herramienta(s, r, {'path': 'informe.md', 'content': '# Informe\n\nLínea 1…'}, name='write_file',
                title='Escribir informe.md', truncated=True)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
s('agent', 'diff_updated', {'run_id': r, 'files': [{'path': 'deploy.log', 'added': 3, 'removed': 0},
                                                   {'path': 'informe.md', 'added': 40, 'removed': 0}]})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/16-argumentos-reales.jsonl')

# 17: cancelaciones que se cruzan: el agente cancela justo cuando llega la respuesta del cliente; vale el cancelled.
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié y publícalo.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
args = {'argv': ['git', 'push']}
k = herramienta(s, r, args, title='git push')
a = pedir(s, r, k, args, scopes=['once'], reason='network', expires=None)
s('client', 'interrupt', {'run_id': r})
s('client', 'tool_end', {'tool_call_id': t, 'status': 'success', 'output': texto('Hello world')}, reply_to=t)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'approval_result', {'decision': 'cancelled'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': k, 'status': 'cancelled'})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s.write('valid/17-cancelaciones-cruzadas.jsonl')

# 18: la «Sesión típica» del README: un mensaje en streaming y una herramienta que pide permiso.
s = Sesion(); inicio(s)
e = s('client', 'input', {'blocks': texto('Borra la carpeta build.')})
r = s('agent', 'run_started', {'input_id': e})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant'})
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('Voy a borrar build/; antes te pido permiso.')})
s('agent', 'message_end', {'message_id': m})
args = {'argv': ['rm', '-rf', 'build']}
t = herramienta(s, r, args, title='rm -rf build')
a = pedir(s, r, t, args, scopes=['once'], expires=None)
s('client', 'approval_result', {'decision': 'approved', 'scope': 'once'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': 'build/ borrada'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'})
s.write('valid/18-sesion-tipica.jsonl')

# El README enseña esta misma sesión: se reescribe entre sus marcas para que no se separen.
README = D.parent / 'README.md'
MARCA_INICIO, MARCA_FIN = '<!-- sesion-tipica:inicio -->', '<!-- sesion-tipica:fin -->'
antes, resto = README.read_text().split(MARCA_INICIO, 1)
_, despues = resto.split(MARCA_FIN, 1)
bloque = '\n```jsonl\n' + ''.join(json.dumps(m, ensure_ascii=False) + '\n' for m in s.msgs) + '```\n'
README.write_text(antes + MARCA_INICIO + bloque + MARCA_FIN + despues)


# 19: un observador (spec/propuestas/observadores.md) mira una sesión en marcha sin participar. Es su propia sesión
# PACAI: la foto inicial (snapshot) trae lo que está en marcha y después llega la copia de lo que ve el dueño, con los
# mismos id; la decisión del dueño le llega reenviada (relayed). Él solo manda hello, heartbeat, error y close.
def del_dueno(n, type, payload, seq):
    """Un mensaje que el agente mandó al dueño antes de que llegara el observador, dentro de la foto."""
    return {'pacai': '0.3', 'id': f'd_{n:08d}', 'type': type, 'session': SES, 'sender': 'agent', 'seq': seq,
            'time': '2026-11-12T09:59:00Z', 'payload': payload}


s = Sesion()
h = s('client', 'hello', {'versions': ['0.3'], 'profiles': ['work'], 'extensions': [], 'observe': True})
s('agent', 'hello', {'versions': ['0.3'], 'profiles': ['work'], 'extensions': []})
s('agent', 'session_started', {'version': '0.3', 'profiles': ['work'], 'extensions': [], 'observe': True,
                               'agent': {'name': 'ejemplo', 'version': '0.0.1'}}, reply_to=h)
args = {'argv': ['rm', '-rf', 'build']}
r, t, a = 'd_00000001', 'd_00000002', 'd_00000003'
s('agent', 'snapshot', {
    'runs': [{'run_id': r, 'status': 'active'}],
    'pending_approvals': [del_dueno(3, 'approval_request', {
        'run_id': r, 'tool_call_id': t, 'name': 'run_command', 'arguments': args, 'digest': digest(args),
        'reason': 'dangerous', 'scopes': ['once']}, 5)],
    'last_messages': [del_dueno(1, 'run_started', {'input_id': 'd_entrada1'}, 3),
                      del_dueno(2, 'tool_start', {'run_id': r, 'name': 'run_command', 'arguments': args,
                                                  'side': 'agent', 'title': 'rm -rf build'}, 4)]}, reply_to=h)
s('agent', 'approval_result', {'decision': 'approved', 'scope': 'once', 'relayed': True}, reply_to=a)
s('client', 'heartbeat', {'last_seq': s.seq['agent']})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': 'build/ borrada'}, id='d_00000004')
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant'}, id='d_00000005')
s('agent', 'message_delta', {'message_id': m, 'blocks': texto('Listo: build/ ya no existe.')}, id='d_00000006')
s('agent', 'message_end', {'message_id': m}, id='d_00000007')
s('agent', 'run_finished', {'run_id': r, 'outcome': 'success'}, id='d_00000008')
s('agent', 'close', {'reason': 'Fin del encargo'}, id='d_00000009')
s.write('valid/19-observador.jsonl')

# Inválidos: una línea por caso; el campo "x_motivo" dice qué debe detectar el verificador.
def malo(motivo, **cambios):
    base = {'pacai': '0.3', 'id': 'm_99999999', 'session': SES, 'sender': 'client', 'seq': 1,
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
    malo('versión anterior', pacai='0.2', type='close', payload={}),
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
        'runs': [], 'pending_approvals': [{'pacai': '0.3', 'id': 'm_00000009', 'type': 'close', 'session': SES,
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
         payload={'version': '0.3', 'profiles': [], 'extensions': []}),
    # 0.3: cancelled solo lo envía el agente; truncated solo en el lado del agente y sin approval_id.
    malo('cancelled enviado por el cliente', type='approval_result', payload={'decision': 'cancelled'}),
    malo('cancelled con alcance', sender='agent', type='approval_result',
         payload={'decision': 'cancelled', 'scope': 'once'}),
    malo('truncated en una herramienta del cliente', sender='agent', type='tool_start', reply_to=None, payload={
        'run_id': 'm_00000002', 'name': 'x', 'arguments': {}, 'side': 'client', 'truncated': True}),
    malo('truncated con approval_id', sender='agent', type='tool_start', reply_to=None, payload={
        'run_id': 'm_00000002', 'name': 'x', 'arguments': {}, 'side': 'agent', 'truncated': True,
        'approval_id': 'm_00000007'}),
    malo('truncated que no es booleano', sender='agent', type='tool_start', reply_to=None, payload={
        'run_id': 'm_00000002', 'name': 'x', 'arguments': {}, 'side': 'agent', 'truncated': 'yes'}),
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
    h = s('client', 'hello', {'versions': ['0.3'], 'profiles': list(perfiles), 'extensions': [],
                              'resume_after_seq': s.seq['agent']})
    s.seq['agent'] += salto
    s('agent', 'session_started', {'version': '0.3', 'profiles': list(perfiles), 'extensions': [],
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

# El cliente no cierra una herramienta del agente.
s = Sesion(); r = raiz(s)
t = herramienta(s, r, {'argv': ['ls']})
s('client', 'tool_end', {'tool_call_id': t, 'status': 'success'}, reply_to=t)
cerrar(s, r)
s.write(S + 'tool-end-del-lado-equivocado.jsonl', 'lo cierra client y la herramienta es del lado agent')

# -- 0.3 ----------------------------------------------------------------
# El agente solo cierra una herramienta del cliente para cancelarla (§4.4).
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'output': texto('Hello world')})
cerrar(s, r)
s.write(S + 'agente-cierra-herramienta-del-cliente-sin-cancelar.jsonl',
        'el agente solo puede cerrar una herramienta del cliente con cancelled')

# Tras cancelar una herramienta del cliente, la ejecución se cierra: nada de trabajo nuevo (§4.2).
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
m = s('agent', 'message_start', {'run_id': r, 'role': 'assistant', 'blocks': texto('Sigo sin el portapapeles.')})
s('agent', 'message_end', {'message_id': m})
cerrar(s, r)
s.write(S + 'trabajo-tras-cancelar-herramienta-del-cliente.jsonl', 'que se está cerrando')

# Tras cancelar una aprobación, tampoco (§4.5).
s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, expires=None)
s('agent', 'approval_result', {'decision': 'cancelled'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
t = herramienta(s, r, {'argv': ['npm', 'ci']})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
cerrar(s, r)
s.write(S + 'trabajo-tras-cancelar-aprobacion.jsonl', 'tool_start en la ejecución')

# Ni subagentes nuevos.
s = Sesion(); inicio(s, client_tools=herr)
e = s('client', 'input', {'blocks': texto('Traduce lo que copié.')})
r = s('agent', 'run_started', {'input_id': e})
t = s('agent', 'tool_start', {'run_id': r, 'name': 'clipboard_read', 'arguments': {}, 'side': 'client'})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
c = s('agent', 'run_started', {'parent_run_id': r, 'agent': {'name': 'traductor'}})
cerrar(s, c, r)
s.write(S + 'subagente-de-ejecucion-que-se-cierra.jsonl', 'parent_run_id es una ejecución que se está cerrando')

# Encadenar vale tras el hello del cliente, no antes (§4.1).
s = Sesion()
s('client', 'input', {'blocks': texto('Hola.')})
inicio(s)
s.write(S + 'input-antes-del-hello.jsonl', 'input antes del hello del cliente')

# El agente no encadena: nada antes de su session_started.
s = Sesion()
h = s('client', 'hello', {'versions': ['0.3']})
s('agent', 'hello', {'versions': ['0.3']})
s('agent', 'usage', {'input' + T: 1})
s('agent', 'session_started', {'version': '0.3', 'profiles': [], 'extensions': []}, reply_to=h)
s.write(S + 'agente-antes-de-session-started.jsonl', 'usage antes de session_started')

# Lo encadenado se juzga con lo negociado.
s = Sesion()
h = s('client', 'hello', {'versions': ['0.3'], 'profiles': ['shared_state']})
s('client', 'state_delta', {'patch': [{'op': 'add', 'path': '/client/surface', 'value': 'widget'}]})
s('agent', 'hello', {'versions': ['0.3'], 'profiles': []})
s('agent', 'session_started', {'version': '0.3', 'profiles': [], 'extensions': []}, reply_to=h)
s.write(S + 'encadenado-de-perfil-no-negociado.jsonl', 'perfil shared_state no negociado')

# Una petición sin expires no caduca (§4.5).
s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, expires=None)
s('agent', 'approval_result', {'decision': 'expired'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
cerrar(s, r)
s.write(S + 'caducada-sin-expires.jsonl', 'declara caducada una petición sin expires')

# Interrumpir no resuelve en silencio: antes del tool_end va el cancelled (§4.5, §4.6).
s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, expires=None)
s('client', 'interrupt', {'run_id': r})
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'cancelled'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s.write(S + 'herramienta-cerrada-con-aprobacion-pendiente.jsonl', 'cierra la herramienta con su aprobación pendiente')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, expires=None)
s('client', 'interrupt', {'run_id': r})
s('agent', 'approval_result', {'decision': 'cancelled'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'error'})
s('agent', 'run_finished', {'run_id': r, 'outcome': 'interrupted'})
s.write(S + 'aprobacion-cancelada-cerrada-con-error.jsonl', 'se cierra con cancelled')

# No se aprueba lo que no se ve entero (§4.4).
s = Sesion(); r = raiz(s)
grande = {'path': 'datos.csv', 'content': 'a,b\n1,2\n…'}
t = herramienta(s, r, grande, name='write_file', truncated=True)
a = pedir(s, r, t, grande, name='write_file', reason='outside_sandbox', expires=None)
s('client', 'approval_result', {'decision': 'denied'}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'error'})
cerrar(s, r)
s.write(S + 'aprobacion-de-llamada-truncada.jsonl', 'approval_request de una llamada con truncated')

# Un subagente en segundo plano no sobrevive a su raíz (§4.9).
s = Sesion(); r = raiz(s)
t, c = subagente(s, r, 'Revisar api/')
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success', 'summary': 'Lanzado en segundo plano'})
cerrar(s, r, c)
s.write(S + 'subagente-en-segundo-plano-sobrevive-a-la-raiz.jsonl', 'termina antes que sus subejecuciones')
# Un observador solo mira (propuesta de observadores).
s = Sesion()
h = s('client', 'hello', {'versions': ['0.3'], 'profiles': [], 'extensions': [], 'observe': True})
s('agent', 'hello', {'versions': ['0.3'], 'profiles': [], 'extensions': []})
s('agent', 'session_started', {'version': '0.3', 'profiles': [], 'extensions': [], 'observe': True}, reply_to=h)
s('agent', 'snapshot', {'runs': [], 'pending_approvals': []}, reply_to=h)
s('client', 'input', {'blocks': texto('Borra todo.')})
s.write(S + 'observador-envia-input.jsonl', 'un observador solo envía heartbeat, error y close')

s = Sesion(); r = raiz(s)
t = herramienta(s, r, args)
a = pedir(s, r, t, args, scopes=['once'], expires=None)
s('agent', 'approval_result', {'decision': 'approved', 'scope': 'once', 'relayed': True}, reply_to=a)
s('agent', 'tool_end', {'tool_call_id': t, 'status': 'success'})
cerrar(s, r)
s.write(S + 'decision-reenviada-sin-observador.jsonl', 'relayed solo lo envía el agente, en la sesión de un observador')
print('ejemplos escritos')
