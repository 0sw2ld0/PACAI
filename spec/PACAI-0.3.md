# PACAI 0.3 — Especificación

- **Nombre:** PACAI — *Protocol for Agent Communication And Interfaces*.
- **Versión:** 0.3 (2026-11-15). Sustituye a la 0.2, que se conserva en `spec/historico/` junto con el borrador 0.1. Lo que cambia está en el §11.
- **Estado:** contenido cerrado. Licencia Apache-2.0. Solo queda pendiente el nombre (anexo B). Hasta la 1.0 una versión nueva puede romper la compatibilidad, pero la 0.3 no cambia.
- **Idioma:** los nombres de mensajes y campos están en inglés. La prosa está en español.
- **Palabras clave:** «DEBE», «NO DEBE», «DEBERÍA» y «PUEDE» siguen RFC 2119/8174 cuando van en mayúsculas.
- **Material normativo:** este documento. El esquema (`schema/pacai-0.3.schema.json`) y el verificador (`conformance/verificar.py`) lo traducen a máquina; si discrepan, manda este texto y el otro se corrige.

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
| `pacai` | string | sí | Versión del protocolo: `"0.3"`. |
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
- La entrega es «al menos una vez». Un mensaje cuyo `id` ya se recibió con el mismo contenido es una retransmisión y se DEBE descartar sin más. Un `id` repetido con otro contenido es un `error` `invalid_message`.
- Cada lado lleva su propia `seq`. Las retransmisiones conservan el `id` y la `seq` originales.
- Un salto en `seq` indica mensajes perdidos. Se recupera con §6, y si no se puede, se responde con `error` `seq_unrecoverable`.
- El tipo de mensaje fija quién puede enviarlo (catálogo del §4). Un mensaje del lado equivocado es un `error` `invalid_message`.

### 2.1 Peticiones y respuestas

PACAI se basa en eventos, pero algunos mensajes esperan respuesta. La respuesta lleva `reply_to` con el `id` exacto de la petición. La correlación es **siempre** por `reply_to`, nunca por el orden de llegada.

| Petición | Respuesta | `reply_to` |
|---|---|---|
| `hello` del cliente | `session_started` (y, al reanudar sin reenvío, `snapshot`) | obligatorio |
| `approval_request` | `approval_result` | obligatorio |
| `tool_start` con `side` `"client"` | `tool_end` del cliente | obligatorio |

Una respuesta DEBE contestar a un mensaje del otro lado. Las únicas excepciones son los `approval_result` `expired` y `cancelled`, que el agente emite sobre su propia petición (§4.5). Los demás mensajes PUEDEN llevar `reply_to` como referencia informativa; el `tool_end` `cancelled` con el que el agente cierra una herramienta del cliente (§4.4) no es una respuesta y no lo lleva.

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

Catálogo de tipos. «Ambos» significa que cualquiera de los dos lados lo envía.

| Tipo | Emisor | Perfil | § |
|---|---|---|---|
| `hello` | ambos | núcleo | 4.1 |
| `session_started` | agente | núcleo | 4.1 |
| `input` | cliente | núcleo | 4.2 |
| `run_started`, `run_finished` | agente | núcleo | 4.2, 4.9 |
| `message_start`, `message_delta`, `message_end` | agente | núcleo | 4.3 |
| `tool_start` | agente | núcleo | 4.4 |
| `tool_end` | el lado que ejecuta (`side`); el agente también, para cancelar una del cliente | núcleo | 4.4 |
| `approval_request` | agente | núcleo | 4.5 |
| `approval_result` | cliente (`approved`, `denied`) o agente (`expired`, `cancelled`) | núcleo | 4.5 |
| `interrupt` | cliente | núcleo | 4.6 |
| `usage` | agente | núcleo | 4.7 |
| `heartbeat`, `error`, `close` | ambos | núcleo | 4.8 |
| `snapshot` | agente | núcleo | 6 |
| `voice_turn` | ambos | `voice` | 7.1 |
| `state_snapshot`, `state_delta` | ambos, cada uno en su raíz | `shared_state` | 7.2 |
| `plan_updated`, `diff_updated` | agente | `work` | 7.3 |
| `expression` | agente | `expression` | 7.4 |
| `<espacio>.<nombre>` | según la extensión | extensión | 8 |

### 4.1 Saludo y negociación

Ambos lados envían `hello` como primer mensaje. El agente contesta al del cliente con `session_started`, que lleva `reply_to`.

`hello.payload`:

| Campo | Descripción |
|---|---|
| `versions` | Versiones admitidas, de la preferida a la menos preferida. |
| `profiles` | Perfiles que admite (§7). |
| `extensions` | Espacios de extensión que admite (§8), p. ej. `["alfalfa"]`. |
| `client_tools` | Solo el cliente. Herramientas que el cliente puede ejecutar para el agente: `name`, `description` e `input_schema` (JSON Schema). Cierra el hueco 2 del 0.1. |
| `limits` | `max_message_bytes` (por defecto 1 MiB). En stdio cuenta también el salto de línea (§5.1). |
| `resume_after_seq` | Solo el cliente, para reconectar: la última `seq` del agente que recibió (§6). |
| `render` | Solo el cliente. Qué sabe representar, p. ej. para `expression` (§7.4). Es informativo. |
| `implementation` | `name` y `version` del programa. Es informativo. |

Solo `versions` es obligatorio. `profiles` y `extensions` ausentes equivalen a listas vacías.

`session_started.payload`: `version` (la elegida), `profiles` (la intersección), `extensions` (la intersección), todos obligatorios, y `agent` (`name` y `version`, opcional). Al reanudar (§6) añade `resumed: true` y `resume_after_seq`: la última `seq` del cliente que el agente recibió.

Reglas:

