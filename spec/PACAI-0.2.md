# PACAI 0.2 — Especificación (borrador)

- **Nombre:** PACAI — *Protocol for Agent Communication And Interfaces*.
- **Versión:** 0.2-borrador (2026-11-12). Sustituye al borrador 0.1, que se conserva en `spec/historico/`.
- **Estado:** borrador de trabajo. No es estable: puede cambiar sin aviso hasta la 1.0.
- **Idioma:** los nombres de mensajes y campos están en inglés. La prosa está en español.
- **Palabras clave:** «DEBE», «NO DEBE», «DEBERÍA» y «PUEDE» siguen RFC 2119/8174 cuando van en mayúsculas.

## 1. Qué es y qué no es

PACAI es el idioma común entre un **agente** y un **cliente**. El agente es el proceso que razona, usa herramientas y produce contenido. El cliente es lo que lo muestra al usuario: una app de Mac, un móvil, un widget, un terminal, una web o un altavoz.

El agente decide **qué** quiere decir o hacer. El cliente decide **cómo** mostrarlo según sus capacidades.

PACAI es un protocolo, no un programa. No define:

- **Cómo piensa el agente.** La personalidad, la memoria, el razonamiento o el estado de ánimo de Chiyo, de un NPC o de AlfalfaCode viven en el agente. PACAI solo transporta lo que el agente decide expresar.
- **Cómo usa el agente sus herramientas internas.** Eso es MCP.
- **Cómo hablan dos agentes entre sí.** Eso es A2A.
- **El vocabulario visual de componentes.** Eso es A2UI, que puede viajar dentro de un bloque `structured`.
- **La autenticación.** Va fuera de banda.

## 2. Sobre común

Cada mensaje es un objeto JSON en UTF-8:

| Campo | Tipo | Oblig. | Descripción |
|---|---|---|---|
| `pacai` | string | sí | Versión del protocolo: `"0.2"`. |
| `id` | string | sí | Id único del mensaje dentro de la sesión (≥ 8 caracteres). |
| `type` | string | sí | Tipo de mensaje (§4) o de extensión (§8). |
| `session` | string | sí | Id de la sesión (≥ 16 caracteres; ≥ 128 bits aleatorios en transportes de red). |
| `sender` | string | sí | `"agent"` o `"client"`. |
| `seq` | entero | sí | Contador por sesión y emisor. Empieza en 1 y sube de uno en uno. |
| `time` | string | sí | Instante ISO 8601 en UTC, p. ej. `2026-11-12T10:15:30Z`. |
| `reply_to` | string | no | `id` del mensaje al que responde (§2.1). |
| `payload` | objeto | sí | Contenido propio del tipo. |

Reglas:

- Los campos desconocidos se DEBEN ignorar.
- Un `id` repetido se DEBE descartar: la entrega es «al menos una vez».
- Un salto en `seq` indica mensajes perdidos. Se recupera con §6, y si no se puede, se responde con `error` `seq_unrecoverable`.

### 2.1 Peticiones y respuestas

PACAI se basa en eventos, pero algunos mensajes esperan respuesta: `hello`, `approval_request`, una herramienta del cliente y `resume`. La respuesta lleva `reply_to` con el `id` exacto de la petición. La correlación es **siempre** por `reply_to`, nunca por el orden de llegada.

## 3. Contenido: bloques

Los mensajes con contenido llevan `payload.blocks`, una lista de bloques:

| Bloque | Perfil | Campos |
|---|---|---|
| `text` | núcleo | `text` |
| `file` | núcleo | `name`, `media_type`, `data` (base64) o `url` |
| `structured` | núcleo | `schema` (URI), `data` (objeto) |
| `audio` | `voice` | `media_type`, `encoding` (`pcm16`, `opus`, `mp3`), `data` o `url`, `transcript` |

Un texto DEBE poder entenderse por sí solo. La expresión (§7.4) y el audio lo acompañan, pero no lo sustituyen.

## 4. Núcleo

### 4.1 Saludo y negociación

