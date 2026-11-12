# PACAI — Especificación del protocolo (borrador 0.1)

> Copia histórica del borrador 0.1 (2026-11-03). Las marcas «CA-n» remiten a los criterios del encargo que lo produjo; no forman parte del protocolo.

- **Nombre:** PACAI — *Protocolo Abierto Común Agente Interfaz*.
- **Versión de este documento:** 0.1 (2026-11-03).
- **Estado:** propuesta independiente, alternativa para evaluación (CA-18).
- **Palabras clave:** «DEBE», «NO DEBE», «REQUERIDO», «DEBERÍA» y «PUEDE» se
  interpretan como en RFC 2119/RFC 8174 solo cuando aparecen en mayúsculas.

## 1. Nombre y sigla (CA-14)

**Frase identificativa:** *PACAI es un protocolo abierto, común y general de
comunicación entre agentes e interfaces.* — identifica qué es sin necesitar
explicación y no lo limita a voz: cubre texto, voz y cualquier modalidad que
una interfaz pueda renderizar.

La sigla **PACAI** toma, en orden y sin saltos, las iniciales de las cinco
palabras reales consecutivas del nombre: **P**rotocolo **A**bierto **C**omún
**A**gente **I**nterfaz. No hay palabras de enlace intercaladas ni letras
tomadas de fuera de la secuencia; la sigla agota el nombre y el nombre agota
la sigla.

Elegí «Protocolo» como primera palabra porque declara la naturaleza del
artefacto sin ambigüedad: no es una aplicación, un SDK ni un servicio, sino un
conjunto de reglas de intercambio. «Abierto» fija la condición de estándar
público, adoptable sin licencia de un proveedor. «Común» señala el rasgo que
más lo distingue de sus vecinos: un mismo núcleo sirve a texto, web, móvil y
voz, en lugar de un protocolo por modalidad. «Agente» e «Interfaz» delimitan
la capa: agente-interfaz, no agente-herramienta (MCP) ni agente-agente (A2A).
El orden de las palabras sigue el recorrido del mensaje: del protocolo al
canal común, y del agente a la interfaz. La palabra «pacai» se pronuncia con
facilidad en español y en inglés técnico; no se comprobó que sea un término
libre en todos los registros, y los choques hallados se documentan en
`EVIDENCIA.md` (CA-15 no exige una sigla libre).

## 2. Alcance y no objetivos (CA-5)

PACAI estandariza el intercambio entre un **agente** (proceso que razona,
llama herramientas y emite contenido) y una **interfaz** (cliente de usuario:
web, aplicación móvil, terminal, cliente de voz o cualquier superficie de
renderizado). Es:

- **General:** no depende de una aplicación ni de un endpoint concreto; no
  define rutas, puertos, dominios ni nombres de servicio. Una implementación
  elige sus URLs; el protocolo solo define mensajes y su orden.
- **Multicanal:** cubre texto, web, móvil y voz mediante un núcleo común y
  perfiles opcionales (§5).
- **Bidireccional:** la interfaz puede interrumpir, aprobar, editar y
  reanudar mientras el agente emite eventos incrementales.

**No objetivos.** PACAI no define: (a) cómo un agente invoca a sus
herramientas internamente (eso es ámbito de MCP, §11); (b) cómo dos agentes
independientes se descubren y delegan trabajo (ámbito de A2A); (c) el
vocabulario visual de componentes renderizables (ámbito de A2UI);
(d) autenticación de usuarios ni autorización de largo alcance (delega en la
capa de transporte y en la aplicación).

## 3. Modelo de mensajes

### 3.1 Sobre común

Todos los mensajes PACAI son objetos JSON (UTF-8) con este sobre:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `pacai` | string | sí | Versión del protocolo, p. ej. `"0.1"`. |
| `id` | string | sí | Identificador único del mensaje: `<prefijo>_<aleatorio>`, con el prefijo de la tabla §3.1.1. |
| `tipo` | string | sí | Tipo del mensaje (catálogo §3.3). |
| `sesion` | string | sí | Identificador de sesión (§7.1). |
| `emisor` | string | sí | `"agente"` o `"interfaz"`. |
| `marca` | string | sí | Instante ISO 8601 UTC con segundos como mínimo, p. ej. `2026-11-02T10:15:30Z`. |
| `secuencia` | entero | sí | Contador monótono estrictamente creciente por sesión y emisor, empezando en 1. |
| `carga` | objeto | sí | Contenido específico del tipo. |

