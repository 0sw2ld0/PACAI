# Propuesta para PACAI 0.4: avisos y varios clientes

- **Fecha:** 2026-11-18.
- **Estado:** propuesta para que Oswaldo la revise. **No cambia la especificación**: PACAI 0.3 sigue cerrada y es la vigente.
- **De dónde sale:** el alcance de YuntaKit (`yuntakit/yuntakit`, `docs/ALCANCE.md`, borrador 2). Oswaldo decidió el 2026-11-18 que **los avisos del agente tienen que funcionar** en la primera versión de YuntaKit, y que **varios clientes** también hacen falta.
- Los nombres de mensajes y campos van en inglés, como en el núcleo.

## 1. Los dos huecos

1. **El agente no puede hablar primero.** En la 0.3 todo lo que dice el agente va dentro de una ejecución, y toda ejecución raíz nace de un `input` del cliente (`run_started` exige `input_id`). No hay forma de decir «la papa bajó de precio» si nadie preguntó.
2. **Una sesión es un agente y un cliente.** `sender` es `"agent"` o `"client"`, sin más. No hay forma de que el iPhone y la app de Mac vean la misma conversación, ni de que el agente sepa por cuál avisarte.

## 2. Perfil `notifications` (para cerrar en la 0.4)

Un perfil nuevo, opcional como los demás: solo vale si los dos `hello` lo declaran.

### 2.1 Mensajes

| Tipo | Emisor | Para qué |
|---|---|---|
| `notification` | agente | Un aviso que el agente da por su cuenta, dentro o fuera de una ejecución. |
| `notification_ack` | cliente | Qué pasó con el aviso: llegó, se mostró o se descartó. |
| `notification_withdrawn` | agente | Retira un aviso que ya no vale: se atendió en otro cliente, caducó o lo sustituyó otro. |

**`notification.payload`:**

| Campo | Oblig. | Descripción |
|---|---|---|
| `notification_id` | sí | Id estable del aviso. Es el mismo en todas las sesiones y todos los clientes por los que se entregue (§3), así que **no** es el `id` del mensaje. |
| `title` | sí | Una línea, como mucho 120 caracteres. Es lo único que puede salir por un canal externo, como una notificación del sistema (§2.3). NO DEBE llevar secretos ni datos personales de terceros. |
| `blocks` | sí | El contenido completo, con los bloques de siempre (§3 de la 0.3). Un texto DEBE entenderse por sí solo; los datos exactos (precios, cantidades, fechas) DEBERÍAN ir además en un bloque `structured`, para que el cliente los muestre sin reescribirlos. |
| `priority` | no | `"low"`, `"normal"` (por defecto) o `"high"`. Es una sugerencia: el cliente decide cómo presentarlo. |
| `topic` | no | Agrupa avisos del mismo asunto, p. ej. `"mercado.papa"`. Un aviso nuevo del mismo `topic` sustituye al anterior que aún no se haya presentado. |
| `expects_reply` | no | `true` si el agente espera respuesta. Por defecto, `false`. |
| `expires` | no | Instante a partir del cual el aviso ya no vale. Si está, DEBE ser posterior al `time` del mensaje. |
| `run_id` | no | La ejecución que lo produjo, si lo produjo una. Si está, DEBE nombrar una ejecución activa. |

**`notification_ack.payload`:** `notification_id` y `status`, que es `"delivered"` (llegó al cliente), `"presented"` (se le mostró o se le dijo al usuario) o `"dismissed"` (el usuario lo descartó). Lleva `reply_to` con el `id` del `notification` que contesta.

**`notification_withdrawn.payload`:** `notification_id` y `reason`: `"handled_elsewhere"`, `"expired"`, `"superseded"` u otro valor con prefijo de extensión.

### 2.2 Reglas