Ambos lados envían `hello` como primer mensaje. El agente contesta al del cliente con `session_started`, que lleva `reply_to`.

`hello.payload`:

| Campo | Descripción |
|---|---|
| `versions` | Versiones admitidas, de la preferida a la menos preferida. |
| `profiles` | Perfiles que admite (§7). |
| `extensions` | Espacios de extensión que admite (§8), p. ej. `["alfalfa"]`. |
| `client_tools` | Solo el cliente. Herramientas que el cliente puede ejecutar para el agente: `name`, `description` e `input_schema` (JSON Schema). Cierra el hueco 2 del 0.1. |
| `limits` | `max_message_bytes` (por defecto 1 MiB). |
| `resume_after_seq` | Para reconectar: la última `seq` del otro lado que recibió (§6). |
| `implementation` | `name` y `version` del programa. Es informativo. |

`session_started.payload`: `version` (la elegida), `profiles` (la intersección), `extensions` (la intersección), `agent` (`name` y `version`).

Reglas:

- La versión elegida es la primera de la lista del cliente que el agente también admite. Si no hay ninguna común, el agente responde `error` `version_incompatible` y cierra.
- Los perfiles y las extensiones activos son la intersección de los dos `hello`. Enviar un mensaje de un perfil o una extensión no activos es un `error` `not_negotiated`.

### 4.2 Entradas y ejecuciones

**`input`** (cliente), con `payload.blocks` y `payload.mode`:

- `"new_run"` (por defecto): abre una ejecución nueva. Si ya hay una en curso, el agente la encola y la ejecuta al terminar la actual. Así el usuario puede escribir sin esperar.
- `"steer"`: añade la entrada a la ejecución en curso, que lleva `payload.run_id`. El agente la incorpora antes de su siguiente paso de razonamiento, sin cortar la herramienta en marcha. Si esa ejecución ya terminó, el agente la trata como `new_run`.

**`run_started`** (agente): `payload.input_id`. El `id` de este mensaje es el **id de la ejecución** (`run_id`) en todo lo que sigue.

**`run_finished`** (agente): `payload.run_id` y `payload.outcome`, que es `"success"`, `"interrupted"`, `"failed"` o `"blocked"`. Con `failed` o `blocked` añade `payload.detail`. Toda ejecución DEBE cerrarse con `run_finished`. Tras él, la sesión sigue abierta y acepta otro `input`.

En 0.2 solo hay una ejecución activa por sesión.

### 4.3 Mensajes

Los mensajes se envían en tres partes:

- `message_start`: `run_id`, `role` (`assistant`, `user`, `system` o `tool`), `blocks` iniciales opcionales.
- `message_delta`: `message_id` (el `id` de su `message_start`) y `blocks`. Los bloques `text` se concatenan en el orden de `seq`.
- `message_end`: `message_id` y, opcionalmente, `blocks` con el contenido final completo.

Un cliente que no muestre texto en streaming PUEDE esperar a `message_end`.

### 4.4 Herramientas

**`tool_start`**: `run_id`, `name`, `arguments` (objeto), `side` (`"agent"` o `"client"`) y `title` (texto corto para mostrar).

**`tool_end`**: `tool_call_id` (el `id` de su `tool_start`), `status` (`"success"`, `"error"` o `"cancelled"`), `output` (bloques) y `summary`.

Si `side` es `"agent"`, el agente ejecuta la herramienta y emite `tool_end`.

Si `side` es `"client"`, el agente pide al cliente que ejecute una de sus `client_tools` (abrir un diálogo, leer el portapapeles, hacer una foto). El **cliente** emite `tool_end`, con `reply_to` igual al `tool_start`. Cierra el hueco 3 del 0.1.

Una herramienta cortada por una interrupción DEBE cerrarse con `tool_end` `cancelled`.

### 4.5 Aprobaciones

Antes de una acción que necesita permiso, el agente emite **`approval_request`**:

| Campo | Descripción |
|---|---|
| `run_id`, `tool_call_id` | Qué se va a aprobar. |
| `name`, `arguments` | La herramienta y sus argumentos completos. |
| `digest` | `"sha256:<hex>"` de los argumentos canonizados (JCS, RFC 8785). |
| `reason` | Por qué se pregunta: `dangerous`, `network`, `outside_sandbox`, `sandbox_denied_retry`, `external_tool`, `policy` u otro valor con prefijo de extensión. |
| `scopes` | Alcances que se ofrecen: `["once"]` o `["once", "session"]`. |
| `expires` | Instante límite. DEBE ser posterior al `time` de la propia petición. |

El cliente responde con **`approval_result`**, con `reply_to` y estos campos:

- `decision`: `"approved"`, `"denied"` o `"expired"`.
- `scope`: `"once"` o `"session"`, solo si se aprobó.
- `reason`: el motivo, opcional.

Reglas duras:

- **`once`** autoriza una sola ejecución con ese `digest`.
- **`session`** autoriza repetir, durante esa sesión, la misma herramienta con el **mismo digest**. Nunca autoriza otros argumentos.
- Antes de ejecutar, el agente DEBE comprobar que el digest de lo que va a ejecutar coincide con el aprobado. Si no coincide, DEBE pedir otra aprobación.
- **Sin respuesta no es un sí.** Pasado `expires`, el agente emite él mismo un `approval_result` `expired` y no ejecuta.
- Si un `approval_result` responde a un `reply_to` desconocido, el agente contesta `error` `unknown_approval` y no lo interpreta jamás como aprobación.
- Solo un `true` o un valor exacto de la lista es válido. Las cadenas como `"true"` se rechazan.

### 4.6 Interrupción

**`interrupt`** (cliente) lleva `payload.run_id`. El agente corta esa ejecución: cancela las herramientas en marcha, cierra cada una con `tool_end` `cancelled` y termina con `run_finished` `interrupted`. Si el `run_id` no está en curso, responde `error` `unknown_run`.

### 4.7 Uso y progreso

**`usage`** (agente), siempre opcional: `run_id`, `input_tokens`, `output_tokens`, `cached_tokens`, `context_tokens`, `context_limit` y `cost` (`amount` y `currency`). El cliente PUEDE mostrarlo y NO DEBE depender de él.

### 4.8 Latido, errores y cierre

- **`heartbeat`**: en transportes de red, al menos cada 30 s de silencio. Lleva `payload.last_seq`.
- **`error`**: `code` (snake_case estable), `message` y `ref` (el `id` relacionado, opcional). Códigos del núcleo:
  - `version_incompatible`, `not_negotiated`, `seq_unrecoverable`;
  - `unknown_run`, `unknown_approval`, `unknown_tool_call`;
  - `message_too_large`, `invalid_message`, `retention_expired`.
- **`close`**: `payload.reason`. Después de un `close` se descarta todo mensaje de esa sesión.

## 5. Transportes

### 5.1 stdio (`pacai+stdio`)

Es el transporte de los procesos locales, como `alfalfa --pacai`.

- Un mensaje por línea, JSON compacto terminado en `\n` (JSONL).
- **stdout lleva solo mensajes PACAI.** Los registros van por stderr.
- Cerrar la entrada (EOF) equivale a `close` del cliente. Una aprobación pendiente se resuelve entonces como `denied`, nunca como aprobada.
- No hace falta latido.

### 5.2 WebSocket (`pacai+ws`)

- Cada marco de texto lleva un mensaje. El subprotocolo es `pacai.v0`.
- En producción DEBE usarse `wss://`.

### 5.3 SSE/HTTP (`pacai+sse`)

- Un `POST` para los mensajes del cliente y un `GET text/event-stream` para los del agente.
- Cada evento SSE lleva `id:` igual al `id` del mensaje.
- Para reanudar se reabre el `GET` con `Last-Event-ID`.
- Las credenciales van en una cabecera `Authorization`, nunca en la URL.

## 6. Reanudación