Reglas:

- Los campos desconocidos DEBEN ignorarse (extensibilidad hacia adelante).
- `id` es único por sesión; los receptores DEBEN descartar duplicados
  (entrega al menos una vez: la idempotencia es responsabilidad del receptor).
- `secuencia` permite reconstruir orden y detectar huecos tras una
  reconexión; un hueco NO resoluble se notifica como error de sesión
  (`error` con código `secuencia_irrecuperable`, §7.6).

#### 3.1.1 Prefijos de `id`

El prefijo es una abreviatura estable de tres o cuatro letras del tipo, no el nombre
del tipo completo; el tipo autoritativo es siempre `tipo`, y el prefijo solo
ayuda a leer trazas y a correlacionar referencias. Un `id` con prefijo
distinto del que corresponde a su `tipo` es un error de protocolo.

| Tipo | Prefijo | Tipo | Prefijo |
|---|---|---|---|
| `saludo` | `sal` | `aprobacion_solicitud` | `apr` |
| `sesion_iniciada` | `ses` | `aprobacion_resultado` | `apr` |
| `entrada` | `ent` | `interrupcion` | `int` |
| `ejecucion_inicio` | `eje` | `reanudacion` | `rea` |
| `ejecucion_fin` | `eje` | `instantanea` | `ins` |
| `mensaje_inicio` | `msg` | `turno_voz` | `trn` |
| `mensaje_delta` | `msg` | `estado_instantanea` | `est` |
| `mensaje_fin` | `msg` | `estado_delta` | `est` |
| `herramienta_inicio` | `herr` | `corazon` | `cor` |
| `herramienta_fin` | `herr` | `error` | `err` |
| `cierre` | `cie` | | |

La correlación entre mensajes se hace por el `id` completo, nunca por el
prefijo: `herramienta_fin.carga.herramienta_id`, `aprobacion_resultado
.carga.solicitud_id` y `ejecucion_inicio.carga.entrada_id` son `id` exactos de
mensajes previos.

### 3.2 Bloques de contenido

El contenido se expresa como lista de **bloques** (dentro de `carga.bloques`),
análoga a contenido multipart pero tipada:

| Bloque | Perfil | Campos | Descripción |
|---|---|---|---|
| `texto` | núcleo | `texto` (string) | Texto plano en UTF-8. |
| `audio` | voz | `medios` (string, tipo MIME, p. ej. `audio/L16;rate=16000`), `codificacion` (`"pcm16"` \| `"opus"` \| `"mp3"` \| `"base64-url"`), `datos` (string base64 o URL), `transcripcion` (string, opcional) | Tramo de audio. |
| `archivo` | núcleo | `nombre`, `medios`, `datos` (base64 o URL) | Adjunto binario. |
| `estructurado` | núcleo | `esquema` (URI), `datos` (objeto) | Datos tipados (formularios, tarjetas, vistas). |

Un mensaje `mensaje_*` PUEDE mezclar bloques (p. ej. audio + transcripción).

### 3.3 Catálogo de tipos

Núcleo (obligatorio): `saludo`, `sesion_iniciada`, `entrada`, `mensaje_inicio`,
`mensaje_delta`, `mensaje_fin`, `herramienta_inicio`, `herramienta_fin`,
`aprobacion_solicitud`, `aprobacion_resultado`, `ejecucion_inicio`,
`ejecucion_fin`, `interrupcion`, `reanudacion`, `instantanea`, `corazon`,
`error`, `cierre`.

Perfil voz: `audio` (como bloque dentro de `entrada`/`mensaje_delta`) y el
evento de control de turno hablado `turno_voz` (§5.2).

Perfil estado compartido: `estado_instantanea`, `estado_delta`.

---

## 4. Transportes (CA-6)

PACAI define dos transportes normativos. Una implementación conforme DEBE
ofrecer al menos uno; se RECOMIENDA ofrecer ambos, porque sus restricciones
son complementarias.

### 4.1 WebSocket (`pacai+ws`)

- Canal único **bidireccional y full-duplex**: agente e interfaz envían
  mensajes cuando quieran sobre la misma conexión, incluidos audio en
  tramos, interrupciones y aprobaciones (CA-9, CA-10).
