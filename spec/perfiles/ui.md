# Perfil `ui` de PACAI (borrador 1)

> Estado: **borrador**, con las preguntas del primer borrador resueltas (sección 9). El motor de AlfalfaCode
> ya lo habla, y la app de Mac, la extensión de VS Code y una demo web dibujan las pantallas (sección 8).
> Puesto al día el 27 de noviembre de 2026 con lo que usa AlfalfaCode: `example` en los componentes propios,
> `required` en `Select` y la sección 10 (lo que escribe el modelo es asunto del agente).
> Esquema: [`pacai-ui-1.schema.json`](../../schema/pacai-ui-1.schema.json). Ejemplo completo:
> [`ejemplos/ui-tickets.jsonl`](ejemplos/ui-tickets.jsonl).

El perfil `ui` deja que el agente dibuje pantallas dentro del chat mientras conversa: tarjetas, tablas,
formularios, botones, gráficos. El cliente las va mostrando a medida que llegan, y lo que el usuario hace en
ellas (pulsar un botón, enviar un formulario) vuelve al agente como un mensaje más de la conversación.

Funciona con PACAI 0.3 tal como está: no añade tipos de mensaje. Usa tres piezas que el núcleo ya tiene:

| Pieza del núcleo | Para qué la usa `ui` |
| --- | --- |
| `hello.payload.render` | El cliente declara qué sabe dibujar (su catálogo de componentes). |
| bloque `structured` en `message_start`, `message_delta` y `message_end` | El agente manda las pantallas, por partes. |
| bloque `structured` en `input` | El cliente devuelve las acciones del usuario. |

**AlfalfaUI** es el nombre del kit de AlfalfaCode que implementa este perfil: los renderizadores de la app
de Mac (SwiftUI) y de la extensión de VS Code (web), y el traductor del motor. El formato es de PACAI y vale
para cualquier agente.

## 1. Ideas de partida

- **El cliente manda en lo que se dibuja.** El agente solo puede usar los componentes que el cliente declaró.
  Nada de HTML, scripts ni estilos libres.
- **Se dibuja mientras llega.** Una pantalla es una lista plana de nodos. Cada nodo llega solo y se muestra en
  cuanto llega; los hijos pueden llegar después que el padre.
- **Cambiar es mandar lo que cambia.** Un nodo con un `id` que ya existe reemplaza al anterior. En el turno
  siguiente el agente manda solo los nodos nuevos o distintos.
- **Una pantalla siempre puede reconstruirse.** Al cerrar el mensaje, el agente manda la pantalla completa.
  Un cliente que reanuda o llega tarde no tiene que reconstruir la historia.
- **Todo se valida con JSON Schema.** Lo que ya usa PACAI. El cliente no tiene que analizar ningún lenguaje
  propio. Cómo escribe el modelo las pantallas por dentro es asunto del agente (sección 10).

## 2. Negociación

El cliente pide el perfil en `profiles` y describe lo que sabe dibujar en `render.ui`:

```json
{"type": "hello", "sender": "client", "payload": {
  "versions": ["0.3"], "profiles": ["work", "ui"], "extensions": ["alfalfa"],
  "render": {"ui": {
    "version": "1",
    "catalog": "base",
    "components": {
      "Ticket": {"description": "Un ticket con su estado", "props": {"type": "object",
        "properties": {"title": {"type": "string"}, "status": {"enum": ["open", "closed"]}},
        "required": ["title"]}, "children": false, "events": ["press"]}
    },
    "actions": ["send", "set", "open_url"],
    "limits": {"max_nodes": 300, "max_depth": 12}
  }}
}}
```

