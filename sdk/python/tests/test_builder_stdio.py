"""Constructor de mensajes, transporte stdio y reglas de Session vistas desde la API."""
import io
import itertools

import pytest

from conftest import VALIDOS, leer
from pacai import (MessageBuilder, MessageTooLarge, Session, StdioTransport, decode, digest, encode,
                   new_session_id, read_messages, validate)


def par(**kw):
    """Agente y cliente que comparten sesión, con ids y reloj deterministas."""
    n = itertools.count(1)
    ids = lambda: f'm_{next(n):08d}'  # noqa: E731
    reloj = lambda: '2026-11-12T10:00:00Z'  # noqa: E731
    cliente = MessageBuilder('client', 's_prueba_0123456789abcdef', ids=ids, clock=reloj)
    agente = MessageBuilder('agent', cliente.session, ids=ids, clock=reloj)
    return agente, cliente


def test_ids_y_sesion_aleatorios():
    s = new_session_id()
    assert len(s) >= 16 and s != new_session_id()
    b = MessageBuilder('agent')
    assert b.message('close')['id'] != b.message('close')['id']


def test_seq_por_emisor():
    agente, cliente = par()
    assert [cliente.close()['seq'], cliente.close()['seq']] == [1, 2]
    assert agente.close()['seq'] == 1


def test_sender_invalido():
    with pytest.raises(ValueError):
        MessageBuilder('server')


def test_hora_por_defecto_valida():
    m = MessageBuilder('agent').close('fin')
    assert validate(m) == []


def test_sesion_completa_construida_con_el_sdk():
    agente, cliente = par()
    h = cliente.hello(profiles=['work'])
    msgs = [h, agente.hello(profiles=['work']), agente.session_started(h['id'], profiles=['work'])]
    e = cliente.input('Borra build/')
    r = agente.run_started(e['id'])
    t = agente.tool_start(r['id'], 'run_command', {'argv': ['rm', '-rf', 'build']})
    a = agente.approval_request(t, reason='dangerous', expires='2026-11-12T14:00:00Z', scopes=['once', 'session'])
    assert a['payload']['digest'] == digest({'argv': ['rm', '-rf', 'build']})
    ok = cliente.approval_result(a['id'], 'approved', 'session')
    fin = agente.tool_end(t['id'], summary='hecho')
    t2 = agente.tool_start(r['id'], 'run_command', {'argv': ['rm', '-rf', 'build']}, approval_id=a['id'])
    msgs += [e, r, t, a, ok, fin, t2, agente.tool_end(t2['id']), *agente.text_message(r['id'], 'Listo.'),
             agente.run_finished(r['id']), cliente.close('fin')]
    s = Session()
    for m in msgs:
        assert s.feed(m) == [], m
    assert s.authorized_by_session('run_command', {'argv': ['rm', '-rf', 'build']}) == a['id']
    assert s.authorized_by_session('run_command', {'argv': ['rm', '-rf', '/']}) is None
    assert s.finish() == []


def test_tool_end_del_cliente_lleva_reply_to():
    agente, cliente = par()
    m = cliente.tool_end('m_00000042', output=[{'type': 'text', 'text': 'x'}])
    assert m['reply_to'] == 'm_00000042'
    assert 'reply_to' not in agente.tool_end('m_00000042')


def test_subejecucion_con_el_constructor():
    agente, _ = par()
    m = agente.run_started(parent_run_id='m_00000005', tool_call_id='m_00000006', agent={'name': 'revisor'})
    assert m['payload'] == {'parent_run_id': 'm_00000005', 'tool_call_id': 'm_00000006', 'agent': {'name': 'revisor'}}
    assert validate(m) == []


def test_retransmision_identica_se_descarta():
    msgs = leer(VALIDOS[0])
    s = Session()
    for m in msgs[:5]:
        s.feed(m)
    assert s.feed(dict(msgs[4])) == []          # mismo id y contenido: se ignora
    otro = dict(msgs[4], payload={'blocks': []})
    assert any('id repetido' in p for p in s.feed(otro))


def test_mensaje_antes_de_empezar():
    agente, cliente = par()
    problemas = Session.check([cliente.input('hola')], validate_schema=False)
    assert any('antes del hello del cliente' in p for p in problemas)
    agente, cliente = par()
    problemas = Session.check([cliente.hello(), agente.close()], validate_schema=False)
    assert problemas == []
    agente, cliente = par()
    problemas = Session.check([cliente.hello(), agente.message('usage', {})], validate_schema=False)
    assert any('usage antes de session_started' in p for p in problemas)


def test_encadenar_tras_el_hello():
    agente, cliente = par()
    h = cliente.hello()
    e = cliente.input('hola')
    msgs = [h, e, agente.hello(), agente.session_started(h['id'])]
    r = agente.run_started(e['id'])
    msgs += [r, *agente.text_message(r['id'], 'Hola.'), agente.run_finished(r['id'])]
    assert Session.check(msgs) == []