- Cada mensaje PACAI viaja como **un marco de texto WebSocket** (UTF-8) con
  el sobre JSON completo. Los datos binarios (audio, adjuntos) viajan como
  base64 dentro del sobre, o como URL si el bloque lo permite; el protocolo
  NO define marcos binarios propios.
- Subprotocolo WebSocket RECOMENDADO: `pacai.v0`. La URL usa esquema `wss://`
  en producción; `ws://` se limita a desarrollo local (§9.1).
- La conexión DEBE abrirse con `saludo` como primer mensaje de cada sentido;
  el servidor responde con `sesion_iniciada` (§6.2).
- Cierre: `cierre` (con `carga.motivo`) seguido del cierre de transporte con
  código normal 1000. Un corte de transporte códigos 1006/1011 equivale a
  desconexión accidental y habilita la reanudación (§7.6).
- Latido: `corazon` en cualquier dirección al menos cada 30 s de silencio;
  si no se recibe tráfico en 90 s, el par DEBE tratar la sesión como
  interrumpida y recuperarla vía `reanudacion` (§7.5). El `corazon` no exige
  campos propios en `carga`; PUEDE incluir `carga.ultima_secuencia` (entero
  ≥ 1) con la última `secuencia` emitida por ese emisor, que sirve para
  detectar huecos sin esperar al siguiente mensaje de contenido.

### 4.2 SSE/HTTP (`pacai+sse`)

- Par de recursos HTTP separados, sin URL fijada por el protocolo:
  1. **Publicar** (`POST`): la interfaz envía UN mensaje PACAI
     (`entrada`, `aprobacion_resultado`, `interrupcion`, `reanudacion`,
     `saludo`, `cierre`) como cuerpo `application/json; charset=utf-8`.
     Respuesta `202 Accepted` con `application/problem+json` solo en error.
  2. **Escuchar** (`GET`): el agente responde `text/event-stream` y emite
     los mensajes PACAI del agente como eventos SSE, uno por línea `data:`
     seguida de línea en blanco; cada evento DEBE declarar `id:` con el
     `id` del mensaje PACAI y DEBERÍA declarar `event:` con su `tipo`.
- **Restricciones:** SSE es **unidireccional** (agente → interfaz); la voz
  full-duplex en tiempo real NO es viable por este transporte (el perfil voz
  sobre SSE solo admite tramos pregrabados en `entrada` y audio final en
  `mensaje_fin`, no streaming micrófono-altavoz simultáneo). La
  bidireccionalidad se logra combinando Publicar y Escuchar.
- **Reanudación:** tras una caída, la interfaz reabre Escuchar con la
  cabecera `Last-Event-ID` igual al último `id:` entregado; el agente DEBE
  reenviar todo lo posterior dentro de una ventana de retención RECOMENDADA
  de 5 minutos; fuera de ventana responde `204 No Content` a un
  `reanudacion` por Publicar (§7.6).
- Escuchar DEBE reintentarse con backoff exponencial con jitter (inicio
  RECOMENDADO 1 s, techo 30 s). Los proxies intermedios NO DEBEN bufferizar:
  cabeceras `Cache-Control: no-cache` y `X-Accel-Buffering: no`
  RECOMENDADAS; el agente DEBE enviar un comentario SSE `: pacai` al menos
  cada 15 s para atravesar intermediarios con tiempo de espera corto.
- Publicar y Escuchar DEBEN usar HTTPS en producción; el token de sesión va
  en cabecera `Authorization: Bearer …`, nunca en la URL (§9.1).

---

## 5. Núcleo obligatorio y perfiles opcionales (CA-7)

### 5.1 Núcleo PACAI-Core (obligatorio)

Comprende: sobre común (§3.1), negociación (§6), ejecución y mensajes de
texto (§7.2), herramientas y aprobaciones (§7.3, §8), interrupción y
reanudación (§7.4–7.6), errores y cierre (§7.7). Todo el contenido del
núcleo es textual o estructurado; **ningún mensaje del núcleo contiene
audio**. Un cliente solo de texto conforma implementando exactamente el
núcleo, sin tocar el perfil voz.

### 5.2 Perfil `voz` (opcional)