| Campo | Significado |
| --- | --- |
| `version` | Versión del perfil. Este borrador es la `"1"`. |
| `catalog` | `"base"` (los 12 componentes de la sección 4) o `"none"` (solo los de `components`). Por defecto, `"base"`. |
| `components` | Componentes propios del cliente. Cada uno: `description` (para el modelo), `props` (JSON Schema), `children` (si admite hijos), `events` y, opcional, `example`: de 1 a 4 nodos `pacai.ui/1` que enseñan al modelo a usarlo (enlaces `{"$": …}`, la forma de su `query`…). Un nombre propio no puede pisar uno del catálogo base. |
| `actions` | Acciones que el cliente sabe ejecutar. Por defecto, las tres. |
| `limits` | Nodos por pantalla y profundidad máxima. Por defecto, 300 y 12. |

Si el agente admite el perfil, lo incluye en los `profiles` de `session_started`. Si el cliente pide `ui`
sin `render.ui`, vale el catálogo base con todas las acciones y los límites por defecto. Un agente que no
negoció `ui` no manda pantallas; un cliente que recibe un bloque `pacai.ui/1` sin haberlo negociado lo ignora.

## 3. Pantallas: lo que manda el agente

Una **vista** es una pantalla con nombre (`view`). Vive toda la sesión: el agente puede actualizarla en
mensajes posteriores. Dónde se muestra lo sugiere el agente con `placement` (`inline`: en el mensaje donde
apareció por primera vez; `latest`: en el último mensaje que la tocó). Sin esa pista, decide el cliente.

El agente la manda en bloques `structured` con `schema: "pacai.ui/1"`, dentro de los mensajes de siempre:

```json
{"type": "message_delta", "payload": {"message_id": "m_00000011", "blocks": [
  {"type": "structured", "schema": "pacai.ui/1", "data": {
    "view": "tickets", "op": "patch", "rev": 1,
    "nodes": [
      {"id": "root", "component": "Stack", "children": ["titulo", "tabla", "nuevo"]},
      {"id": "titulo", "component": "Text", "props": {"text": "3 tickets abiertos", "style": "title"}}
    ]
  }}
]}}
```

| Campo | Significado |
| --- | --- |
| `view` | Nombre de la vista, único en la sesión. `[a-z][a-z0-9_]*`. |
| `op` | `patch`: mezcla los nodos con los que ya hay. `replace`: la vista completa; lo que no venga se borra. |
| `rev` | Revisión de la vista. Sube en cada bloque que la toca. El cliente descarta un bloque con `rev` menor o igual que el que ya tiene. |
| `nodes` | Nodos nuevos o que cambian. |
| `remove` | Ids de nodos que se borran (solo en `patch`). |
| `state` | Valores iniciales o nuevos del estado de la vista (sección 5). En `patch` se mezclan por clave. |
| `alt` | Resumen en texto de la vista, para accesibilidad, registros y clientes que no dibujan. Obligatorio en `replace`. |
| `placement` | Opcional. `inline` o `latest` (ver arriba). Vale la última pista recibida para esa vista. |

### Nodos

```json
{"id": "enviar", "component": "Button", "props": {"label": "Crear", "variant": "primary"},
 "events": {"press": {"send": "crear_ticket", "with": ["title", "priority"]}}}
```

| Campo | Significado |
| --- | --- |
| `id` | Único dentro de la vista. La raíz se llama `root`. |
| `component` | Componente: uno del catálogo negociado. |
| `props` | Propiedades, según el esquema del componente. Un valor `{"$": "nombre"}` se lee del estado de la vista. |
| `children` | Ids de los hijos, en orden. Solo en componentes que admiten hijos. |
| `events` | Qué hacer en cada evento del componente (sección 5). |

Reglas para dibujar mientras llega:

1. El cliente dibuja desde `root`. Un hijo que todavía no llegó no ocupa sitio (o muestra un hueco de
   carga); cuando llega, aparece en su lugar.
2. Un nodo con un `id` conocido reemplaza al anterior **entero** (no se mezclan sus `props`).
3. Un nodo que nadie referencia no se dibuja. Un ciclo en `children` se corta en el primer nodo repetido.
4. Al terminar el mensaje (`message_end`), el agente manda un `replace` de cada vista que el mensaje tocó.
   Es la foto de referencia: si difiere de lo que el cliente fue montando, gana la foto.