- La versión elegida es la primera de la lista del cliente que el agente también admite. Si no hay ninguna común, el agente responde `error` `version_incompatible` y cierra.
- Los perfiles y las extensiones activos son la intersección de los dos `hello`. Enviar un mensaje de un perfil o una extensión no activos es un `error` `not_negotiated`.
- Antes de su propio `hello`, un lado solo puede enviar `error`, `close` y `heartbeat`. Cualquier otro mensaje es un `error` `invalid_message`.
- El agente no envía nada más que `hello`, `error`, `close` y `heartbeat` antes de su `session_started`.
- **Encadenar («pipelining»):** el cliente PUEDE enviar mensajes justo después de su `hello`, sin esperar a `session_started`. El agente los procesa en orden de `seq` una vez negociada la sesión, como si hubieran llegado después, y con las reglas de la sesión negociada: un mensaje de un perfil o una extensión que no quedaron activos recibe `not_negotiated`. Si la negociación falla, el agente responde `error` `version_incompatible`, cierra y descarta esos mensajes sin contestarlos uno a uno. En stdio el agente no puede saber si el cliente esperó, y así no le hace falta.
- Una sesión solo se negocia una vez. Un segundo `hello` del cliente solo es válido para reanudar (§6), y el agente no vuelve a enviar `hello`.

### 4.2 Entradas y ejecuciones

**`input`** (cliente), con `payload.blocks` y `payload.mode`:

- `"new_run"` (por defecto): abre una ejecución nueva. Si ya hay una en curso, el agente la encola y la ejecuta al terminar la actual. Así el usuario puede escribir sin esperar.
- `"steer"`: añade la entrada a la ejecución en curso que nombra `payload.run_id` (obligatorio). El agente la incorpora antes de su siguiente paso de razonamiento, sin cortar la herramienta en marcha. Si `run_id` es una subejecución (§4.9), la entrada va a ese subagente. Si esa ejecución ya terminó, el agente la trata como `new_run`.

**`run_started`** (agente). El `id` de este mensaje es el **id de la ejecución** (`run_id`) en todo lo que sigue. Lleva exactamente uno de estos dos campos:

- `input_id`: el `input` que la abre. Es una **ejecución raíz**.
- `parent_run_id`: la ejecución que la lanza. Es una **subejecución** (§4.9). Lleva además `tool_call_id` si la lanzó una herramienta, y PUEDE llevar `agent`.

**`run_finished`** (agente): `payload.run_id` y `payload.outcome`, que es `"success"`, `"interrupted"`, `"failed"` o `"blocked"`. Con `failed` o `blocked` añade `payload.detail`. Toda ejecución DEBE cerrarse con `run_finished`. Tras él, la sesión sigue abierta y acepta otro `input`.

Reglas:

- Hay como mucho **una ejecución raíz activa** por sesión. Las entradas `new_run` se encolan (no se rechazan), y su `run_started` llega cuando termina la anterior.
- Las subejecuciones pueden ser varias y correr en paralelo (§4.9).
- Los mensajes del agente que llevan `run_id` (`message_start`, `tool_start`, `approval_request`, `usage`, `plan_updated`, `diff_updated` y `expression`) DEBEN nombrar una ejecución activa.
- Una ejecución no termina con herramientas abiertas ni con aprobaciones pendientes: antes de su `run_finished`, cada `tool_start` suyo tiene su `tool_end`, y cada `approval_request` suyo, su `approval_result`.
- **Ejecución que se cierra.** Cuando el agente cancela algo de una ejecución porque esta termina o se interrumpe (un `approval_result` `cancelled`, §4.5, o el `tool_end` `cancelled` de una herramienta del cliente, §4.4), esa ejecución entra en cierre. Desde ese momento el agente NO DEBE empezar trabajo nuevo en ella (`message_start`, `message_delta`, `tool_start`, `approval_request`, `expression` ni subejecuciones nuevas). Solo PUEDE cerrar lo que siga abierto (`tool_end`, `approval_result` `cancelled`, `message_end`, el cierre de sus subejecuciones), informar (`usage`, `plan_updated`, `diff_updated`) y terminar con `run_finished`.

### 4.3 Mensajes

Los mensajes se envían en tres partes:

- `message_start`: `run_id`, `role` (`assistant`, `user`, `system` o `tool`), `blocks` iniciales opcionales.
- `message_delta`: `message_id` (el `id` de su `message_start`) y `blocks`. Los bloques `text` se concatenan en el orden de `seq`.
- `message_end`: `message_id` y, opcionalmente, `blocks` con el contenido final completo.

Un cliente que no muestre texto en streaming PUEDE esperar a `message_end`.

### 4.4 Herramientas

**`tool_start`**: `run_id`, `name`, `arguments` (objeto), `side` (`"agent"` o `"client"`), `title` (opcional) y `truncated` (opcional).
Si la llamada está cubierta por una aprobación de alcance `session`, lleva también `approval_id` (§4.5).

Argumentos:

- **`arguments` son los argumentos reales de la llamada**, completos y en crudo: lo que recibe la herramienta, no un resumen. Con ellos el cliente puede mostrar la llamada tal cual y calcular el digest de una aprobación (§4.5).
- **`title` es la parte legible:** un texto corto para mostrar, p. ej. `rm -rf build`. Es opcional y no tiene autoridad; lo que se aprueba son `name` y `arguments`.
- **Secretos.** Con `side` `"agent"`, el agente PUEDE tachar el valor de un secreto (una clave, un token, una contraseña) sustituyéndolo por la cadena `"[redacted]"`. No cambia las claves ni la estructura. El digest de una aprobación se calcula sobre los argumentos tal como viajan, tachados, y el agente DEBE tachar siempre igual para poder comprobarlo antes de ejecutar.
- **Argumentos demasiado grandes.** Si el `tool_start` no cabe en `max_message_bytes`, el agente PUEDE acortar valores de cadena (nunca claves, números ni la estructura) y marcarlo con `truncated: true`. Una llamada con `truncated` NO DEBE pedir aprobación ni reutilizar una aprobación `session` (`approval_id`), porque nadie puede aprobar lo que no ve entero: si la necesita, el agente la cierra con `tool_end` `error`.
- Con `side` `"client"`, `arguments` son exactamente lo que el cliente ejecuta: ni tachados ni acortados.