Añade el bloque `audio` (§3.2) y el evento `turno_voz`
(`carga.estado`: `"habla_interfaz" | "escucha_agente" | "barge_in"`), que
coordina el turno hablado: al recibir `barge_in`, el agente DEBE cortar el
audio en curso y confirmar con `interrupcion`. Requisitos: audio PCM16 o
Opus, tramos ≤ 250 ms durante `mensaje_delta`, y transcripción textual
RECOMENDADA en cada bloque para accesibilidad. Un par solo intercambia
bloques `audio` si ambos declararon el perfil en el `saludo` (§6.2).

### 5.3 Perfil `estado_compartido` (opcional)

Añade `estado_instantanea` (objeto JSON completo) y `estado_delta` (parche
RFC 6902). El agente emite instantáneas al inicio de cada ejecución y deltas
durante ella; la interfaz PUEDE ignorarlos sin perder conformidad del núcleo.
El estado DEBE ser serializable y NO DEBE contener secretos (§9.1).

---

## 6. Conformidad y negociación (CA-8)

### 6.1 Niveles de conformidad

| Nivel | Requisito |
|---|---|
| **PACAI-1** (núcleo mínimo) | Núcleo completo sobre **un** transporte; perfil de voz opcional y ausente. |
| **PACAI-2** (núcleo completo) | Núcleo sobre **ambos** transportes, con reanudación funcional en ambos. |
| **PACAI-3** (completo) | Núcleo + perfil `voz` + perfil `estado_compartido` sobre ambos transportes. |

La declaración de nivel es un acto público de la implementación; la
negociación de sesión (§6.2) no cambia el nivel, solo activa perfiles.

### 6.2 Negociación de versión y perfiles

Al abrir una sesión ambas partes intercambian `saludo`:

```json
{
  "pacai": "0.1", "id": "sal_7f3a91c0", "tipo": "saludo",
  "sesion": "s_propuesta_9c4e1d7b", "emisor": "interfaz",
  "marca": "2026-11-02T10:00:00Z", "secuencia": 1,
  "carga": {
    "versiones": ["0.1"],
    "perfiles": ["nucleo", "voz"]
  }
}
```

El ejemplo respeta los mínimos del esquema (`id` ≥ 8 caracteres, `sesion` ≥ 16)
y el prefijo `sal_` de `saludo` (§3.1.1).

Reglas:

- **Versión:** la versión de sesión es la primera versión de la lista del
  iniciador que el receptor también admite; si no hay ninguna común, el
  receptor responde `error` con código `version_incompatible` y cierra. La
  versión menor se ignora para compatibilidad: `0.x` habla con `0.x`.
- **Perfiles:** el conjunto activo es la **intersección** de las listas
  `perfiles`; el núcleo (`"nucleo"`) está implícito y no se negocia. El
  servidor confirma en `sesion_iniciada.carga.perfiles_activos`.
- **Prohibido degradar:** ninguna parte puede activar un perfil que la otra
  no declaró. Enviar un mensaje de un perfil no activo es un error de
  protocolo (`perfil_no_negociado`, §6.2).
- Las extensiones futuras DEBEN anunciarse como perfiles nuevos en el
  `saludo`, nunca reutilizando campos del núcleo con otro significado.

---

## 7. Sesión, ejecución, eventos y estado (CA-9)

### 7.1 Sesión

Una sesión PACAI (`sesion`) es el contexto de conversación completo entre un
agente y una interfaz. Sobrevive a cortes de transporte y a reconexiones, y
solo termina con `cierre` o por caducidad decidida por el servidor (mínimo
RECOMENDADO 24 h). Los mensajes de la sesión comparten el valor `sesion` y
dos contadores `secuencia` independientes, uno por emisor.

### 7.2 Ejecución y eventos

Cada petición de la interfaz abre una **ejecución** (`ejecucion`), ciclo
acotado dentro de la sesión:

1. `ejecucion_inicio` (agente) con `carga.entrada_id` = `id` de la entrada.
2. Cero o más grupos de mensaje: `mensaje_inicio` → `mensaje_delta`* →
   `mensaje_fin`. Los deltas del mismo mensaje comparten
   `carga.mensaje_id` y se concatenan en orden llegada.
3. Cero o más llamadas a herramienta (§7.3).
4. `ejecucion_fin` con `carga.resultado`: `"exito" | "interrumpida" |
   "error"`; en error incluye `carga.detalle`.