### Validación

- **El agente valida antes de mandar.** Un nodo con un componente fuera del catálogo, propiedades que no
  cumplen su esquema o más nodos que `max_nodes` no sale. AlfalfaCode se lo dice al modelo para que lo corrija.
- **El cliente es tolerante.** Si aun así le llega un nodo que no entiende, no lo dibuja y sigue. Nunca
  rompe la sesión por una pantalla.

## 4. Catálogo base

Doce componentes que cualquier cliente con `catalog: "base"` sabe dibujar. El esquema exacto de sus
propiedades está en `pacai-ui-1.schema.json` (`$defs/base_props`).

| Componente | Propiedades principales | Hijos | Eventos |
| --- | --- | --- | --- |
| `Stack` | `direction` (`vertical`/`horizontal`/`grid`: tarjetas en columnas según el ancho), `gap` (`none`/`small`/`medium`/`large`) | sí | — |
| `Card` | `title`, `subtitle`, `image` (`https:` o `data:image/…`), `meta` (línea pequeña: «19 nov · Salud»), `tags` (etiquetas), `detail` (texto largo que el usuario despliega con «Ver más», sin llamar al agente) | sí | `press` |
| `Text` | `text` (texto plano, sin markdown), `style` (`body`/`title`/`subtitle`/`caption`/`muted`) | no | — |
| `Table` | `columns` (`[{key, label}]`), `rows` (lista de objetos) | no | `row_press` |
| `List` | `items` (`[{id, title, subtitle?}]`) | no | `item_press` |
| `Button` | `label`, `variant` (`primary`/`secondary`/`danger`), `disabled` | no | `press` |
| `Form` | `submit_label` | sí | `submit` |
| `Input` | `name`, `label`, `kind` (`text`/`number`/`multiline`/`email`/`date`), `placeholder`, `required` | no | `change` |
| `Select` | `name`, `label`, `options` (`[{value, label}]`), `multiple`, `required` (empieza sin opción elegida y el `Form` no se envía hasta elegir una) | no | `change` |
| `Chart` | `kind` (`bar`/`line`/`pie`), `labels`, `series` (`[{name, values}]`) | no | — |
| `Image` | `src` (`https:` o `data:image/…`), `alt` (obligatorio) | no | — |
| `Code` | `code`, `language` | no | — |

El aspecto (colores, tipografía, márgenes) es del cliente: la app de Mac dibuja con SwiftUI y VS Code con su
tema. El agente describe **qué** hay, no **cómo** se ve.

## 5. Estado y acciones

### Estado de la vista

Cada vista tiene un estado: un objeto plano de valores. Los campos de un formulario (`Input`, `Select`) leen
y escriben en él la clave de su `name`. Cualquier propiedad puede leerlo con `{"$": "clave"}`. El agente da
valores iniciales con `state`; el usuario los cambia al escribir. El estado vive en el cliente: el agente solo
lo ve cuando una acción `send` se lo manda. (La ruta `/client/ui/` de `shared_state` queda reservada para una
versión futura; un cliente de la versión 1 no escribe en ella.)

### Acciones

En `events`, cada evento lleva una acción o una lista de acciones, que se ejecutan en orden:

| Acción | Forma | Qué hace |
| --- | --- | --- |
| `send` | `{"send": "nombre", "with": ["clave", …]}` | Devuelve la acción al agente con los valores pedidos del estado. Sin `with`, manda todo el estado. |
| `set` | `{"set": {"clave": valor}}` | Cambia el estado de la vista. No llama al agente. |
| `open_url` | `{"open_url": "https://…"}` | Abre un enlace. Solo `https:`. El cliente puede pedir confirmación. |