**`tool_end`**: `tool_call_id` (el `id` de su `tool_start`), `status` (`"success"`, `"error"` o `"cancelled"`), `output` (bloques) y `summary`.
Solo `tool_call_id` y `status` son obligatorios.

Si `side` es `"agent"`, el agente ejecuta la herramienta y emite `tool_end`.

Si `side` es `"client"`, el agente pide al cliente que ejecute una de sus `client_tools` (abrir un diálogo, leer el portapapeles, hacer una foto). El **cliente** emite `tool_end`, con `reply_to` igual al `tool_start`. Cierra el hueco 3 del 0.1. El agente NO DEBE pedir una herramienta que el cliente no declaró; si lo hace, el cliente responde `tool_end` `error`.

**Cancelar una herramienta del cliente.** Si la ejecución termina o se interrumpe con una herramienta del cliente abierta, el agente PUEDE cerrarla él mismo con un `tool_end` con `status` `cancelled`, sin `reply_to`. Es el único `tool_end` que el agente envía por una herramienta del cliente, y solo con ese estado. Desde ese momento:

- La ejecución entra en cierre (§4.2): el agente ya no empieza trabajo nuevo en ella.
- El cliente DEBERÍA dejar de ejecutar la herramienta. PUEDE no enviar su `tool_end`.
- Un `tool_end` del cliente que llegue después, o que se cruce con el del agente, se ignora sin error de protocolo (ni `unknown_tool_call` ni `invalid_message`). La herramienta cuenta como cancelada.

Si el agente no la cancela, sigue esperando el `tool_end` del cliente, como en la 0.2.

Cada `tool_start` tiene exactamente un `tool_end` que cuenta. Una herramienta cortada por una interrupción DEBE cerrarse con `tool_end` `cancelled`. Un `tool_end` cuyo `tool_call_id` no se conoce recibe `error` `unknown_tool_call`.

### 4.5 Aprobaciones

Antes de una acción que necesita permiso, el agente emite su `tool_start` y después **`approval_request`**. Todos los campos son obligatorios salvo `expires`:

| Campo | Descripción |
|---|---|
| `run_id`, `tool_call_id` | Qué se va a aprobar: la ejecución (raíz o subejecución) y su `tool_start`, que sigue abierto. |
| `name`, `arguments` | La herramienta y sus argumentos, iguales a los del `tool_start` (§4.4). |
| `digest` | `"sha256:<hex>"` de los argumentos canonizados (JCS, RFC 8785). |
| `reason` | Por qué se pregunta: `dangerous`, `network`, `outside_sandbox`, `sandbox_denied_retry`, `external_tool`, `policy` u otro valor con prefijo de extensión. |
| `scopes` | Alcances que se ofrecen, sin repetir: `["once"]`, `["session"]` o `["once", "session"]`. |
| `expires` | Opcional. Instante límite; si está, DEBE ser posterior al `time` de la propia petición. Sin `expires`, la petición no caduca: espera hasta que el cliente responda o el agente la cancele. |

La respuesta es **`approval_result`**, siempre con `reply_to` igual al `id` de la petición:

- `decision`: el **cliente** envía `"approved"` o `"denied"`; solo el **agente** envía `"expired"` o `"cancelled"`.
- `scope`: `"once"` o `"session"`. Es obligatorio si se aprobó y está prohibido en otro caso. DEBE ser uno de los `scopes` ofrecidos.
- `reason`: el motivo, opcional.

Reglas duras:

- **`once`** autoriza una sola ejecución: la del `tool_start` de la petición.
- **`session`** autoriza además repetir, durante esa sesión, la misma herramienta (`name`) con el **mismo digest**. Nunca autoriza otros argumentos ni otra herramienta. Cubre todas las ejecuciones de la sesión, subagentes incluidos, y sobrevive a una reanudación porque la sesión es la misma. Muere con la sesión.
- **Reutilizar `session`:** cada repetición es un `tool_start` nuevo con `approval_id` igual al `id` del `approval_request` aprobado, y sin otra petición. Así el cliente ve qué permiso se está usando. Un `approval_id` que no sea una aprobación `session` vigente, o cuyo `name` o digest no coincidan, invalida la llamada.
- Antes de ejecutar, el agente DEBE comprobar que el digest de lo que va a ejecutar coincide con el aprobado. Si no coincide, DEBE pedir otra aprobación.
- Una herramienta denegada o caducada NO DEBE ejecutarse: su `tool_end` es `error` o `cancelled`, nunca `success`. Una cancelada se cierra con `tool_end` `cancelled`.
- **Sin respuesta no es un sí.** Pasado `expires`, el agente emite él mismo un `approval_result` `expired` y no ejecuta. Sin `expires`, el agente espera; nunca ejecuta sin respuesta.
- El agente NO DEBE declarar `expired` antes de `expires`, ni en una petición sin `expires`. Una respuesta del cliente que llega después de `expires`, o después del `expired` o el `cancelled` del agente, se ignora: no cuenta como aprobación.
- **Al terminar o interrumpir.** Si una ejecución termina o se interrumpe con peticiones pendientes, el agente DEBE resolver cada una de forma explícita con un `approval_result` `cancelled` (con `reply_to` a la petición) antes del `tool_end` `cancelled` de su herramienta. Así el cliente retira la tarjeta sin adivinar. Desde ese `cancelled`, la ejecución entra en cierre (§4.2). Si el `cancelled` se cruza con la respuesta del cliente, vale el `cancelled`.
- Una petición se resuelve una sola vez. Si `scope` no está entre los ofrecidos, la respuesta no vale como aprobación y el agente contesta `error` `invalid_message`.
- Si un `approval_result` responde a un `reply_to` desconocido, el agente contesta `error` `unknown_approval` y no lo interpreta jamás como aprobación.
- Solo valen los valores exactos de la lista. `"true"`, `"yes"` o `true` no son una decisión: el mensaje se rechaza con `invalid_message`.
- El cierre de la sesión (`close` o EOF) resuelve las peticiones pendientes como negadas, sin más mensajes.

