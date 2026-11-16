# pacai (Python)

SDK de PACAI 0.3. Solo depende de `jsonschema`, y únicamente para validar. Requiere Python ≥ 3.11.

| Módulo | Qué hace |
|---|---|
| `pacai.types` | `TypedDict` del sobre y de cada payload, y tablas: emisor, perfil y códigos de error. |
| `pacai.builder` | `MessageBuilder`: rellena el sobre, lleva `seq` e inventa ids. |
| `pacai.jcs` | `canonicalize` (JCS, RFC 8785) y `digest` para aprobaciones. |
| `pacai.schema` | `validate` / `is_valid` contra el esquema empaquetado. |
| `pacai.stdio` | `StdioTransport`, `encode`, `decode` y `read_messages` (JSONL). |
| `pacai.session` | `Session`: las reglas de sesión que usa `conformance/verificar.py`. |

Uso y pruebas: ver el README de la raíz del repositorio.