- **Fuera de las ejecuciones.** Un `notification` sin `run_id` PUEDE llegar en cualquier momento después de `session_started`, aunque no haya ninguna ejecución activa. No abre ninguna ejecución, y no cuenta para «una ejecución no termina con nada abierto» (§4.2 de la 0.3).
- **Responder es empezar una ejecución normal.** El usuario contesta con un `input` `new_run` que añade `payload.in_reply_to_notification` con el `notification_id`. El `run_started` lleva su `input_id` como siempre, así que las reglas de las ejecuciones no cambian. El campo PUEDE ir aunque el aviso no lleve `expects_reply`.
- **Acuses en orden.** Cada `status` se envía como mucho una vez por aviso y cliente, en este orden: `delivered`, `presented` y `dismissed`. Se puede saltar `presented` (descartado sin mirarlo). Un acuse de un `notification_id` desconocido es un `error` con el código nuevo `unknown_notification`.
- **Un aviso no es un permiso.** Un `notification` nunca aprueba nada, nunca abre una herramienta del cliente y nunca hace que el cliente ejecute algo. Lo que el usuario decida después va por un `input`, como cualquier otra petición.
- **Caducar.** Pasado `expires`, el cliente NO DEBE presentar el aviso y el agente DEBERÍA retirarlo con `notification_withdrawn` `expired` en los clientes que no lo hayan descartado.
- **Sustituir.** Cuando un aviso sustituye a otro por `topic`, el agente DEBERÍA retirar el anterior con `notification_withdrawn` `superseded`.
- **Retirado es retirado.** Tras un `notification_withdrawn`, el cliente quita el aviso si aún lo muestra, y sus acuses tardíos se ignoran.

### 2.3 Con el cliente cerrado

PACAI no define cómo despertar a una app cerrada: eso es de cada plataforma (APNs en Apple, FCM en Android). Lo que sí fija:

- El servidor PUEDE avisar por esos canales con **solo** el `title` y el `notification_id`. **Los `blocks` nunca salen por un canal externo**: el contenido completo se recoge por PACAI al abrir la app.
- Al conectarse (sesión nueva o reanudada), el agente DEBE entregar los avisos pendientes de ese usuario que no hayan caducado ni se hayan retirado, conservando su `notification_id`. «Pendiente» quiere decir sin `presented` ni `dismissed` en ningún cliente.
- Una entrega repetida del mismo `notification_id` no es un aviso nuevo: el cliente la reconoce por ese id y no la presenta dos veces.

### 2.4 Lo que el cliente declara

En `hello.payload.render`, informativo: `{"notifications": {"priorities": ["low", "normal", "high"], "system": true}}`. `system: true` dice que el cliente sabe recibir avisos del sistema con la app cerrada. El agente PUEDE usarlo para elegir cliente (§3).

### 2.5 Seguridad

| Riesgo | Medida |
|---|---|
| Un aviso que se cuela como orden | Un aviso no aprueba ni ejecuta nada (§2.2). |
| Datos privados en el servidor de notificaciones de Apple o Google | Por el canal externo solo salen `title` y `notification_id` (§2.3). |
| Avisos repetidos o en bucle | `notification_id` estable, `topic` para sustituir y acuses por cliente. |
| Contenido de terceros dentro del aviso | El aviso puede resumir correos o webs. Un cliente que lo pase por otro modelo (por ejemplo, la capa de personalidad de YuntaKit) DEBE tratarlo como datos, no como instrucciones. |

## 3. Varios clientes, nivel 1: un usuario, varias sesiones (para cerrar en la 0.4)

Cada app (iPhone, Mac, CuyWorld) abre **su propia sesión** con el mismo agente. Casi todo funciona ya con la 0.3; la 0.4 solo añade:

- **Usuario («principal»).** Dos sesiones pertenecen al mismo usuario cuando así lo dice la autenticación, que sigue fuera de banda. PACAI no define cómo; YuntaKit, sí.
- **Los avisos son del usuario, no de la sesión.** Un aviso se PUEDE entregar por todas sus sesiones abiertas. Cuando un cliente envía `presented` o `dismissed`, el agente DEBERÍA retirarlo en los demás con `notification_withdrawn` `handled_elsewhere`.
- **Cuál está activo.** El cliente PUEDE publicar `/client/active` (`true` o `false`) con el perfil `shared_state`, para que el agente sepa qué app tienes delante. Si ninguna lo está, el servidor usa el canal externo (§2.3).
- **Lo que no se comparte entre sesiones.** Las aprobaciones `session` siguen valiendo solo en su sesión (§4.5 de la 0.3), y las ejecuciones de una sesión no se ven desde otra.

