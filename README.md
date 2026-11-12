# PACAI

**Protocol for Agent Communication And Interfaces.** Un idioma común entre agentes (AlfalfaCode, Chiyo, el director de juego de CuyWorld…) y los clientes que los muestran: apps de Mac y móvil, widgets, terminales, webs y voz.

El agente decide qué quiere decir o hacer, y el cliente decide cómo mostrarlo según lo que sepa hacer.

> Estado: **borrador 0.2**, todavía inestable. El repo es privado hasta comprobar el nombre y elegir licencia.

## Contenido

| Ruta | Qué es |
|---|---|
| [`spec/PACAI-0.2.md`](spec/PACAI-0.2.md) | La especificación, con identificadores en inglés y prosa en español |
| [`spec/historico/PACAI-0.1.md`](spec/historico/PACAI-0.1.md) | El borrador anterior |
| `schema/pacai-0.2.schema.json` | El esquema JSON, generado por `schema/generar.py` |
| `conformance/` | Ejemplos válidos, ejemplos inválidos y el verificador |

## Comprobar

```sh
pip install jsonschema
python3 schema/generar.py                  # regenera el esquema
python3 conformance/generar_ejemplos.py    # regenera los ejemplos válidos e inválidos por mensaje
python3 conformance/verificar.py           # todo debe salir OK
python3 conformance/verificar.py mi-sesion.jsonl
```

## En una página

- **Un sobre por mensaje:** `pacai`, `id`, `type`, `session`, `sender`, `seq`, `time`, `reply_to` y `payload`.
- **Al empezar:** ambos lados envían `hello`, que negocia versión, perfiles, extensiones y las herramientas del cliente.
- **Trabajo:** `input` (`new_run` o `steer`) → `run_started` → `message_*` y `tool_*` → `run_finished`.
- **Aprobaciones:** con digest de los argumentos, caducidad y alcance `once` o `session`. El silencio nunca cuenta como un sí.
- **Perfiles opcionales:** `voice`, `shared_state`, `work` (plan y diff) y `expression` (emoción, gesto y voz del personaje).
- **Extensiones:** con espacio de nombres, como `alfalfa.budget`.
- **Transportes:** stdio (JSONL), WebSocket y SSE.

## Hoja de ruta

1. Cerrar el borrador 0.2: subagentes y ejecuciones en paralelo, y el puente con AG-UI.
2. SDK de Python y paquete Swift, con tipos generados desde el esquema.
3. `alfalfa --pacai`, que sustituye a `--stdio` v2 (ver el anexo A de la especificación).
4. La app de Mac de AlfalfaCode sobre PACAI.
5. El director de juego de CuyWorld sobre PACAI.
