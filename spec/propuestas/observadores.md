# Propuesta: observadores

- **Estado:** propuesta para la 0.4 (2026-11-17). No cambia nada de lo que ya hace una sesión de la 0.3: sólo se activa
  con `observe: true` en el `hello`. El esquema y el verificador de este repositorio ya la aceptan.
- **Implementación de referencia:** AlfalfaCode (`alfalfa --pacai`, `alfalfa/pacai/observadores.py`) y su app de Mac
  (`AlfalfaKit/Pacai/PacaiObservation.swift`).
- **Palabras clave:** como en la especificación (RFC 2119/8174).

## 1. El problema

En la 0.3 una sesión tiene **un cliente**. La reanudación (§6) es ese mismo cliente que vuelve tras un corte. No hay
forma de que otro programa vea lo que pasa en una sesión que no abrió él.

El caso que lo pide: un encargo lanzado desde Claude Code (la skill `encargar-a-alfalfa`, que habla PACAI con
`alfalfa --pacai` por stdio) o desde una terminal. El usuario quiere verlo **en vivo** en la app de AlfalfaCode, como
ve sus propias sesiones: el texto, cada herramienta, el gasto y el contexto, los subagentes y los permisos
pendientes. Leer los archivos que la sesión deja en disco no basta: ahí no están el uso al momento, el plan, los
permisos pendientes ni el estado de los subagentes, y llega tarde.

## 2. La idea

Un **observador** es un cliente que mira una sesión en marcha y no participa. El cliente que la abrió es su
**dueño**: el único que escribe (`input`), interrumpe (`interrupt`), contesta permisos (`approval_result`) y ejecuta
herramientas del cliente (`tool_end`).

El observador abre **su propia sesión PACAI** por su propio transporte. Recibe primero una foto de lo que está en
marcha (`snapshot`) y después una **copia** de lo que el agente manda al dueño. Las copias conservan los `id`, así que
todo lo que remite a otro mensaje (`run_id`, `message_id`, `tool_call_id`, `approval_id`, `reply_to`) sigue valiendo.

## 3. Texto propuesto para la especificación

### §5.4 Socket Unix (`pacai+unix`)

- Para procesos locales: un socket Unix de tipo stream. Cada mensaje es una línea JSON, como en stdio (§5.1).
- La autenticación son los permisos del sistema de archivos. El agente DEBE crear el socket en una carpeta a la que
  sólo llegue el usuario (p. ej. `0700`) y DEBERÍA dejarlo en `0600`. DEBE borrarlo al terminar.
- Dónde está el socket lo dice el agente; PACAI no fija la ruta. AlfalfaCode usa `<sesiones>/<id>/vivo.sock`.
- No hace falta latido. Cerrar la conexión equivale a `close` del cliente.

### §6.1 Observadores

**Saludo.** El observador envía un `hello` con `payload.observe: true`. El agente que admite observadores contesta
con su `hello` y con `session_started` con `observe: true`. Los perfiles y las extensiones se negocian como siempre
(§4.1), y el agente sólo le copia lo que quedó activo. Un agente que no admite observadores en ese transporte (p. ej.
el stdio del proceso que lanzó, donde siempre habla el dueño) DEBE contestar `error` y cerrar; NO DEBE tratar a ese
cliente como dueño.

**Foto inicial.** Justo después de `session_started`, el agente envía un `snapshot` con `reply_to` al `hello`, con la
misma forma que al reanudar (§6):

- `runs`: cada ejecución activa, con su `parent_run_id` si es una subejecución;
- `pending_approvals`: los `approval_request` sin contestar;
- `last_messages`: lo necesario para seguir. DEBE llevar el `run_started` de cada ejecución activa y el `tool_start` de
  cada herramienta del agente abierta. PUEDE llevar el mensaje a medias (`message_start` y sus `message_delta`) y el
  último de cada estado (`usage`, `plan_updated`, extensiones).

Los mensajes dentro de la foto son los que recibió el dueño, con el `session` del observador.

**Copia.** Desde la foto, el agente envía al observador cada mensaje que envía al dueño, en el mismo orden y con el
mismo `id`, `type`, `time`, `reply_to` y `payload`, pero con el `session` y la `seq` de la sesión del observador. No
se copian:

- el saludo del dueño (`hello` y `session_started`);
- los `error` que contestan a mensajes del dueño;
- las herramientas del cliente del dueño (`tool_start` con `side: "client"` y su `tool_end`).

**Decisiones del dueño.** Cuando el dueño contesta un `approval_request`, el agente envía al observador un
`approval_result` propio con `relayed: true`, `reply_to` a la petición y la decisión del dueño (`approved` o
`denied`, con su `scope`). Es la única vez que el agente envía `approved` o `denied`, y sólo en la sesión de un
observador. Así el observador retira la tarjeta sin adivinar.

