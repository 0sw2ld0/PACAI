"""El SDK acepta todos los ejemplos válidos y rechaza los inválidos de conformance/."""
import copy

import pytest

from conftest import MENSAJES_INVALIDOS, SESIONES_INVALIDAS, VALIDOS, leer
from pacai import Session, is_valid, validate


def test_hay_ejemplos():
    assert len(VALIDOS) >= 11 and len(SESIONES_INVALIDAS) >= 20 and len(MENSAJES_INVALIDOS) >= 30


@pytest.mark.parametrize('ruta', VALIDOS, ids=lambda r: r.name)
def test_sesion_valida(ruta):
    assert Session.check(leer(ruta)) == []


@pytest.mark.parametrize('ruta', VALIDOS, ids=lambda r: r.name)
def test_cada_mensaje_valido_cumple_el_esquema(ruta):
    for m in leer(ruta):
        assert validate(m) == [], m['id']


@pytest.mark.parametrize('m', MENSAJES_INVALIDOS, ids=lambda m: m['x_motivo'])
def test_mensaje_invalido(m):
    m = copy.deepcopy(m)
    del m['x_motivo']
    assert not is_valid(m)


@pytest.mark.parametrize('ruta', SESIONES_INVALIDAS, ids=lambda r: r.name)
def test_sesion_invalida_por_su_motivo(ruta):
    msgs = leer(ruta)
    motivo = msgs.pop(0)['x_motivo']
    problemas = Session.check(msgs)
    assert any(motivo in p for p in problemas), problemas


@pytest.mark.parametrize('ruta', VALIDOS, ids=lambda r: r.name)
def test_feed_incremental_igual_que_check(ruta):
    s = Session()
    for m in leer(ruta):
        assert s.feed(m) == []
    assert s.finish() == []
    assert s.active_runs == []
