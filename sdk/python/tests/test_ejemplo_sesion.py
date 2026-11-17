"""El cliente de ejemplos/sesion_con_alfalfa.py contra un agente falso hecho con el SDK, sin AlfalfaCode."""
import importlib.util
import sys
from pathlib import Path

from conftest import leer
from pacai import Session

SDK = Path(__file__).resolve().parents[1]

AGENTE_FALSO = '''
from pacai import MessageBuilder, StdioTransport

canal = StdioTransport()
for m in canal:
    if m['type'] == 'hello':
        agente = MessageBuilder('agent', m['session'])
        canal.send(agente.hello(profiles=['work'], extensions=['alfalfa'],
                                implementation={'name': 'falso', 'version': '1'}))
        canal.send(agente.session_started(m['id'], profiles=['work'], extensions=['alfalfa']))
    elif m['type'] == 'input':
        run = agente.run_started(m['id'])
        canal.send(run)
        canal.send(agente.message('alfalfa.budget', {'spent': 0.1, 'limit': 2.0}))
        herramienta = agente.tool_start(run['id'], 'run_command', {'argv': ['rm', '-rf', 'build']},
                                        title='rm -rf build')
        canal.send(herramienta)
        canal.send(agente.approval_request(herramienta, reason='dangerous', scopes=['once']))
    elif m['type'] == 'approval_result':
        canal.send(agente.tool_end(herramienta['id'], 'error', summary='permiso ' + m['payload']['decision']))
        for parte in agente.text_message(run['id'], 'No borré nada.'):
            canal.send(parte)
        canal.send(agente.run_finished(run['id']))
    elif m['type'] == 'close':
        break
'''


def cargar_ejemplo():
    spec = importlib.util.spec_from_file_location('sesion_con_alfalfa', SDK / 'ejemplos/sesion_con_alfalfa.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_niega_el_permiso_y_la_sesion_guardada_es_valida(tmp_path, monkeypatch, capsys):
    falso = tmp_path / 'agente_falso.py'
    falso.write_text(AGENTE_FALSO, encoding='utf-8')
    monkeypatch.setenv('PYTHONPATH', str(SDK))
    guardada = tmp_path / 'sesion.jsonl'

    codigo = cargar_ejemplo().main(['--guardar', str(guardada), 'Borra build.', '--', sys.executable, str(falso)])

    salida = capsys.readouterr().out
    assert codigo == 0, salida
    assert 'approval_request' in salida and 'run_command · dangerous · se niega' in salida
    assert '→ cliente  3  approval_result  denied' in salida
    assert 'tool_end         error · permiso denied' in salida
    assert 'alfalfa.budget' not in salida and '(sin enseñar: 1 mensajes' in salida
    assert 'Sesión correcta según pacai.Session.' in salida
    assert Session.check(leer(guardada)) == []


def test_todo_ensena_las_extensiones(tmp_path, monkeypatch, capsys):
    falso = tmp_path / 'agente_falso.py'
    falso.write_text(AGENTE_FALSO, encoding='utf-8')
    monkeypatch.setenv('PYTHONPATH', str(SDK))

    assert cargar_ejemplo().main(['--todo', '--', sys.executable, str(falso)]) == 0
    salida = capsys.readouterr().out
    assert 'alfalfa.budget' in salida and 'sin enseñar' not in salida