Cortarse el transporte no termina la sesión. Al reconectar, el cliente envía `hello` con la misma `session` y `resume_after_seq`.

El agente responde de una de dos formas:

- reenvía en orden los mensajes posteriores que aún retiene;
- o, si ya no los tiene, envía `snapshot` con `payload` = `runs` (estado de cada ejecución), `pending_approvals`, `last_messages` y un `error` `retention_expired`.

Una ejecución terminada **nunca** se vuelve a lanzar por una reanudación.

Se RECOMIENDA retener los mensajes al menos 5 minutos en transportes de red. En stdio la sesión vive lo que vive el proceso. Para continuarla en otro proceso, el agente PUEDE ofrecer su propio mecanismo, como `alfalfa --reanudar`.

## 7. Perfiles opcionales

Un perfil se activa solo si ambos lados lo declaran en `hello`.

### 7.1 `voice`

- Añade el bloque `audio` y el mensaje **`voice_turn`**, con `payload.state` igual a `"client_speaking"`, `"agent_listening"` o `"barge_in"`.
- Con `barge_in`, el agente DEBE cortar el audio en curso.
- Los tramos de audio durarán como mucho 250 ms, y se RECOMIENDA incluir siempre la transcripción.

### 7.2 `shared_state`

Añade `state_snapshot` (objeto completo) y `state_delta` (JSON Patch, RFC 6902). El estado tiene dos raíces:

- `/agent`: solo la modifica el agente;
- `/client`: solo la modifica el cliente.

Así **el cliente también puede enviar estado**, como la pantalla abierta, la batería o «el usuario está ocupado», sin conflictos. Cierra el hueco 1 del 0.1.

Un parche que toque la raíz del otro lado es un `error` `invalid_message`. El estado NO DEBE contener secretos.

### 7.3 `work`

Es el perfil de los agentes que trabajan sobre archivos, como AlfalfaCode o Codex:

- **`plan_updated`**: `run_id` y `steps`, cada uno con `text` y `status` (`pending`, `in_progress` o `completed`).
- **`diff_updated`**: `run_id`, `files` (cada uno con `path`, `added` y `removed`) y `patch`, un diff unificado opcional.

### 7.4 `expression`

Lo propone la experiencia de Chiyo: el agente transmite **intenciones y estados del personaje**, y no recursos concretos. Cada cliente lo representa como pueda. Un widget muestra una imagen de Chiyo saludando; la app reproduce la animación con voz; un terminal no muestra nada.

**`expression`** (agente), con `run_id` opcional y `message_id` opcional (el mensaje al que acompaña):

| Campo | Descripción |
|---|---|
| `emotion` | Del vocabulario base: `neutral`, `happy`, `excited`, `curious`, `thinking`, `surprised`, `confused`, `sad`, `worried`, `bored`, `sleepy`, `proud`, `embarrassed`, `annoyed`. |
| `intensity` | De 0 a 1 (por defecto 0,5). |
| `gesture` | Opcional: `wave`, `nod`, `shake_head`, `shrug`, `point`, `celebrate`, `bow`, `facepalm`. |
| `voice_style` | Opcional: `cheerful`, `calm`, `whisper`, `serious`, `playful`. |
| `duration_ms` | Opcional: cuánto tiempo mantenerla. |
| `character` | Opcional: a qué personaje se refiere, cuando hay varios (p. ej. los NPC del director de juego). |

Reglas:

- **Es una sugerencia, nunca una orden.** El cliente PUEDE ignorar cualquier campo que no sepa representar, y DEBE ignorar los valores desconocidos.
- **No contiene significado imprescindible.** Lo que haya que entender va en el texto.
- **Extensible:** se añaden valores con prefijo, p. ej. `cuyworld.gesture.cast_spell`.
- **El cliente declara qué sabe hacer** en `hello.payload.render`, por ejemplo `{"expression": {"emotions": [...], "gestures": [...]}}`. Así el agente puede elegir lo que se verá, sin estar obligado a ello.