Una ejecución DEBE terminar siempre con `ejecucion_fin`. Una sesión puede
alojar ejecuciones secuenciales; las ejecuciones paralelas NO están
permitidas en PACAI 0.1 (segunda ejecución = error `ejecucion_en_curso`).

### 7.3 Herramientas

- `herramienta_inicio` (agente): `carga.herramienta` (nombre),
  `carga.argumentos` (objeto), `carga.aprobacion` (booleano, §8).
- `herramienta_fin` (agente): `carga.herramienta_id` (= `id` del inicio),
  `carga.estado`: `"exito" | "error" | "cancelada"`, `carga.salida`
  (bloques §3.2) y `carga.resumen` (texto corto para mostrar).
- La interfaz PUEDE ejecutar herramientas de usuario-respuesta
  (`carga.lado`: `"interfaz"` en `herramienta_inicio`) cuando el agente le
  pide una acción local (abrir diálogo, leer portapapeles): sigue el mismo
  par de eventos.
- Una herramienta cancelada por interrupción DEBE cerrarse con
  `herramienta_fin` y estado `"cancelada"` antes de cualquier `reanudacion`.

### 7.4 Interrupción

`interrupcion` (cualquier emisor): congela la ejecución actual.

- Desde la interfaz: el usuario pulsa detener o corta el audio (`barge_in`).
- Desde el agente: necesita entrada humana (p. ej. una aprobación, §8) o
  detecta un riesgo.

Al interrumpir, el agente DEBE emitir `instantanea`
(`carga.vista`: posición textual, último mensaje completo y herramientas
pendientes) que permita a la interfaz reanudar sin haber guardado nada.
Una ejecución interrumpida no emite `ejecucion_fin` hasta ser reanudada o
cerrada; su estado final es `"interrumpida"`.

### 7.5 Reanudación

`reanudacion` (interfaz): `carga.ejecucion_id` y `carga.motivo`
(`"usuario" | "reconexion" | "aprobacion"`). El agente responde con los
mensajes pendientes desde la última posición confirmada (`secuencia`) y
continúa la ejecución. Las reglas duras:

- Si la ejecución ya terminó, el agente responde `error` con código
  `ejecucion_inexistente` y NUNCA reinicia el trabajo.
- Si la interfaz desconocía el estado, el agente envía primero una nueva
  `instantanea`; la interfaz DEBE reconciliarla antes de mostrar nada.

### 7.6 Desconexión y recuperación

Corte de transporte ≠ fin de sesión. Ambas partes guardan `sesion`,
`secuencia` y último `id` visto. Al reconectar, el que perdió la conexión
envía `saludo` con la misma `sesion` y `carga.reanudar_tras_secuencia`. La
otra parte reenvía lo pendiente por orden de `secuencia`. Agotada la ventana
de retención (§4.2), el agente marca la ejecución como `error` con código
`retencion_agotada` y ofrece `instantanea` + `entrada` fresca.

### 7.7 Errores y cierre

`error` siempre incluye `carga.codigo` (snake_case estable) y
`carga.mensaje`. Códigos normados del núcleo: `version_incompatible`,
`perfil_no_negociado`, `secuencia_irrecuperable`, `ejecucion_en_curso`,
`ejecucion_inexistente`, `retencion_agotada`, `aprobacion_desconocida`,
`carga_excedida`.
`cierre` termina la sesión de forma ordenada; tras `cierre`, cualquier
mensaje posterior con la misma `sesion` DEBE descartarse.

---

## 8. Aprobaciones duraderas (CA-10)

Una **aprobación** solicita el consentimiento humano antes de ejecutar una
herramienta de `herramienta_inicio` con `carga.aprobacion: true`. Debe poder
durar **horas** (el usuario puede estar ausente) y no puede confundirse con
un resultado desconocido.

### 8.1 Ciclo

1. El agente emite `aprobacion_solicitud` con:
   - `carga.herramienta` y `carga.argumentos` (objeto JSON completo).
   - `carga.digest`: SHA-256 en hexadecimal de los argumentos **canonizados**
     (claves ordenadas, sin espacios, UTF-8), p. ej. `"sha256:ab12…"`.
   - `carga.vence`: instante ISO 8601 (RECOMENDADO ≥ 4 h, puede ser días).