### 4.6 Interrupción

**`interrupt`** (cliente) lleva `payload.run_id`. El agente corta esa ejecución y **todas sus subejecuciones**, de las hojas a la raíz. En cada una: resuelve las aprobaciones pendientes con `approval_result` `cancelled` (§4.5), cancela las herramientas en marcha y cierra cada una con `tool_end` `cancelled` (las del cliente, si no las ha cerrado el cliente, §4.4), y termina la ejecución con `run_finished` `interrupted`.

Interrumpir una subejecución no interrumpe a su madre. Si la herramienta que la lanzó sigue abierta, la madre recibe su `tool_end` `cancelled` y sigue; si ya terminó (subagente en segundo plano, §4.9), no hay nada más que cerrar. Si el `run_id` no está en curso, responde `error` `unknown_run`.

### 4.7 Uso y progreso

**`usage`** (agente), siempre opcional y con todos sus campos opcionales: `run_id`, `input_tokens`, `output_tokens`, `cached_tokens`, `context_tokens`, `context_limit` y `cost` (`amount` y `currency` ISO 4217). Sin `run_id` se refiere a la sesión. El cliente PUEDE mostrarlo y NO DEBE depender de él.

### 4.8 Latido, errores y cierre

- **`heartbeat`** (ambos): en transportes de red, al menos cada 30 s de silencio. Lleva `payload.last_seq`, obligatorio: la última `seq` del otro lado que recibió.
- **`error`** (ambos): `code` y `message` obligatorios, y `ref` (el `id` relacionado), opcional. Un `error` no cierra la sesión salvo que se diga lo contrario.
- **`close`** (ambos): `payload.reason`, opcional. Después de un `close` se descarta todo mensaje de esa sesión.

Códigos del núcleo:

| `code` | Cuándo | ¿Cierra? |
|---|---|---|
| `version_incompatible` | No hay versión común (§4.1). | sí |
| `not_negotiated` | Mensaje de un perfil o una extensión no activos. | no |
| `seq_unrecoverable` | Faltan mensajes y no se pueden recuperar (§6). | sí |
| `retention_expired` | Se pide reanudar una sesión que el agente ya no retiene, ni siquiera para un `snapshot` (§6). | sí |
| `unknown_run` | `interrupt` con un `run_id` que no está en curso, o `steer` con uno que no existe. | no |
| `unknown_approval` | `approval_result` con un `reply_to` que no es una petición pendiente. | no |
| `unknown_tool_call` | `tool_end` de una herramienta desconocida. No se usa para el `tool_end` tardío de una herramienta del cliente que el agente canceló (§4.4), que se ignora. | no |
| `message_too_large` | Mensaje mayor que `max_message_bytes`. | no |
| `invalid_message` | No cumple el esquema o rompe una regla de sesión. | no |

Los códigos son `snake_case`. Las extensiones añaden los suyos con su prefijo, p. ej. `alfalfa.budget_exceeded`.

### 4.9 Subagentes y ejecuciones en paralelo

Un agente PUEDE delegar trabajo en **subagentes**, uno detrás de otro o varios a la vez: AlfalfaCode lanza revisores en paralelo y el director de juego de CuyWorld hace hablar a varios NPC. En PACAI cada invocación de un subagente es una **subejecución**: un `run_started` con `parent_run_id`.

`run_started.payload` de una subejecución:

| Campo | Oblig. | Descripción |
|---|---|---|
| `parent_run_id` | sí | La ejecución que la lanza: la raíz u otra subejecución (se pueden anidar). |
| `tool_call_id` | si la lanzó una herramienta | El `tool_start` de la madre que la lanzó, cuando el subagente se lanza con una herramienta (`spawn_agent`). Permite pintar el subagente dentro de la tarjeta de esa herramienta. Si la lanzó el agente sin herramienta, no va. |
| `agent` | no | `name` (obligatorio dentro de `agent`) y `description`: qué tipo de subagente es, para mostrarlo. |

Reglas:

- `parent_run_id` DEBE nombrar una ejecución activa que no esté en cierre (§4.2). Si hay `tool_call_id`, DEBE ser una herramienta abierta de esa madre en el momento del `run_started`.
- Todo lo que hace el subagente lleva su propio `run_id`: mensajes, herramientas, aprobaciones, uso, plan y expresión. El `run_id` identifica **una invocación**; `agent.name` identifica el tipo. Dos invocaciones del mismo subagente tienen `run_id` distintos.
- Varias subejecuciones pueden estar activas a la vez y sus mensajes se intercalan. Cada mensaje se atribuye sin ambigüedad: por su `run_id`, o por el `message_id` o el `tool_call_id` que remiten a uno.
- **Subagentes en segundo plano.** La herramienta `tool_call_id` PUEDE terminar antes que la subejecución que lanzó: un `spawn_agent` que vuelve en el acto con el id del subagente cierra su `tool_end` `success` y el subagente sigue trabajando. Si espera al informe, termina después. Las dos formas son válidas.
- **Orden de cierre:** una ejecución no termina antes que sus subejecuciones. Una subejecución, por tanto, nunca sobrevive a su madre ni a su ejecución raíz, aunque su herramienta ya haya terminado. Si la madre acaba su trabajo con subagentes vivos, DEBE esperarlos o interrumpirlos (§4.6) antes de su `run_finished`. Mientras tanto la raíz sigue activa: los `input` `new_run` se encolan y el `steer` y el `interrupt` funcionan como siempre.
- Las aprobaciones de un subagente son normales (§4.5): su `run_id` dice al cliente quién pregunta. Una aprobación `session` vale para toda la sesión, también para los demás subagentes.
- `steer` e `interrupt` pueden apuntar a una subejecución (§4.2, §4.6).
- El agente decide cuántos subagentes lanza; PACAI no fija un límite.
- Un cliente sin interfaz para subagentes DEBE aceptarlos igualmente. PUEDE mostrarlos aplanados como parte de la ejecución raíz u ocultar su contenido, pero DEBE mostrar sus `approval_request`.

