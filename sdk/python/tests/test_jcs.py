"""JCS (RFC 8785) con los vectores de la propia RFC."""
import hashlib
import json

import pytest

from conftest import VALIDOS, leer
from pacai import canonicalize, digest


@pytest.mark.parametrize('valor, esperado', [
    (0.0, '0'), (-0.0, '0'), (1.0, '1'), (-1.5, '-1.5'), (4.50, '4.5'), (2e-3, '0.002'),
    (333333333.33333329, '333333333.3333333'), (1e30, '1e+30'), (1e21, '1e+21'), (1e20, '100000000000000000000'),
    (1e-6, '0.000001'), (1e-7, '1e-7'), (0.000000000000000000000000001, '1e-27'),
    (5e-324, '5e-324'), (1.7976931348623157e308, '1.7976931348623157e+308'),
    (9007199254740992, '9007199254740992'), (-123, '-123'), (295147905179352830000.0, '295147905179352830000'),
])
def test_numeros(valor, esperado):
    assert canonicalize(valor) == esperado


def test_orden_de_claves_por_utf16():
    # Ejemplo de ordenación de la RFC 8785, §3.2.3.
    obj = {'\u20ac': 'Euro Sign', '\r': 'Carriage Return', '\ufb33': 'Hebrew Letter Dalet With Dagesh',
           '1': 'One', '\U0001f600': 'Emoji: Grinning Face', '\u0080': 'Control', '\u00f6': 'Latin Small Letter O With Diaeresis'}
    claves = list(json.loads(canonicalize(obj)))
    assert claves == ['\r', '1', '\u0080', '\u00f6', '\u20ac', '\U0001f600', '\ufb33']


def test_ejemplo_completo_de_la_rfc():
    entrada = {'numbers': [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],
               'string': '\u20ac$\u000f\nA\'B"\\\\"/', 'literals': [None, True, False]}
    assert canonicalize(entrada) == ('{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,'
                                     '1e-27],"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}')


def test_sin_espacios_y_utf8():
    assert canonicalize({'b': [1, {'z': 'ñ', 'a': None}], 'a': 'x'}) == '{"a":"x","b":[1,{"a":null,"z":"ñ"}]}'


def test_rechaza_lo_que_no_es_json():
    with pytest.raises(ValueError):
        canonicalize(float('nan'))
    with pytest.raises(TypeError):
        canonicalize({1: 'x'})
    with pytest.raises(TypeError):
        canonicalize(object())


def test_digest():
    assert digest({}) == 'sha256:' + hashlib.sha256(b'{}').hexdigest()
    assert digest({'b': 1, 'a': 2}) == digest({'a': 2, 'b': 1})


@pytest.mark.parametrize('ruta', VALIDOS, ids=lambda r: r.name)
def test_digest_de_los_ejemplos(ruta):
    for m in leer(ruta):
        if m['type'] == 'approval_request':
            assert m['payload']['digest'] == digest(m['payload']['arguments'])