2. La ejecución queda interrumpida (§7.4) hasta `aprobacion_resultado`.
3. La interfaz responde `aprobacion_resultado` con
   `carga.solicitud_id` (el `id` de la solicitud) y `carga.estado`:
   - `"aprobada"`: ejecutar una sola vez con esos argumentos exactos.
   - `"denegada"`: registrar motivo opcional `carga.motivo`.
   - `"caducada"`: pasó `vence` sin respuesta; el agente la emite también si
     decide no esperar más.
4. Si aprobada, el agente verifica que el digest de los argumentos que va a
   ejecutar coincide con el digest aprobado; si difiere, DEBE pedir una
   aprobación nueva (nunca ejecutar argumentos mutados bajo una aprobación
   previa).

### 8.2 Reglas duras

- **Un digest, una ejecución:** una aprobación autoriza como máximo UNA
  ejecución de la herramienta con los argumentos cuyo digest contiene. Volver
  a necesitar la misma herramienta exige solicitud nueva.
- **Resultado desconocido ≠ reintento:** si la interfaz no ha respondido,
  el agente NO reintenta la ejecución «por si acaso». Los únicos estados
  válidos son los de §8.1. Un `aprobacion_resultado` con `solicitud_id`
  desconocido se contesta con `error` `aprobacion_desconocida` y se ignora;
  nunca se reinterpreta como aprobación.
- **Sin ambigüedad de transporte:** con SSE, la solicitud viaja por Escuchar
  y la respuesta por Publicar; la correlación es exclusivamente por
  `solicitud_id`, nunca por orden temporal.
- **Caducidad declarada:** toda solicitud DEBE llevar `vence`; el agente
  DEBE dejar de esperar en ese instante y emitir `aprobacion_resultado`
  propio con estado `"caducada"` si la interfaz no respondió. `vence` DEBE
  ser posterior a la `marca` de la propia solicitud: una solicitud que nace
  caducada es un error de construcción, no una aprobación pendiente.

---

## 9. Seguridad y amenazas (CA-11)

### 9.1 Matriz de amenazas

| Amenaza | Vector | Medida PACAI |
|---|---|---|
| Suplantación de extremo | MITM en canal claro | TLS obligatorio en producción (`wss://`, HTTPS); validar certificado. |
| Sesión robada | Secreto `sesion` predecible | `sesion` ≥ 128 bits aleatorios; rotación en `reanudacion` tras reconexión larga. |
| Repetición de mensajes | Reenvío de paquetes | `id` único + deduplicación; `secuencia` detecta huecos/reorden. |
| Herramienta tóxica | Descripción falsa de herramienta | La descripción NO es autoridad (como en MCP): mostrar nombre + digest de argumentos, que el usuario vea lo que aprueba. |
| Aprobación confundida | Resultado desconocido tratado como sí | Regla §8.2: desconocido nunca reintenta; correlación por `solicitud_id`. |
| Audio inyectado | Tramos falsos en voz | Deduplicación por secuencia; `turno_voz` con `barge_in` corta y confirma. |
| Fuga de secretos en estado | `estado_*` con tokens/claves | §5.3: estado serializable sin secretos; el agente DEBE filtrar. |
| Log con datos sensibles | Trazas del puente | Prohibido registrar cuerpos de `audio`/`archivo`; solo metadatos. |
| DoS por mensajes gigantes | Cargas desmesuradas | Tamaño máximo 1 MiB por mensaje (RECOMENDADO); cortar y `error` `carga_excedida`. |
| Confusión de perfil | Mensaje de voz sin perfil negociado | Error `perfil_no_negociado` (§6.2) y descarte. |

### 9.2 Requisitos mínimos de despliegue

1. Autenticación fuera de banda (OAuth2, sesión de aplicación, mTLS); PACAI
   transporta el resultado pero no define el handshake.
2. Principio de mínimo privilegio en herramientas: el agente solo expone lo
   necesario, y las destructivas DEBEN llevar `aprobacion: true`.
3. No confiar en `carga.argumentos` ni en `carga.salida` como texto a ejecutar;
   ambos son datos no fiables.
4. Mantener `rawEvent`/metadatos de depuración fuera del canal de producción
   o filtrados.

---

## 10. Puentes con AG-UI (CA-12)

PACAI y AG-UI comparten el modelo «stream de eventos sobre HTTP/WebSocket».
Un puente PACAI↔AG-UI es viable en ambas direcciones con estas pérdidas:

### 10.1 PACAI → AG-UI (agente PACAI sirviendo a frontend AG-UI)

| PACAI | AG-UI | Pérdida |
|---|---|---|
| `ejecucion_inicio`/`ejecucion_fin` | `RunStarted`/`RunFinished`/`RunError` | Ninguna (mapeo 1:1). |
| Grupo `mensaje_*` | `TextMessageStart/Content/End` | Ninguna. |
| `herramienta_*` | `ToolCallStart/Args/End` | Menor: PACAI separa `aprobacion`; en AG-UI se aplana a `metadata`. |
| `aprobacion_*` | Ciclo interrupt/resume de `RunFinished.outcome=interrupt` | Pérdida del digest SHA-256 y del `vence`: AG-UI aproxima con interrupts opacos; el puente DEBE guardar el digest fuera de banda o en `metadata`. |
| `instantanea` | `MessagesSnapshot`/`StateSnapshot` | Pérdida de `vista` textual: hay que sintetizarla. |
| `turno_voz`/`barge_in` | `ActivityEvents`/interrupts | Pérdida del control sub-segundo del turno hablado; AG-UI no normaliza barge-in. |
| `secuencia` por emisor | (no existe; AG-UI confía en orden del stream) | Pérdida de detección exacta de huecos tras reconexión larga. |

### 10.2 AG-UI → PACAI (agente AG-UI sirviendo a interfaz PACAI)

| AG-UI | PACAI | Pérdida |
|---|---|---|
| `RunStarted/Finished/Error` | `ejecucion_inicio/fin` | El `parentRunId` (ramificación) se pierde: PACAI 0.1 no tiene linaje de ejecuciones. |
| `StateSnapshot/Delta` (RFC 6902) | `estado_instantanea/delta` | Ninguna (mismo formato). |
| `ToolCall*` | `herramienta_*` | Los `parentMessageId` de herramienta se pierden. |
| `TextMessageStart.role` ∈ {`developer`, `system`, `assistant`, `user`, `tool`} | `mensaje_inicio.rol` ∈ {`asistente`, `usuario`, `herramienta`, `sistema`} | El rol `developer` de AG-UI se pierde: PACAI 0.1 no lo tiene. El puente DEBE plegarlo a `sistema` o rechazar el mensaje, y declarar cuál de las dos cosas hace. |
| Interrupts y resume | `interrupcion`/`reanudacion` + `instantanea` | AG-UI no aporta digest de argumentos ni caducidad: el puente DEBE calcular el digest al traducir la solicitud y fijar un `vence` por defecto. |
| `rawEvent` | descartado o `estructurado` | Los eventos crudos del framework subyacente no cruzan el puente de forma normada. |
| (sin equivalente) | `saludo`/negociación de perfiles | AG-UI no negocia perfiles; el puente fija por configuración. |

## 11. Comparativa con protocols existentes (CA-13)

Fechas de consulta: **2026-11-03** (ver `EVIDENCIA.md` para URLs y citas).

| Aspecto | AG-UI | MCP | A2A | A2UI | PACAI |
|---|---|---|---|---|---|
| Capa | Agente ↔ interfaz de usuario | Agente ↔ herramientas/contexto | Agente ↔ agente | Agente → componentes UI | Agente ↔ interfaz (texto, web, móvil, voz) |
| Transporte | Agnóstico de transporte: SSE, webhooks, WebSocket y un binding binario propio | JSON-RPC 2.0 sobre HTTP+SSE o stdio | Enlaces JSON-RPC, gRPC y HTTP/REST sobre el mismo modelo de datos | Formato declarativo, no transporte (viaja sobre AG-UI o A2A) | WebSocket y SSE/HTTP normados |
| Modelo | Eventos tipados (16 en la descripción de arquitectura) | JSON-RPC 2.0, peticiones autocontenidas | Tareas con ciclo de vida, mensajes/partes y artefactos | Documento declarativo de UI | Sobre común + 21 tipos: 18 de núcleo y 3 de perfiles |
| Voz | Multimodal declarado; el contenido de mensaje del estándar es texto | No | No (audio como referencia de archivo en una parte) | No | Perfil voz con `turno_voz` y barge-in |
| Aprobaciones | Interrupts genéricos (HITL) | Consentimiento del usuario antes de invocar | Interacción humano-en-el-bucle por tareas de larga duración | No | Digest de argumentos + caducidad + no-reintento |
| Negociación | Declaración de capacidades informativa; cómo se obtiene queda a la implementación | Capacidades por petición e inicialización de extensiones | Agent Card y extensiones | Catálogo de componentes | `saludo`: versiones y perfiles explícitos y vinculantes |