Como mucho un `send` por evento. Las acciones solo se disparan por un gesto del usuario: el cliente nunca
manda un `send` por su cuenta. El evento `change` solo admite `set`: llamar al modelo en cada tecla gastaría un
turno por pulsación. No hay acción que ejecute una herramienta sin pasar por el modelo.

### Lo que manda el cliente

Un `send` se convierte en un `input` con un bloque `structured` de `schema: "pacai.ui.action/1"` y, delante,
un bloque `text` con un resumen legible:

```json
{"type": "input", "sender": "client", "payload": {"blocks": [
  {"type": "text", "text": "Crear ticket: «Error al iniciar sesión», prioridad alta"},
  {"type": "structured", "schema": "pacai.ui.action/1", "data": {
    "view": "tickets", "rev": 3, "node": "enviar", "event": "press", "name": "crear_ticket",
    "values": {"title": "Error al iniciar sesión", "priority": "high"}
  }}
]}}
```

- Sin una ejecución en marcha, el `input` abre una nueva (`new_run`, el modo por defecto). Con una en
  marcha, va como `steer` con su `run_id`.
- `item` dice sobre qué elemento fue el evento: en `row_press`, la fila pulsada (el objeto de `rows`); en
  `item_press`, el `id` del elemento de la lista. Los demás eventos no lo llevan.
- `rev` es la revisión de la vista que el usuario tenía delante. Si el agente ya la cambió, la acción puede
  estar desfasada; el agente se lo dice al modelo y el modelo decide.
- Tras un `send`, el cliente desactiva el control que lo disparó hasta que llegue una revisión nueva de la
  vista o termine la ejecución. Evita el doble envío.
- El bloque `text` es lo que el usuario «dijo». Un cliente que no conozca el perfil, o un registro, lo
  entiende sin dibujar nada.

## 6. Reanudar y llegar tarde

El `replace` de cada `message_end` es la foto de la vista. Un `snapshot` lleva los últimos mensajes en
`last_messages`; con el último `message_end` de cada vista, el cliente la dibuja como estaba. El estado que el
usuario había escrito y no envió se pierde: vive solo en el cliente que lo tenía.

## 7. Seguridad

- **Sin código.** Ni HTML, ni scripts, ni CSS, ni markdown que se interprete. `Text` es texto plano.
- **Enlaces e imágenes.** `open_url` solo con `https:` y siempre por un gesto del usuario. `Image` solo con
  `https:` o `data:image/png|jpeg|gif|webp`. El cliente puede no cargar imágenes remotas (revelan que la
  pantalla se abrió) o pedir permiso.
- **Nada de credenciales.** El agente no debe pedir contraseñas ni tarjetas en un formulario, y el cliente
  puede negarse a dibujar un `Input` cuyo `name` o `label` lo sugiera. Un formulario del agente nunca debe
  parecer una pantalla del sistema o de otra aplicación.
- **Límites.** El cliente aplica `max_nodes`, `max_depth` y `limits.max_message_bytes` del núcleo aunque el
  agente no lo haga.
- **Lo que vuelve es entrada del usuario.** Una acción `send` llega al agente con la misma confianza que un
  mensaje escrito. Los permisos de las herramientas no cambian por venir de un botón.

## 8. Cómo lo hace AlfalfaCode (informativo)