## 8. Extensiones con nombre

Lo propio de un producto va en su espacio de nombres: tipos `<espacio>.<nombre>`, como `alfalfa.budget`, `alfalfa.processes` o `cuyworld.scene`.

- Solo se envían si ambos lados declararon el espacio en `hello.payload.extensions`.
- NO DEBEN redefinir tipos ni campos del núcleo.
- Si una extensión resulta útil para muchos, pasa al núcleo o a un perfil en una versión futura.

## 9. Seguridad

| Riesgo | Medida |
|---|---|
| Aprobar otra cosa de lo que se ve | Digest de los argumentos canonizados y comprobación antes de ejecutar (§4.5). |
| Tomar el silencio por un sí | `expires`, EOF como negación, `reply_to` exacto y valores estrictos. |
| Repetir mensajes | Deduplicar por `id` y comprobar huecos en `seq`. |
| Fugas en el estado o en los registros | El estado no lleva secretos. No se registran los datos de `audio` ni de `file`. |
| Mensajes enormes | Límite negociado y `error` `message_too_large`. |
| Herramienta con descripción engañosa | La descripción no es autoridad: el cliente muestra el nombre, los argumentos y el digest. |
| Canal sin cifrar | `wss://` y HTTPS en red. stdio solo entre procesos locales. |

## 10. Conformidad

| Nivel | Requisito |
|---|---|
| **PACAI-Core** | Núcleo completo sobre un transporte. |
| **PACAI-Core+Resume** | Además, reanudación (§6) sobre un transporte de red. |

Cada perfil se declara aparte, por ejemplo «PACAI-Core + work + expression». Las pruebas de `conformance/` definen qué hay que pasar.

## 11. Cambios respecto a 0.1

- **Nombres en inglés.** `interfaz` pasa a `client`, y `ejecucion` a `run`.
- **`reply_to`**: correlación explícita entre petición y respuesta.
- **Transporte stdio**, que es el que usan los procesos locales.
- **Entrada:** `input.mode` distingue `steer` de `new_run`, y las entradas se encolan.
- **Interrupción:** `interrupt` apunta a una ejecución concreta.
- **Aprobaciones:** añaden `reason` y `scopes`, con «aprobar para la sesión» limitado al mismo digest.
- **Nuevos mensajes:** `usage`, perfil `work` y perfil `expression`.
- **Extensiones con nombre.**
- **Huecos del 0.1 cerrados:** el estado del cliente (§7.2), las herramientas del cliente en `hello` (§4.1) y el `tool_end` del cliente (§4.4).
- **Se quitan** los prefijos obligatorios de `id`, que no aportaban seguridad, y los tres niveles de conformidad atados a dos transportes.

## Anexo A. De `alfalfa --stdio` v2 a PACAI

| v2 | PACAI 0.2 |
|---|---|
| `sesion` | `session_started` |
| `evento` (texto del agente) | `message_start`/`message_delta`/`message_end` |
| `evento` (herramienta) | `tool_start`/`tool_end` |
| `permiso` / `permiso_resuelto` | `approval_request` / `approval_result` |
| `contexto` | `usage` |
| `turno_terminado` | `run_finished` |
| `plan` | `plan_updated` (perfil `work`) |
| `error` / `fin` | `error` / `close` |
| entrada `mensaje` | `input` `new_run` |
| entrada `redirigir`, `enviar_ahora` | `input` `steer` |
| entrada `cancelar`, `interrumpir` | `interrupt` / `close` |
| `presupuesto`, `procesos`, `navegador`, `despierto`, `cuota`, `compactar`, `subagentes`… | extensión `alfalfa.*` |

## Anexo B. Pendiente para salir del borrador

1. Nombre: comprobar marcas, repositorios y dominios.
2. Licencia: Apache-2.0 o MIT.
3. Ejecuciones en paralelo y subagentes (¿un `parent_run_id`?).
4. Puente con AG-UI, actualizado desde el 0.1.
5. Generar los tipos de Python y Swift desde el esquema.