Observaciones basadas en las fuentes consultadas:

- AG-UI se describe a sí mismo como «an open , lightweight , event-based
  protocol» para conectar agentes con aplicaciones de usuario, se declara
  «Transport Agnostic» y una de sus páginas de capacidades advierte que ningún
  enlace HTTP estándar «carries sequence numbers, resumes a stream, or defines
  a post-run channel» (docs.ag-ui.com/introduction y
  docs.ag-ui.com/concepts/architecture, consultados 2026-11-03). PACAI lo toma
  como referente más cercano; se diferencia en: núcleo/perfiles explícitos y
  vinculantes (un cliente solo de texto conforma sin voz), aprobaciones con
  digest y caducidad normadas, y reanudación por `secuencia` definida en ambos
  transportes.
- MCP «uses JSON-RPC 2.0 messages» entre hosts, clientes y servidores, con
  «stateless, self-contained requests» y «per-request capability negotiation»
  (modelcontextprotocol.io/specification/2026-07-28, consultado 2026-11-03). Es
  un protocolo agente↔herramienta: PACAI no compite con él; un agente PACAI
  puede usar MCP internamente para sus herramientas.
- A2A es «an open standard for seamless communication and collaboration
  between AI agents», opaco y orientado a delegación entre agentes, «originally
  developed by Google and donated to the Linux Foundation»; su especificación
  vigente es la 1.0.0 y declara capas de modelo de datos, operaciones y enlaces
  JSON-RPC/gRPC/HTTP-REST (a2a-protocol.org, consultado 2026-11-03). PACAI no
  modela descubrimiento de agentes ni tarjetas de agente: si la necesidad es
  agente↔agente, corresponde A2A.
- A2UI es «a declarative JSON format» para que agentes generen interfaces
  ricas, actualmente «Early stage public preview» (v0.9.1 en producción, v1.0
  candidata) y compatible con A2A y AG-UI como transporte
  (github.com/a2ui-project/a2ui, consultado 2026-11-03). PACAI transporta
  contenido estructurado pero no define el vocabulario visual: pueden
  integrarse llevando documentos A2UI dentro del bloque `estructurado`.

### 11.1 Cuándo NO conviene adoptar PACAI

1. **Frontend ya sobre CopilotKit/AG-UI:** con AG-UI funcionando, un puente
   o migración solo se justifica si se necesita el turno de voz normado o
   aprobaciones con digest; si no, quedarse en AG-UI.
2. **Solo conexión con herramientas/datos:** usar MCP; PACAI no aporta nada
   dentro del backend.
3. **Colaboración entre agentes independientes:** usar A2A; PACAI no incluye
   descubrimiento, tarjetas de agente ni delegación opaca.
4. **UI generativa rica multi-framework:** adoptar A2UI para el vocabulario
   visual y mantenerlo sobre su transporte habitual (AG-UI/A2A); PACAI no
   pretende reemplazar catálogos de componentes.
5. **Un solo canal y un solo transporte:** si solo hay chat de texto HTTPS
   sencillo sin interrupciones largas, la maquinaria de aprobaciones,
   secuencias y perfiles de PACAI es mayor que el problema.
6. **Ecosistemas cerrados:** dentro de un solo producto sin interoperabilidad
   externa, un protocolo propio mínimo puede ser más barato de mantener que
   cualquier estándar.

---

## 12. Esquema y verificación

El esquema JSON de todos los mensajes está en `esquema/pacai.schema.json`
(borrador 2020-12, disciplina de una sola variante por `tipo`). Los ejemplos
válidos e inválidos están en `ejemplos/` y se comprueban desde la raíz del
repositorio con:

```sh
python3 docs/propuestas-generales/22f5d29c33/verificar.py
```

Salida 0 = esquema válido, ejemplos válidos conformes, ejemplos inválidos
rechazados con el motivo esperado. El verificador no es normativo: la
autoridad es este documento y el esquema.