**Por qué así.** Se descartaron otras tres opciones:

1. **Mensajes propios (`subagent_started`, `subagent_finished`), como AG-UI.** Habría que repetir para el subagente todo lo que ya cumple una ejecución: cierre obligatorio, interrupción, uso, aprobaciones y reanudación. Con `parent_run_id` todas esas reglas valen sin escribirlas otra vez, y un cliente que ya entiende ejecuciones entiende subagentes.
2. **Un campo de atribución en cada mensaje (el `subagentRunId` de AG-UI).** En PACAI ya hay uno: todo mensaje de trabajo lleva `run_id` o remite a él. Basta con que ese `run_id` sea el de la subejecución.
3. **Varias ejecuciones raíz en paralelo, o una sesión por subagente.** Romperían la cola de entradas y el `steer` (¿a cuál va lo que escribe el usuario?), y la sesión aparte perdería la interrupción en cascada y las aprobaciones `session` compartidas. Para conversaciones independientes de verdad, se abren sesiones distintas.
4. **Subagentes que sobreviven a su ejecución raíz** (lo que hace Claude Code con `task_notification`, o la RFC «Background Work» de ACP). Harían falta un dueño para el subagente huérfano, una forma de interrumpirlo sin raíz y reglas para el `snapshot`. Exigir que la madre espere o interrumpa a sus subagentes es lo más sencillo, se comprueba con el árbol de `parent_run_id` y es lo que ya hace AlfalfaCode: el turno no se cierra hasta que acaban sus subagentes.

El nombre `parent_run_id` sigue el vocabulario de `run_id`. AG-UI tiene un campo homónimo (`parentRunId`) con otro significado, el linaje de ejecuciones sucesivas de un hilo; el anexo C lo explica.

## 5. Transportes

### 5.1 stdio (`pacai+stdio`)

Es el transporte de los procesos locales, como `alfalfa --pacai`.

- Un mensaje por línea, JSON compacto terminado en `\n` (JSONL).
- Para `max_message_bytes`, se DEBEN contar los bytes UTF-8 de toda la línea, incluido el byte final `\n` (LF). Una línea de exactamente ese tamaño cabe. Si lo supera, corresponde `message_too_large` (§4.8).
- **stdout lleva solo mensajes PACAI.** Los registros van por stderr.
- Cerrar la entrada (EOF) equivale a `close` del cliente. Las aprobaciones pendientes se resuelven entonces como negadas, nunca como aprobadas.
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

Cortarse el transporte no termina la sesión. Al reconectar, el cliente envía `hello` con la misma `session`, su `seq` siguiente y `resume_after_seq`: la última `seq` del agente que recibió. El agente no vuelve a enviar `hello`.

El agente responde de una de tres formas:

1. **Reenvío.** Si retiene todos los mensajes posteriores a `resume_after_seq`, los reenvía en orden, con su `id` y su `seq` originales, y después envía `session_started` con `resumed: true`, que sigue la numeración. El cliente descarta por `id` los que ya tuviera.
2. **Snapshot.** Si ya no los retiene, envía `session_started` con `resumed: true` y una `seq` que salta los mensajes perdidos, e inmediatamente después **`snapshot`**, también con `reply_to` al `hello`. El salto de `seq` solo es válido en ese `session_started`, y solo si lo sigue el `snapshot`.
3. **Imposible.** Si ya no conserva la sesión, responde `error` `retention_expired` y cierra. El cliente empieza una sesión nueva.

El `session_started` de reanudación repite la `version`, los `profiles` y las `extensions` ya negociados, que no cambian, y lleva `resume_after_seq` con la última `seq` del cliente que recibió el agente. El cliente reenvía los suyos posteriores, también con su `id` y su `seq` originales.

`snapshot.payload`:

| Campo | Oblig. | Descripción |
|---|---|---|
| `runs` | sí | Estado de cada ejecución que el cliente pudo ver activa o que empezó durante el corte: `run_id`, `status` (`"active"` o `"finished"`), `outcome` (obligatorio si terminó, prohibido si no) y `parent_run_id` (si es una subejecución). |
| `pending_approvals` | sí | Los `approval_request` aún pendientes, como mensajes PACAI completos. Lista vacía si no hay. |
| `last_messages` | no | Mensajes PACAI completos que el agente elige devolver, p. ej. el último mensaje del asistente o el `tool_start` de una herramienta abierta. |

Reglas:

- `runs` DEBE incluir toda ejecución que el cliente tuviera por activa. Las que aparecen como `finished` se dan por cerradas, con sus herramientas.
- Una ejecución terminada **nunca** se vuelve a lanzar por una reanudación: no puede aparecer como `active` en el `snapshot`.
- Las peticiones de `pending_approvals` se contestan con `approval_result` como cualquier otra. Su `expires`, si lo tienen, sigue valiendo.
- Una aprobación `session` concedida antes del corte sigue vigente.