**Sólo mira.** Tras su `hello`, un observador sólo PUEDE enviar `heartbeat`, `error` y `close`. Cualquier otro
mensaje recibe `error` con el código nuevo `read_only` (no cierra la sesión) y NO DEBE llegar al trabajo del agente.

**Sin reanudación.** Un observador que se corta vuelve a conectarse y recibe otra foto. Un `hello` de observador con
`resume_after_seq` PUEDE recibir `retention_expired`.

**Nunca frena al dueño.** El agente NO DEBE esperar a un observador lento: PUEDE cortarle la conexión si se le
acumula demasiado sin leer. Al terminar la sesión, el observador recibe la copia del `close` y se cierra la conexión.

**Cuántos.** El agente decide cuántos observadores admite. Con demasiados, contesta `error` y cierra.

### Cambios en el catálogo y el esquema

| Dónde | Cambio |
|---|---|
| `hello.payload` | `observe` (booleano, opcional, solo el cliente). |
| `session_started.payload` | `observe` (booleano, opcional). |
| `approval_result.payload` | `relayed` (booleano, opcional). Con `relayed: true`, el agente envía `approved` o `denied`. |
| §4.8 | Código `read_only`: un observador envió algo que sólo envía el dueño. No cierra. |
| §10 | Conformidad: «PACAI-Core + observadores» se declara aparte. |

### Reglas que comprueba el verificador

- En la sesión de un observador, el cliente sólo envía `hello`, `heartbeat`, `error` y `close`.
- El `snapshot` contesta al `hello` del observador, sin reanudación.
- La ejecución raíz de la foto no tiene un `input` del observador: su `input_id` es del dueño.
- `relayed` sólo lo envía el agente, sólo en la sesión de un observador y sólo con `approved` o `denied`.

## 4. Lo que se descartó

1. **Ser un segundo cliente de la misma sesión, con su `session` y su `seq`.** Las `seq` son por sesión y emisor
   (§2). El `session_started` y el `snapshot` del observador ocuparían números de la secuencia del agente que el dueño
   nunca ve, y el dueño vería huecos. Con una sesión propia, cada uno tiene su numeración y las copias conservan sus
   `id`.
2. **Envolver las copias en un tipo nuevo (`observed`) con el mensaje original dentro.** Conserva las `seq` del dueño,
   pero obliga a todo cliente a desenvolver y duplica el sobre. Con la copia directa, un cliente que ya entiende PACAI
   ve una sesión normal.
3. **Reenviar todo lo retenido (`resume_after_seq: 0`) en vez de la foto.** Obliga al agente a guardar todos los
   mensajes de la sesión, y el observador repetiría lo que ya tiene (el historial en disco, en AlfalfaCode). La foto
   lleva lo justo; quien quiera más tiene el historial del agente.
4. **Que el observador también conteste permisos.** PACAI quiere una sola respuesta por petición. Con dos sitios con
   botones habría carreras («aprobé aquí y negué allí»), y el dueño es quien sabe qué encargó. Si hace falta cambiar
   de dueño, será otra propuesta («tomar el mando»).
5. **Reenviar el `approval_result` del dueño tal cual (`sender: "client"`).** En la sesión del observador sería un
   mensaje de cliente que el observador no envió, con una `seq` de cliente que no es la suya. El `relayed` del
   agente lo dice sin romper el sobre.

## 5. Seguridad

| Riesgo | Medida |
|---|---|
| Otro usuario del equipo se conecta | Socket en una carpeta `0700`, en `0600`; sólo el usuario llega a él. |
| El observador aprueba, escribe o interrumpe | Sólo envía `heartbeat`, `error` y `close`; lo demás recibe `read_only` y no llega al agente. |
| El observador ejecuta herramientas del cliente | Las herramientas del cliente del dueño no se copian. |
| Un observador lento llena la memoria del agente | El agente no espera a nadie y puede cortarle la conexión. |
| Un socket viejo de un proceso muerto | El agente lo sustituye al arrancar y lo borra al salir. |

## 6. Cómo se usa en AlfalfaCode

- `alfalfa --pacai` abre `$ALFALFA_HOME/sesiones/<id>/vivo.sock` en cuanto tiene el cerrojo de la sesión.
- En `snapshot.payload.alfalfa`, `session_id` (el id de la sesión de AlfalfaCode) e `history_until`: hasta qué hora vale
  la transcripción que AlfalfaCode guarda en disco. La app pinta el historial hasta ese corte y lo demás lo recibe en
  vivo: sin huecos ni repetidos.
- La app de Mac lo usa para las sesiones lanzadas fuera de ella (la terminal, Claude Code): las ve en vivo y enseña
  los permisos sin botones («Lo contesta quien lanzó el encargo»).