Esto no forma parte del perfil; es cómo encaja en el motor de [AlfalfaCode](https://github.com/0sw2ld0/AlfalfaCode), y las rutas de esta sección son de ese repositorio. El código está en `alfalfa/pacai/ui.py`, y las
pruebas en `tests/test_pacai_ui.py`.

1. **Negociación.** `alfalfa --pacai` ofrece `ui` en su `hello`. Si el cliente lo pide, el transporte valida su
   `render.ui` contra `$defs/declaration`. Una declaración inválida recibe `error` `invalid_message` y la
   sesión sigue sin el perfil.
2. **Prompt.** Con `ui` negociado, el motor añade al prompt de sistema, en cada petición, una sección generada
   desde el catálogo (`Catalogo.manual()`): los componentes, sus propiedades y eventos, las acciones que el
   cliente ejecuta y cuándo conviene dibujar en vez de escribir.
3. **Salida del modelo.** El modelo escribe la pantalla en un bloque cercado. Hasta la versión 0.99.56, en PACAI
   UI Lang con GPT-6 Luna y Claude Haiku 5.5; en `main`, con todos los modelos (sección 10). Con
   `ALFALFA_PACAI_UI_LANG=0`, o con los demás modelos hasta la 0.99.56, un nodo JSON por línea:

   ````text
   ```pacai-ui view=tickets placement=latest
   {"id":"root","component":"Stack","children":["titulo","tabla"]}
   {"id":"titulo","component":"Text","props":{"text":"3 tickets abiertos","style":"title"}}
   {"state":{"priority":"medium"}}
   ```
   ````

   Además de los nodos, el bloque admite tres líneas especiales: `{"remove":[ids]}`, `{"state":{…}}` y
   `{"alt":"…"}`. El traductor separa el texto de los bloques (`partir`) y valida cada nodo contra el catálogo.
   Cada bloque sale como un `patch` en su propio `message_delta`, y al final el `message_end` lleva la foto
   (`replace`) de cada vista que el mensaje tocó. El bloque no sale como texto; lo que el modelo escriba antes
   y después, sí. Una valla sin cerrar (respuesta cortada) se procesa igual.
4. **Lo rechazado.** Los nodos que no pasan la validación no salen. El cliente recibe
   `alfalfa.ui_rejected` (`view`, `errors`) si negoció la extensión `alfalfa`.
5. **Historia.** El modelo conserva en su historia el bloque tal como lo escribió, así puede mandar solo los
   nodos que cambian en el turno siguiente.
6. **Acciones.** Un `input` con `pacai.ui.action/1` se valida contra `$defs/action` y llega al modelo como un
   mensaje del usuario: el texto del cliente, `[Acción en la pantalla]` y los datos en JSON. Si la `rev` es
   anterior a la actual, se añade un aviso de que la acción puede estar desfasada. Sin el perfil, la acción
   recibe `not_negotiated`.
7. **Granularidad.** El motor entrega el texto del modelo mensaje a mensaje, no token a token. Por eso hoy las
   pantallas llegan cuando el modelo termina cada mensaje, no mientras lo escribe. El formato ya admite que
   llegue nodo a nodo; queda pendiente pasar el texto en vivo desde el proveedor.
8. **Demo web.** [`docs/demos/pacai-ui/`](https://github.com/0sw2ld0/AlfalfaCode/tree/main/docs/demos/pacai-ui) tiene un renderizador web del catálogo
   base (`ui.js`, sin dependencias) y un chat que lo usa, con AlfalfaCode o con un agente simulado.
9. **App de Mac.** Pide `ui` en su `hello` con el catálogo base (`PacaiScreens.swift`). El modelo puro está en
   `AlfalfaKit/Screens/` (`Screen`, `ScreenUpdate`, `ScreenNode`, `ScreenValue`): aplica los bloques y resuelve los
   eventos sin SwiftUI, y lo prueban `ScreenTests` y `ScreenFlowTests`. Las pantallas llegan con el texto de su
   mensaje (`AgentEvent.screens`) y entran en la conversación como elementos `.screen`, que `ScreenTimeline`
   coloca según `placement`. Las vistas (`AlfalfaCode/Session/Screens/`) sólo dibujan: tabla, lista, formulario,
   campos, desplegable, gráfico con Swift Charts, imagen y código. Con `--stdio` v2, una acción sale como un
   mensaje con su texto legible.
10. **Extensión de VS Code.** Pide `ui` en su `hello` (`lib/pacai.js`) y dibuja con una copia idéntica del `ui.js`
    de la demo (`media/ui.js`; una prueba falla si se separan), cargado como módulo por `media/ui-global.js`. Las
    acciones van del panel a la extensión (`accionPantalla`) y de ahí al agente; los enlaces los abre la
    extensión tras preguntar, y las imágenes remotas no se cargan (se ve su `alt`).
11. **Pendiente.** Que el modelo se entere de los nodos rechazados para corregirlos, y cómo se ven las pantallas
    al reanudar una sesión guardada (sin comprobar). En la app de Mac y en VS Code las pantallas de un mensaje
    salen debajo de todo su texto, no entre los párrafos donde las escribió el modelo.
12. **Un ejemplo por componente en el prompt.** El manual lleva un nodo de ejemplo por componente base y el
    `example` de cada componente propio que pase su propio esquema. Son unos 600 tokens más; en un piloto con
    GPT-6 Luna y Claude Haiku 5.5, las pantallas válidas a la primera pasaron del 86–89 % al 97 %.
13. **La valla vale aunque no empiece la línea.** `Aquí está:```pacai-ui view=x` se reconoce, y el texto de delante
    sale como texto normal.
14. **Las pantallas se guardan con la sesión.** Con `--pacai --reanudar` cada vista sigue por su revisión siguiente, y
    una acción sobre una pantalla de antes de reanudar llega al modelo como cualquier otra.
15. **Reparaciones que no cambian lo pedido.** Por ejemplo, si una vista nueva no trae `root`, el motor añade uno
    que envuelve los nodos sueltos, sin cambiar ningún id. Lo demás que no valida se rechaza y se le pide al modelo
    que lo corrija.
16. **Prototipo, apagado: el manual bajo demanda.** Con `ALFALFA_PACAI_UI_MANUAL=1` el modelo carga el manual con
    una herramienta en vez de llevarlo siempre en el prompt. Se midió que dibuja menos pantallas, así que no se
    enciende por defecto.
17. **«Vista enriquecida».** El cliente puede apagar las pantallas sin renegociar la sesión con la orden
    `alfalfa.set_rich_view` (`active`). Apagada, el modelo no recibe el manual de pantallas y contesta en texto; las
    que ya dibujó se siguen viendo. En `main`, la app de Mac y VS Code la traen apagada por defecto; el motor la
    deja encendida para un cliente que no manda la orden.

El detalle, con sus medidas, está en el
[perfil `ui` de AlfalfaCode](https://github.com/0sw2ld0/AlfalfaCode/blob/main/docs/pacai/perfil-ui.md), secciones 8 y 10.

## 9. Decisiones (24 de noviembre de 2026)

Las preguntas abiertas del primer borrador, ya resueltas:

1. **Dónde se muestra una vista que se actualiza: pista del agente.** El campo opcional `placement` de una
   actualización dice `inline` (la vista se queda en el mensaje donde nació) o `latest` (se mueve al último
   mensaje que la tocó, y en su sitio anterior queda una foto estática). Sin `placement`, decide el cliente.
   Vale la última pista recibida.
2. **`change` no puede llevar `send`.** Solo admite `set`. Un filtro en vivo se hace con estado local; para
   llamar al agente hace falta un gesto explícito (`press`, `submit`, `row_press`, `item_press`). Así no se
   gasta un turno del modelo por tecla. El esquema lo comprueba.
3. **No hay acción `call` en la versión 1.** Todo lo que vuelve al agente pasa por el modelo con `send`. Una
   acción que ejecute una herramienta sin el modelo abre más superficie de seguridad; se reevaluará con casos
   reales.
4. **El estado de la vista es local.** Vive en el cliente y solo viaja con `send`. La ruta `/client/ui/<vista>`
   de `shared_state` queda reservada para una versión 2 que refleje el estado en vivo; un cliente de la
   versión 1 no debe escribir en ella.
5. **Coste en tokens: medido.** Con la vista final del ejemplo (tabla de 3 tickets y formulario de 2 campos),
   contada con el tokenizador `o200k_base` (el de Claude es distinto; las proporciones sirven de guía):

   | Forma | Tokens |
   | --- | --- |
   | La misma información en markdown, sin interacción | 75 |
   | `pacai-ui`, vista completa | 276 |
   | `pacai-ui` con claves de una letra (`c`, `p`, `kids`, `on`) | 276 |
   | Sintaxis de línea al estilo OpenUI Lang (aproximada) | 197 |
   | `pacai-ui`, turno siguiente con `patch` (2 nodos) | 158 |

   Conclusiones: una pantalla cuesta unas 3,7 veces lo que el texto equivalente, y un 40 % más que una
   sintaxis propia de línea. El `patch` ahorra un 43 % frente a reescribir la vista. Se acepta ese 40 % a cambio
   de validar con JSON Schema y no tener que escribir un analizador en cada cliente.

   *Después (26 de noviembre de 2026):* el ahorro se recupera sin tocar a los clientes. El modelo puede escribir
   en una forma compacta y el agente la traduce a `pacai.ui/1` antes de mandarla, así que el analizador está en
   un solo sitio, el agente (sección 10).
6. **Claves legibles.** El primer borrador usaba claves de una letra (`c`, `p`, `kids`, `on`) para ahorrar
   tokens, pero no ahorran nada: `c` y `component` son un token cada una. El coste está en la puntuación de
   JSON y en los datos. Los nodos usan `component`, `props`, `children` y `events`, que el modelo y las
   personas entienden mejor, y la declaración de un componente propio dice `children` en vez de `kids`.

## 10. Lo que escribe el modelo es asunto del agente

El perfil fija lo que viaja entre el agente y el cliente: nodos `pacai.ui/1` en bloques `structured`, y acciones
`pacai.ui.action/1` de vuelta. No fija cómo los produce el agente. Un agente basado en un modelo de lenguaje puede
dejar que el modelo escriba las pantallas en JSON, en una forma abreviada o como prefiera, siempre que:

- traduzca lo que escribe el modelo a nodos `pacai.ui/1` antes de mandarlos;
- valide cada nodo contra el catálogo del cliente (sección 3, «Validación») y no mande lo que no lo cumple;
- ponga él la revisión (`rev`) de cada vista, sin dejarla en manos del modelo.

El cliente no nota la diferencia ni tiene que conocer la forma abreviada.

**El ejemplo de AlfalfaCode: PACAI UI Lang.** Es una línea por nodo,
`id Componente "texto principal" clave=valor > hijos`, con las acciones tras `@evento=`. La misma tarjeta en las dos
formas que puede escribir su modelo (49 y 86 tokens, `o200k_base`):

```text
root Card "Palta Hass" meta="hoy · fruta" > nota,ver
nota Text "Sube un 3 % esta semana."
ver Button "Ver historial" variant=primary @press={"send":"ver_historial"}
```

```text
{"id":"root","component":"Card","props":{"title":"Palta Hass","meta":"hoy · fruta"},"children":["nota","ver"]}
{"id":"nota","component":"Text","props":{"text":"Sube un 3 % esta semana."}}
{"id":"ver","component":"Button","props":{"label":"Ver historial","variant":"primary"},"events":{"press":{"send":"ver_historial"}}}
```

En los dos casos, el `message_end` lleva al cliente los mismos tres nodos `pacai.ui/1`. En las medidas de AlfalfaCode
(52 tareas, GPT-6 Luna y Claude Haiku 5.5, 416 pantallas por formato), la forma abreviada sale válida a la primera
tanto como el JSON o más (416/416 frente a 407/416) y cuesta en torno a un 40 % menos por pantalla correcta.

- Explicación con diagrama: [docs.pacai.dev/ui-lang.html](https://docs.pacai.dev/ui-lang.html).
- Gramática, reparaciones y medidas completas: la sección 10 del
  [perfil `ui` de AlfalfaCode](https://github.com/0sw2ld0/AlfalfaCode/blob/main/docs/pacai/perfil-ui.md).