Se RECOMIENDA retener los mensajes al menos 5 minutos en transportes de red. En stdio la sesión vive lo que vive el proceso. Para continuarla en otro proceso, el agente PUEDE ofrecer su propio mecanismo, como `alfalfa --reanudar`.

## 7. Perfiles opcionales

Un perfil se activa solo si ambos lados lo declaran en `hello`.

### 7.1 `voice`

- Añade el bloque `audio` y el mensaje **`voice_turn`**, con `payload.state` igual a `"client_speaking"`, `"agent_listening"` o `"barge_in"`.
- Con `barge_in`, el agente DEBE cortar el audio en curso.
- Los tramos de audio durarán como mucho 250 ms, y se RECOMIENDA incluir siempre la transcripción.

### 7.2 `shared_state`

Añade `state_snapshot` (objeto completo de la raíz propia) y `state_delta` (JSON Patch, RFC 6902). El estado tiene dos raíces:

- `/agent`: solo la modifica el agente;
- `/client`: solo la modifica el cliente.

Así **el cliente también puede enviar estado**, como la pantalla abierta, la batería o «el usuario está ocupado», sin conflictos. Cierra el hueco 1 del 0.1.

Cada lado envía `state_snapshot` solo con su clave (`agent` o `client`) y parches cuyos `path` (y `from` en `move`, que borra el origen) empiecen por su raíz. Tocar la raíz del otro lado es un `error` `invalid_message`. El estado NO DEBE contener secretos.

### 7.3 `work`

Es el perfil de los agentes que trabajan sobre archivos, como AlfalfaCode o Codex:

- **`plan_updated`**: `run_id` y `steps`, cada uno con `text` y `status` (`pending`, `in_progress` o `completed`).
- **`diff_updated`**: `run_id`, `files` (cada uno con `path`, `added` y `removed`) y `patch`, un diff unificado opcional. Es el **diff acumulado** de esa ejecución: todos los cambios desde su `run_started` hasta ese momento, no solo los del último paso. Cada `diff_updated` de una ejecución sustituye al anterior. Lo calcula el agente; la especificación no dice de dónde sale (instantáneas, git u otro mecanismo).

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
- Los nombres de sus tipos, campos, valores y códigos de error DEBERÍAN seguir el estilo del núcleo: en inglés y en `snake_case`, p. ej. `alfalfa.budget` con `spent` y `limit`, no `alfalfa.presupuesto` con `gastado`. El espacio de nombres (`<espacio>.*`) no cambia.
- Si una extensión resulta útil para muchos, pasa al núcleo o a un perfil en una versión futura.

## 9. Seguridad

| Riesgo | Medida |
|---|---|
| Aprobar otra cosa de lo que se ve | Digest de los argumentos canonizados y comprobación antes de ejecutar (§4.5). |
| Tomar el silencio por un sí | Sin respuesta no se ejecuta nunca, caduque o no. `expires` opcional, EOF como negación, `cancelled` explícito al terminar o interrumpir, `reply_to` exacto y valores estrictos. |
| Aprobar lo que no se ve entero | Una llamada con `truncated` no se puede aprobar (§4.4). Los secretos tachados se tachan siempre igual, y el digest cubre lo que se ve. |
| Un resultado tardío que reabre trabajo | Lo que llega tras un `cancelled` del agente (aprobación o herramienta del cliente) se ignora, y la ejecución en cierre no empieza trabajo nuevo (§4.2). |
| Repetir mensajes | Deduplicar por `id` y comprobar huecos en `seq`. |
| Una aprobación `session` que se estira | Solo cubre el mismo `name` y el mismo digest, y cada uso se ve en `tool_start.approval_id`. |
| No saber qué subagente pide permiso | La petición lleva el `run_id` de la subejecución, y su `run_started` dice qué agente es (§4.9). |
| Relanzar trabajo al reconectar | Una ejecución terminada nunca vuelve a `active` en un `snapshot` (§6). |
| Fugas en el estado o en los registros | El estado no lleva secretos. No se registran los datos de `audio` ni de `file`. |
| Mensajes enormes | Límite negociado y `error` `message_too_large`. |
| Herramienta con descripción engañosa | La descripción no es autoridad: el cliente muestra el nombre, los argumentos y el digest. |
| Canal sin cifrar | `wss://` y HTTPS en red. stdio solo entre procesos locales. |

## 10. Conformidad

| Nivel | Requisito |
|---|---|
| **PACAI-Core** | Núcleo completo (§2–§4, subejecuciones incluidas) sobre un transporte. Un agente no está obligado a lanzar subagentes, pero un cliente DEBE aceptarlos (§4.9). |
| **PACAI-Core+Resume** | Además, reanudación (§6) sobre un transporte de red. |

Cada perfil se declara aparte, por ejemplo «PACAI-Core + work + expression». Una implementación conforme produce sesiones que `conformance/verificar.py` acepta, y rechaza los casos de `conformance/invalid/`.

## 11. Cambios desde la 0.2

La 0.3 sale de implementar la 0.2 en AlfalfaCode (`alfalfa --pacai`) y de compararla, el 2026-11-15, con ACP de Zed, el app-server de Codex, Claude Code y su Agent SDK, AG-UI, A2A y MCP. Cambia lo mínimo; todo lo demás sigue igual. Un agente o un cliente pueden admitir las dos versiones y negociarlas con `hello.versions`.

**Lo que rompe la compatibilidad con la 0.2:**

