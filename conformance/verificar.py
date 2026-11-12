"""Verificador de PACAI 0.2: esquema más reglas de sesión.

Uso: python3 conformance/verificar.py [archivo.jsonl ...]
Sin argumentos comprueba conformance/valid (todo debe pasar) y
conformance/invalid (cada línea debe fallar). No es normativo: la autoridad
es spec/PACAI-0.2.md.
"""
import hashlib, json, sys
from pathlib import Path

import jsonschema

RAIZ = Path(__file__).resolve().parent.parent
ESQUEMA = json.loads((RAIZ / 'schema/pacai-0.2.schema.json').read_text())
VALIDADOR = jsonschema.Draft202012Validator(ESQUEMA, format_checker=jsonschema.FormatChecker())
PERFIL = {'voice_turn': 'voice', 'state_snapshot': 'shared_state', 'state_delta': 'shared_state',
          'plan_updated': 'work', 'diff_updated': 'work', 'expression': 'expression'}
CONTESTA_EL_OTRO = {'session_started': 'hello', 'approval_result': 'approval_request'}


def digest(args):
    canon = json.dumps(args, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return 'sha256:' + hashlib.sha256(canon.encode()).hexdigest()


def errores_de_esquema(m):
    return [e.message for e in VALIDADOR.iter_errors(m)]


def verificar_sesion(msgs):
    """Reglas que el esquema no puede ver. Devuelve la lista de problemas."""
    fallos, vistos, seq = [], {}, {'agent': 0, 'client': 0}
    activos = {'profiles': set(), 'extensions': set()}
    abiertas, herramientas = set(), {}
    for n, m in enumerate(msgs, 1):
        donde = f'línea {n} ({m.get("type")})'
        fallos += [f'{donde}: {e}' for e in errores_de_esquema(m)]
        t, emisor, p = m.get('type'), m.get('sender'), m.get('payload', {})
        if m.get('id') in vistos:
            fallos.append(f'{donde}: id repetido')
        vistos[m.get('id')] = m
        if emisor in seq:
            if m.get('seq') != seq[emisor] + 1:
                fallos.append(f'{donde}: seq {m.get("seq")} tras {seq[emisor]} del mismo emisor')
            seq[emisor] = m.get('seq', seq[emisor])
        ref = m.get('reply_to')
        if ref is not None:
            previo = vistos.get(ref)
            if previo is None or previo is m:
                fallos.append(f'{donde}: reply_to a un mensaje inexistente')
            elif previo.get('sender') == emisor:
                fallos.append(f'{donde}: responde a un mensaje propio')
            elif t in CONTESTA_EL_OTRO and previo.get('type') != CONTESTA_EL_OTRO[t]:
                fallos.append(f'{donde}: responde a un {previo.get("type")}')
        if t == 'session_started':
            activos['profiles'] = set(p.get('profiles', []))
            activos['extensions'] = set(p.get('extensions', []))
        if t in PERFIL and PERFIL[t] not in activos['profiles']:
            fallos.append(f'{donde}: perfil {PERFIL[t]} no negociado')
        if t and '.' in t and t.split('.')[0] not in activos['extensions']:
            fallos.append(f'{donde}: extensión {t.split(".")[0]} no negociada')
        if t == 'run_started':
            abiertas.add(m['id'])
        if t == 'run_finished':
            if p.get('run_id') not in abiertas:
                fallos.append(f'{donde}: cierra una ejecución que no está abierta')
            abiertas.discard(p.get('run_id'))
        if t == 'tool_start':
            herramientas[m['id']] = p
        if t == 'tool_end':
            inicio = herramientas.get(p.get('tool_call_id'))
            if inicio is None:
                fallos.append(f'{donde}: tool_end sin tool_start')
            elif emisor != inicio.get('side'):
                fallos.append(f'{donde}: lo cierra {emisor} y la herramienta es del lado {inicio.get("side")}')
            elif emisor == 'client' and ref != p.get('tool_call_id'):
                fallos.append(f'{donde}: el cliente debe responder con reply_to al tool_start')
        if t == 'approval_request':
            if p.get('digest') != digest(p.get('arguments', {})):
                fallos.append(f'{donde}: el digest no corresponde a los argumentos')
            if p.get('expires', '') <= m.get('time', ''):
                fallos.append(f'{donde}: la petición nace caducada')
        if t == 'approval_result' and p.get('scope') and ref in vistos:
            if p['scope'] not in vistos[ref].get('payload', {}).get('scopes', []):
                fallos.append(f'{donde}: alcance {p["scope"]} no ofrecido')
        if t == 'state_delta':
            for op in p.get('patch', []):
                if not op.get('path', '').startswith('/' + emisor):
                    fallos.append(f'{donde}: {emisor} modifica una raíz ajena ({op.get("path")})')
    if abiertas:
        fallos.append(f'ejecuciones sin run_finished: {sorted(abiertas)}')
    return fallos


def leer(ruta):
    return [json.loads(l) for l in Path(ruta).read_text().splitlines() if l.strip()]


def main(rutas):
    if rutas:
        malos = 0
        for r in rutas:
            f = verificar_sesion(leer(r))
            print(('FALLA ' if f else 'OK    ') + str(r), *('  - ' + x for x in f), sep='\n' if f else '')
            malos += bool(f)
        return 1 if malos else 0
    total = 0
    for r in sorted((RAIZ / 'conformance/valid').glob('*.jsonl')):
        f = verificar_sesion(leer(r))
        print(('OK    ' if not f else 'FALLA ') + r.name, *('  - ' + x for x in f), sep='\n' if f else '')
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