def test_aprobacion_sin_expires_y_cancelada():
    agente, cliente = par()
    h = cliente.hello()
    msgs = [h, agente.hello(), agente.session_started(h['id'])]
    e = cliente.input('Publica.')
    r = agente.run_started(e['id'])
    t = agente.tool_start(r['id'], 'run_command', {'argv': ['git', 'push']})
    a = agente.approval_request(t, reason='network')
    assert 'expires' not in a['payload'] and validate(a) == []
    msgs += [e, r, t, a, cliente.interrupt(r['id']), agente.cancel_approval(a['id']),
             agente.tool_end(t['id'], 'cancelled'), agente.run_finished(r['id'], 'interrupted'),
             cliente.approval_result(a['id'], 'approved', 'once')]
    assert Session.check(msgs) == []


def test_cancelar_herramienta_del_cliente():
    agente, cliente = par()
    herr = [{'name': 'clipboard_read', 'input_schema': {'type': 'object'}}]
    h = cliente.hello(client_tools=herr)
    msgs = [h, agente.hello(), agente.session_started(h['id'])]
    e = cliente.input('Traduce.')
    r = agente.run_started(e['id'])
    t = agente.tool_start(r['id'], 'clipboard_read', {}, side='client')
    fin = agente.cancel_client_tool(t['id'])
    assert 'reply_to' not in fin and fin['payload']['status'] == 'cancelled'
    tarde = cliente.tool_end(t['id'], output=[{'type': 'text', 'text': 'x'}])
    msgs += [e, r, t, fin, agente.run_finished(r['id'], 'interrupted'), tarde]
    assert Session.check(msgs) == []
    with pytest.raises(ValueError):
        cliente.cancel_client_tool(t['id'])


def test_no_se_aprueba_una_llamada_truncada():
    agente, _ = par()
    t = agente.tool_start('m_00000002', 'write_file', {'path': 'x', 'content': 'a…'}, truncated=True)
    with pytest.raises(ValueError):
        agente.approval_request(t, reason='outside_sandbox')


# -- stdio ---------------------------------------------------------------
def test_encode_compacto_en_una_linea():
    linea = encode({'a': 'línea 1\nlínea 2', 'b': [1, 2]})
    assert linea.endswith('\n') and linea.count('\n') == 1 and ', ' not in linea
    assert decode(linea) == {'a': 'línea 1\nlínea 2', 'b': [1, 2]}


@pytest.mark.parametrize('ruta', VALIDOS, ids=lambda r: r.name)
def test_ida_y_vuelta_jsonl(ruta):
    msgs = leer(ruta)
    t = StdioTransport.in_memory()
    for m in msgs:
        t.send(m)
    t.writer.seek(0)
    assert list(read_messages(t.writer)) == msgs
    assert list(StdioTransport(io.StringIO(t.writer.getvalue()), io.StringIO())) == msgs


def test_eof_es_none_y_salta_lineas_vacias():
    t = StdioTransport.in_memory('\n{"a":1}\n\n')
    assert t.receive() == {'a': 1}
    assert t.receive() is None


def test_limite_de_tamano():
    t = StdioTransport.in_memory('{"a":"' + 'x' * 2000 + '"}\n')
    t.max_bytes = 1024
    with pytest.raises(MessageTooLarge):
        t.receive()
    with pytest.raises(MessageTooLarge):
        t.send({'a': 'x' * 2000})


def test_limite_jsonl_cuenta_el_salto_de_linea(conformance):
    mensaje = next(m for m in leer(conformance / 'valid/01-texto.jsonl') if m['type'] == 'input')
    linea = encode(mensaje).encode('utf-8')
    limite = 1024
    exacta = linea[:-1] + b' ' * (limite - len(linea)) + b'\n'
    pasada = exacta[:-1] + b' \n'
    assert len(exacta) == limite and len(pasada) == limite + 1

    lector = StdioTransport.in_memory((exacta + pasada).decode('utf-8'))
    lector.max_bytes = limite
    assert lector.receive() == mensaje
    with pytest.raises(MessageTooLarge):
        lector.receive()
    assert list(read_messages(io.BytesIO(exacta), max_bytes=limite)) == [mensaje]
    with pytest.raises(MessageTooLarge):
        list(read_messages(io.BytesIO(pasada), max_bytes=limite))

    escritor = StdioTransport.in_memory()
    escritor.max_bytes = len(linea)
    escritor.send(mensaje)
    assert escritor.writer.getvalue().encode('utf-8') == linea
    escritor.max_bytes -= 1
    with pytest.raises(MessageTooLarge):
        escritor.send(mensaje)
    assert escritor.writer.getvalue().encode('utf-8') == linea


def test_decode_rechaza_lo_que_no_es_objeto():
    with pytest.raises(ValueError):
        decode('[1, 2]')