1. **Versión del sobre:** `"pacai": "0.3"`, y el esquema es `schema/pacai-0.3.schema.json`.
2. **Aprobaciones pendientes al terminar o interrumpir (§4.5, §4.6):** en la 0.2 se daban por negadas en silencio. Ahora el agente DEBE resolverlas con un `approval_result` `cancelled` antes del `tool_end` `cancelled` de su herramienta. `decision` admite el valor nuevo `cancelled`, que solo envía el agente. Al cerrarse la sesión (`close` o EOF) siguen contando como negadas, sin mensajes.
3. **Subagentes en segundo plano (§4.9):** la herramienta que lanza una subejecución PUEDE terminar antes que ella. La 0.2 lo prohibía. Un cliente 0.2 que esperase que la tarjeta de `spawn_agent` siguiera abierta mientras trabaja el subagente debe dejar de suponerlo.
4. **Herramientas del cliente (§4.4):** el agente PUEDE cerrar una con `tool_end` `cancelled` cuando la ejecución termina o se interrumpe. Un cliente 0.3 debe aceptar ese `tool_end` y no contestar con error a su propio resultado tardío.
5. **Encadenar tras el `hello` (§4.1):** el cliente PUEDE enviar mensajes sin esperar a `session_started`. Un agente 0.3 debe aceptarlos. En la 0.2 eran un error.

**Lo que se añade, se aclara o se precisa:**

6. **`expires` es opcional (§4.5).** Sin él, la petición no caduca, como en Claude Code («los permisos no caducan»), ACP y Codex. El agente no puede declarar `expired` en una petición sin `expires`.
7. **`run_started.tool_call_id` (§4.9):** pasa de PUEDE a obligatorio cuando una herramienta lanzó la subejecución, como `parent_tool_use_id` en Claude Code y `parentToolCallId` en AG-UI.
8. **Ejecución en cierre (§4.2):** tras un `cancelled` del agente, la ejecución ya no empieza trabajo nuevo. Hace verificable que esos `cancelled` solo se usen al terminar o interrumpir.
9. **Argumentos de `tool_start` (§4.4):** son los reales y completos, como el `rawInput` de ACP; `title` es la parte legible. El agente PUEDE tachar secretos con `"[redacted]"`. Campo nuevo `truncated` para los argumentos acortados por tamaño, que no se pueden aprobar.
10. **Estilo de las extensiones (§8):** DEBERÍAN usar inglés y `snake_case`, como el núcleo, igual que en los demás protocolos. El esquema de nombres `<espacio>.*` no cambia.
11. **`diff_updated` (§7.3):** es el diff acumulado de la ejecución, lo calcula el agente y cada uno sustituye al anterior. La especificación no dice de dónde sale.

**Lo que se decidió no cambiar:**

- Una subejecución sigue sin sobrevivir a su madre (§4.9, «Por qué así», punto 4).
- Lo que el cliente envía antes de su `hello` sigue siendo un error, como el «Not initialized» de Codex; a diferencia de MCP, que en su revisión 2026-07-28 quitó el saludo, PACAI lo mantiene porque negocia perfiles, extensiones y herramientas del cliente.

Los cambios de la 0.1 a la 0.2 están en `spec/historico/PACAI-0.2.md`, §11.

## Anexo A. De `alfalfa --stdio` v2 a PACAI

| v2 | PACAI 0.3 |
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
| `subagentes` | subejecuciones del núcleo: `run_started` con `parent_run_id` (§4.9) |
| `presupuesto`, `procesos`, `navegador`, `despierto`, `cuota`, `compactar`… | extensión `alfalfa.*` |

## Anexo B. Pendiente

El contenido técnico de la 0.3 está cerrado. Antes de publicar el repositorio queda una decisión:

1. **Nombre:** comprobar marcas, repositorios y dominios de «PACAI».

Resueltos en la 0.2: la licencia (Apache-2.0 para la especificación, el esquema, los ejemplos y los SDK; ver `LICENSE` y `NOTICE`), subagentes y ejecuciones en paralelo (§4.9), la relación con AG-UI (anexo C, informativo) y los SDK de Python y Swift (`sdk/`).

Resueltos en la 0.3: las siete decisiones abiertas al implementar `alfalfa --pacai` (§11).

## Anexo C. Correspondencia con AG-UI (informativo)

Este anexo **no es normativo**. PACAI no es una extensión de AG-UI ni necesita un puente para ser conforme. Sirve a quien quiera traducir entre los dos, por ejemplo para servir un agente PACAI a un frontend hecho con CopilotKit. AG-UI se publica con licencia MIT, así que se puede implementar un puente sin restricciones; aquí solo se citan los nombres de sus eventos.

Consultado el 2026-11-12 en <https://docs.ag-ui.com/concepts/events>, <https://docs.ag-ui.com/concepts/subagents> y <https://docs.ag-ui.com/concepts/interrupts>.

### C.1 Dos modelos distintos

- **AG-UI** es un flujo de eventos **por ejecución**: el cliente envía un `RunAgentInput` (hilo, mensajes, herramientas del frontend, estado) y recibe eventos hasta `RunFinished` o `RunError`. Para pedir permiso, la ejecución **termina** con una interrupción y el cliente abre otra con `resume`.
- **PACAI** es una **sesión** bidireccional y duradera, con un sobre común, `seq` por emisor y `reply_to`. La ejecución sigue viva mientras espera una aprobación, y el cliente también envía estado, herramientas y entradas en caliente.

Un puente PACAI → AG-UI hace corresponder la `session` con el `threadId` y cada `run_id` raíz con un `runId`.

### C.2 De PACAI a AG-UI

