"""Verificador de PACAI 0.2: esquema más reglas de sesión.

Uso: python3 conformance/verificar.py [archivo.jsonl ...]
Sin argumentos comprueba conformance/valid (todo debe pasar),
conformance/invalid/mensajes.jsonl (cada línea debe fallar el esquema) y
conformance/invalid/sesiones (cada sesión debe fallar por el motivo indicado
en su primera línea, ``x_motivo``). No es normativo: la autoridad es
spec/PACAI-0.2.md.

Las reglas viven en el SDK de Python (sdk/python/pacai/session.py), para que
verificador y SDK no puedan divergir. Solo necesita ``jsonschema``.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'sdk/python'))

from pacai import Session, digest, validate  # noqa: E402

__all__ = ['digest', 'errores_de_esquema', 'verificar_sesion', 'leer']


def errores_de_esquema(m):
    return validate(m)


def verificar_sesion(msgs):
    """Esquema y reglas de sesión. Devuelve la lista de problemas."""
    return Session.check(msgs)


def leer(ruta):
    return [json.loads(linea) for linea in Path(ruta).read_text(encoding='utf-8').splitlines() if linea.strip()]


def _informe(nombre, fallos):
    print(('FALLA ' if fallos else 'OK    ') + nombre)
    for f in fallos:
        print('  - ' + f)


def main(rutas):
    if rutas:
        malos = 0
        for r in rutas:
            f = verificar_sesion(leer(r))
            _informe(str(r), f)
            malos += bool(f)
        return 1 if malos else 0
    total = 0
    for r in sorted((RAIZ / 'conformance/valid').glob('*.jsonl')):
        f = verificar_sesion(leer(r))
        _informe(r.name, f)
        total += bool(f)
    for r in sorted((RAIZ / 'conformance/invalid').glob('*.jsonl')):
        for m in leer(r):
            motivo = m.pop('x_motivo', '?')
            if errores_de_esquema(m):
                print('OK    rechazado:', motivo)
            else:
                print('FALLA aceptado y debía rechazarse:', motivo)
                total += 1
    for r in sorted((RAIZ / 'conformance/invalid/sesiones').glob('*.jsonl')):
        msgs = leer(r)
        motivo = msgs.pop(0)['x_motivo']
        f = verificar_sesion(msgs)
        if any(motivo in x for x in f):
            print('OK    sesión rechazada:', motivo)
        else:
            print('FALLA sesión no rechazada por el motivo esperado:', r.name, f)
            total += 1
    print('resultado:', 'todo correcto' if not total else f'{total} problemas')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
