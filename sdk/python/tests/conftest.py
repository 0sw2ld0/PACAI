import json
from pathlib import Path

import pytest

CONFORMANCE = Path(__file__).resolve().parents[3] / 'conformance'


def leer(ruta):
    return [json.loads(linea) for linea in ruta.read_text(encoding='utf-8').splitlines() if linea.strip()]


VALIDOS = sorted((CONFORMANCE / 'valid').glob('*.jsonl'))
SESIONES_INVALIDAS = sorted((CONFORMANCE / 'invalid/sesiones').glob('*.jsonl'))
MENSAJES_INVALIDOS = leer(CONFORMANCE / 'invalid/mensajes.jsonl')


@pytest.fixture
def conformance():
    return CONFORMANCE