| PACAI | AG-UI | Qué se pierde |
|---|---|---|
| `hello` / `session_started` | Sin equivalente; las capacidades se fijan por configuración. | La negociación vinculante de versión, perfiles y extensiones. |
| `input` `new_run` | Un `RunAgentInput` nuevo. | La cola: AG-UI no encola, así que el puente espera al final de la ejecución anterior. |
| `input` `steer` | Sin equivalente. | Corregir una ejecución en marcha; el puente solo puede esperar y abrir otra. |
| `run_started` (raíz) | `RunStarted` | Nada relevante. |
| `run_started` con `parent_run_id` | `SubagentStarted`: `subagentRunId` = `run_id`, `name` y `description` de `agent`, `parentToolCallId` = `tool_call_id`, y `parentSubagentRunId` si la madre es otra subejecución. Los eventos del subagente llevan `subagentRunId`. | Nada relevante. **Ojo:** el `parentRunId` de `RunStarted` es otra cosa (linaje entre ejecuciones sucesivas de un hilo) y no se usa para esto. |
| `run_finished` `success` | `RunFinished` con `outcome` `success`, o `SubagentFinished`. | Nada. |
| `run_finished` `failed` / `blocked` | `RunError` (o `SubagentError`) con `message` = `detail`. | La diferencia entre fallo y bloqueo, salvo que se codifique en `code`. |
| `run_finished` `interrupted` | `RunError` con un `code` propio. | AG-UI no tiene un resultado «interrumpido por el usuario». |
| `message_start` / `message_delta` / `message_end` | `TextMessageStart` / `TextMessageContent` / `TextMessageEnd` | Los bloques que no son texto (`file`, `structured`, `audio`): van como `Custom` o se pierden. |
| `tool_start` (`side` `agent`) | `ToolCallStart` + un `ToolCallArgs` con los argumentos completos + `ToolCallEnd` | `title` y `truncated`. |
| `tool_end` | `ToolCallResult` | `status` y `summary`, salvo que se metan en `content` o `metadata`. |
| `tool_start` (`side` `client`) / `tool_end` del cliente | Herramienta del frontend: va en `RunAgentInput.tools`, el agente emite `ToolCall*` y el resultado vuelve en el siguiente `RunAgentInput`. | La respuesta dentro de la misma ejecución: AG-UI la termina y abre otra. |
| `approval_request` | `RunFinished` con `outcome` `interrupt`: `reason` `tool_call`, `toolCallId`, `expiresAt` (si hay `expires`) y `message`. | El **digest** (solo cabe en `metadata`, y AG-UI no exige comprobarlo), el `reason` de PACAI y los `scopes`. La ejecución termina en vez de esperar. |
| `approval_result` | `resume` en el siguiente `RunAgentInput`, con `payload` `{"approved": true}` o `false`. | El alcance `session` y su reutilización con `approval_id`. El `expired` del agente pasa a ser un `RunError` cuando llega una respuesta tardía, y el `cancelled`, a cerrar la interrupción abierta sin `resume`. |
| `interrupt` | Cancelar la petición HTTP. | No hay evento: se pierden los `tool_end` `cancelled` y el cierre ordenado de subagentes. |
| `usage` | `metadata` de los eventos (uso de tokens). | La forma fija de los campos y el coste. |
| `heartbeat` | Lo resuelve el transporte. | Nada. |
| `error` | `RunError` si ocurre dentro de una ejecución. | Los errores fuera de una ejecución y los códigos estables. |
| `close` | Fin del flujo. | El motivo. |
| `snapshot` | `MessagesSnapshot` + `StateSnapshot`, y las aprobaciones pendientes como interrupciones abiertas. | El estado de cada ejecución. |
| `seq`, reenvío y reanudación | Sin equivalente; depende del transporte. | La detección exacta de huecos y la reanudación sin repetir trabajo. |
| `voice_turn` | Sin equivalente. | El turno hablado y el `barge_in`. |
| `state_snapshot` / `state_delta` | `StateSnapshot` / `StateDelta` (también RFC 6902) | Las dos raíces: en AG-UI el estado es uno y el cliente lo manda en `RunAgentInput.state`. |
| `plan_updated` / `diff_updated` | `ActivitySnapshot` (p. ej. `activityType` `PLAN`) o `Custom`. | La forma normalizada. |
| `expression` | `Custom` con `name` `pacai.expression`. | El vocabulario común: el frontend AG-UI no sabe qué significa. |
| Extensiones (`alfalfa.*`) | `Custom` con `name` igual al tipo. | La negociación. |

### C.3 De AG-UI a PACAI

| AG-UI | PACAI | Qué se pierde |
|---|---|---|
| `RunStarted.parentRunId` (linaje, viaje en el tiempo) | Sin equivalente. | La ramificación de ejecuciones. |
| `StepStarted` / `StepFinished` | `plan_updated` si está activo `work`; si no, nada. | Los pasos sin el perfil `work`. |
| `TextMessageStart.role` `developer` | `role` `system` | La distinción entre `developer` y `system`. |
| `TextMessageChunk`, `ToolCallChunk` | Se expanden a inicio, contenido y fin. | Nada. |
| `ToolCallArgs` en streaming | El puente acumula hasta `ToolCallEnd` y emite un solo `tool_start`. | Ver los argumentos mientras se escriben: PACAI exige argumentos completos para poder calcular el digest. |
| Eventos de razonamiento (`Reasoning*`) | Se descartan. | Todo: en PACAI el razonamiento vive en el agente. |
| Interrupción `input_required` o `confirmation` | Un mensaje del asistente y la respuesta como `input`. | El `responseSchema`. |
| Aprobar con cambios (`editedArgs`) | Una `approval_request` nueva con los argumentos editados y su digest. | Nada; PACAI lo hace explícito. |
| `MessagesSnapshot` con el historial completo | `snapshot.last_messages` | PACAI no transporta el historial entero. |
| `Raw`, `Custom` | Una extensión negociada, o se descartan. | Lo que no tenga extensión. |
| `RunAgentInput.context` y `forwardedProps` | Sin equivalente. | El contexto adicional del frontend. |
| Sin equivalente | `hello` con perfiles y extensiones | El puente los fija por configuración. |