## 4. Varios clientes, nivel 2: varias apps en la misma conversación (boceto, sin cerrar)

Para empezar en el iPhone y seguir en el Mac viendo lo mismo, o para el multijugador de CuyWorld. **No hace falta para YuntaKit 0.1**. Se diseña ahora para que el nivel 1 no lo impida, pero se cierra cuando haya una implementación que lo pruebe.

Boceto:

- **Quién envía.** Un campo nuevo del sobre, `client_id`, obligatorio en los mensajes de cliente cuando la sesión negoció el perfil nuevo `multi_client`. `seq` se cuenta por emisor: el agente y cada `client_id` por separado.
- **Unirse a mitad.** Un cliente nuevo envía `hello` con la `session` existente, su `client_id` y `join: true`. El agente contesta `session_started` con `joined: true` y un `snapshot` (§6 de la 0.3) para ponerlo al día.
- **Ver lo que hacen los otros.** El agente reenvía a todos los clientes los mensajes de cada uno que cambian la conversación (`input`, `approval_result`, `interrupt`), tal cual, con su `client_id` y su `seq`.
- **Permisos.** Cualquier cliente puede contestar un `approval_request`. Vale el primero que llega; los demás se ignoran, como ya pasa con las respuestas tardías.
- **Herramientas del cliente.** Cada cliente declara las suyas en su `hello`. El `tool_start` con `side` `"client"` añade `target_client_id`: el que la ejecuta.
- **Estado.** La raíz `/client` pasa a `/clients/<client_id>`, cada una solo modificable por su dueño.
- **Presencia.** Un mensaje nuevo del agente, `presence`, con la lista de clientes conectados y cuál está activo.

Preguntas abiertas: si el audio (`voice`) puede venir de dos clientes a la vez; qué pasa con una aprobación `session` cuando se une un cliente con otros permisos; y cuánto tiempo se guarda la conversación para quien se une tarde.

## 5. Lo que no cambia

- El sobre, el núcleo y los perfiles de la 0.3, salvo `client_id` en el nivel 2.
- La autenticación sigue fuera de banda.
- Las herramientas internas del agente siguen siendo MCP. Un servidor como YuntaKit le da al agente su herramienta para avisar (`notify`) como un servidor MCP, y es ese servidor el que emite el `notification` hacia los clientes.

## 6. Pruebas de conformidad que habría que añadir

Válidas:
- un aviso fuera de toda ejecución y sus tres acuses;
- respuesta a un aviso con `in_reply_to_notification`;
- aviso pendiente entregado de nuevo al reanudar, con el mismo `notification_id`;
- un aviso retirado con `handled_elsewhere`.

Inválidas:
- `notification` sin el perfil negociado;
- `notification` antes de `session_started`;
- acuse de un aviso desconocido;
- `presented` después de `dismissed`;
- `notification` con `run_id` de una ejecución terminada;
- `expires` anterior al `time` del mensaje.

## 7. Lo que decide Oswaldo

1. ¿Los avisos y el nivel 1 van a una **PACAI 0.4** (versión nueva) o a una extensión `yunta.*` mientras se prueban? Recomiendo la **0.4**: los avisos son de cualquier agente y cualquier cliente, no solo de YuntaKit.
2. ¿El nivel 2 se cierra en la 0.4 o en una versión posterior? Recomiendo **posterior**, cuando CuyWorld o la app de Mac lo pidan de verdad.
3. ¿Tres prioridades (`low`, `normal`, `high`) bastan, o hace falta una urgente que se salte el «no molestar»? Recomiendo **tres**: saltarse el «no molestar» lo decide el usuario en su teléfono, no el agente.
