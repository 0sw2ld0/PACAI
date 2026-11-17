"""Una sesión PACAI con un agente de verdad: lanza `alfalfa --pacai`, le manda un encargo y enseña cada
mensaje que va y viene hasta el `run_finished`.

Comprueba la sesión con `pacai.Session` sobre la marcha y no aprueba nada: si el agente pide permiso, lo
niega. Hace falta AlfalfaCode instalado, con un proveedor configurado.

Uso:
    python3 sesion_con_alfalfa.py [--todo] [--guardar SESION.jsonl] ["ENCARGO"] [-- ORDEN DEL AGENTE…]

Por defecto el encargo es «¿Qué hay en esta carpeta? Contesta en una frase.» y la orden,
`alfalfa --pacai --modo plan`, que solo lee. Los `usage` y los mensajes de extensiones (`alfalfa.*`) se
cuentan pero no se enseñan; `--todo` los enseña también. `--guardar` escribe la sesión entera, los dos
lados, para pasarla por `conformance/verificar.py`.
"""
import subprocess
import sys

from pacai import MessageBuilder, Session, StdioTransport, encode

ENCARGO = '¿Qué hay en esta carpeta? Contesta en una frase.'
ORDEN = ['alfalfa', '--pacai', '--modo', 'plan']


def resumen(m):
    """Lo que interesa de cada mensaje, en una línea."""
    p, t = m['payload'], m['type']
    if t == 'hello':
        quien = p.get('implementation', {})
        return ' · '.join(filter(None, [' '.join(filter(None, [quien.get('name'), quien.get('version')])),
                                        'versiones ' + ','.join(p['versions']),
                                        'perfiles ' + (','.join(p.get('profiles', [])) or '-'),
                                        'extensiones ' + (','.join(p.get('extensions', [])) or '-')]))
    if t == 'session_started':
        return f"{p['version']} · perfiles {','.join(p['profiles']) or '-'} · extensiones {','.join(p['extensions']) or '-'}"
    if t == 'input':
        return '«' + ''.join(b.get('text', '') for b in p['blocks']) + '»'
    if t in ('message_start', 'message_delta', 'message_end'):
        texto = ''.join(b.get('text', '') for b in p.get('blocks', []))
        return ' '.join(filter(None, [p.get('role'), ('«' + texto + '»') if texto else '']))
    if t == 'tool_start':
        return p.get('title') or p['name']
    if t == 'tool_end':
        return p['status'] + (' · ' + p['summary'] if p.get('summary') else '')
    if t == 'approval_request':
        return f"{p['name']} · {p['reason']} · se niega"
    if t == 'approval_result':
        return p['decision']
    if t == 'run_started':
        return 'ejecución raíz' if 'input_id' in p else 'subejecución ' + p.get('agent', {}).get('name', '')
    if t == 'close':
        return p.get('reason', '')
    if t == 'run_finished':
        return p['outcome'] + (' · ' + str(p['detail']) if p.get('detail') else '')
    return ', '.join(sorted(p))


def main(argv):
    if '--' in argv:
        corte = argv.index('--')
        argv, orden = argv[:corte], argv[corte + 1:]
    else:
        orden = ORDEN
    todo = '--todo' in argv
    argv = [a for a in argv if a != '--todo']
    guardar = None
    if '--guardar' in argv:
        i = argv.index('--guardar')
        guardar, argv = argv[i + 1], argv[:i] + argv[i + 2:]
    encargo = argv[0] if argv else ENCARGO
    escondidos = 0
    agente = subprocess.Popen(orden, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8')
    canal = StdioTransport(reader=agente.stdout, writer=agente.stdin)
    cliente = MessageBuilder('client')
    sesion = Session()
    todos = []

    def enviar(m):
        sesion.feed(m)
        todos.append(m)
        print(f"→ cliente {m['seq']:>2}  {m['type']:<16} {resumen(m)}")
        canal.send(m)

    enviar(cliente.hello(profiles=['work'], extensions=['alfalfa']))
    enviar(cliente.input(encargo))      # sin esperar a session_started: se puede encadenar (§4.1)
    raiz = None
    for m in canal:
        sesion.feed(m)
        todos.append(m)
        if todo or not (m['type'] == 'usage' or '.' in m['type']):
            print(f"← agente  {m['seq']:>2}  {m['type']:<16} {resumen(m)}")
        else:
            escondidos += 1
        if m['type'] == 'run_started' and 'input_id' in m['payload']:
            raiz = m['id']
        elif m['type'] == 'approval_request':
            enviar(cliente.approval_result(m['id'], 'denied', reason='este ejemplo no aprueba nada'))
        elif m['type'] == 'run_finished' and m['payload']['run_id'] == raiz:
            break
    enviar(cliente.close('fin'))
    agente.stdin.close()
    agente.wait(timeout=30)
    if guardar:
        with open(guardar, 'w', encoding='utf-8') as f:
            f.writelines(encode(m) for m in todos)
    if escondidos:
        print(f'(sin enseñar: {escondidos} mensajes usage o de extensiones; --todo los enseña)')
    sesion.finish()                     # p. ej. ejecuciones sin run_finished
    problemas = sesion.problems
    print('Sesión correcta según pacai.Session.' if not problemas else 'Problemas:\n- ' + '\n- '.join(problemas))
    return 0 if not problemas else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
