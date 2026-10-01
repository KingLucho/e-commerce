# Contratos de API — Fase 0

Este documento fija los contratos de Usuarios, Productos y Ventas para la implementación posterior. Los ejemplos omiten campos no relevantes. Los errores usan el formato estándar de FastAPI: `{"detail": "mensaje"}` para errores explícitos y el formato estándar de `detail` para validación. No se añaden códigos de error propios.

Las fechas y horas se serializan en ISO 8601 UTC, por ejemplo `2026-09-28T14:30:00Z`. Los importes monetarios se representan como cadenas decimales JSON (por ejemplo, `"19.99"`) para conservar la precisión de `NUMERIC(10,2)`. Los secretos y hashes nunca se devuelven.

Los tres servicios exponen además `GET /health`, que devuelve HTTP `200` con `{"status":"healthy","service":"<nombre>"}` cuando la API responde.

## Alcance de endpoints y ausencia de borrado

Los contratos se limitan a los endpoints enumerados explícitamente en los apartados 1.1, 1.2 y 1.3 de la Fase 1:

- **Usuarios:** `POST /usuarios`, `GET /usuarios/{id}`, `GET /usuarios`, `PUT /usuarios/{id}`.
- **Productos:** `POST /productos`, `GET /productos/{id}`, `GET /productos`, `PUT /productos/{id}/stock`.
- **Ventas:** `POST /ventas`, `GET /ventas/{id}`, `GET /ventas?usuario_id=X`.

No se añade un endpoint `DELETE` a ninguno de los servicios. La checklist de Fase 0 menciona genéricamente «CRUD básicos», pero no define rutas ni comportamiento de borrado; los apartados 1.1–1.3 sí enumeran los endpoints que se implementarán. En particular, borrar una venta exigiría definir cómo revertir el descuento de stock y cómo conservar el historial, reglas que el ejercicio no especifica.

## Usuarios

| Endpoint | Método | Request | Response de éxito |
|---|---|---|---|
| `/usuarios` | POST | `{nombre, email, password, pais?}` | `201 Created`: `{id, nombre, email, fecha_registro}` |
| `/usuarios/{id}` | GET | — | `200 OK`: `{id, nombre, email, fecha_registro, pais}` |
| `/usuarios` | GET | Query opcional `page`, `size` | `200 OK`: `{items, page, size, total}` |
| `/usuarios/{id}` | PUT | Actualización parcial; para crear: `{nombre, email, password, pais?}` | Si existe, `200 OK`; si no existe, `201 Created`. En ambos casos: `{id, nombre, email, fecha_registro, pais}` |

### Reglas de Usuarios

- `POST /usuarios` requiere `nombre`, `email` y `password`. `pais` es opcional y anulable.
- `nombre` se recorta; no puede quedar vacío ni superar 100 caracteres. La longitud máxima se comprueba después del recorte.
- `email` se recorta, se valida como dirección de correo y se normaliza a minúsculas. Su máximo es 150 caracteres después del recorte. Un email duplicado devuelve `409 Conflict`.
- `password` requiere al menos 8 caracteres. Se conserva exactamente como se recibe, incluidos los espacios; se almacena hasheado y nunca se devuelve.
- `pais` omitido o `null` al crear se guarda como `null`. Si se proporciona como cadena, se recorta; se rechaza si queda vacío y se limita a 50 caracteres después del recorte.
- `POST /usuarios` no incluye `pais` en su respuesta.
- Los IDs de ruta deben ser enteros positivos. Cero o negativos producen error de validación. Un ID positivo inexistente en `GET` produce `404 Not Found`.
- `GET /usuarios` usa `page=1` y `size=20` por defecto. Ambos deben ser enteros positivos y `size` no puede superar 50; valores inválidos se rechazan con error de validación.
- Cada `items` contiene `{id, nombre, email, fecha_registro, pais}`. El orden es `id` ascendente. `total` es el total de usuarios, independiente de la página. Una página fuera de rango devuelve `200 OK`, `items: []` y el total real.
- `PUT /usuarios/{id}` actualiza parcialmente un usuario existente. Se admiten `nombre`, `email`, `password` y `pais`; debe incluir al menos un campo modificable.
- En un usuario existente: `nombre: null`, `email: null` y `password: null` se rechazan con error de validación. Email y contraseña siguen las reglas de normalización y validación indicadas arriba. Un email que pertenezca a otro usuario produce `409 Conflict`.
- En un usuario existente, `pais` omitido o `pais: null` no modifica el valor guardado. Una cadena se recorta; si queda vacía o supera 50 caracteres se rechaza.
- Si el ID de ruta no existe, el body de `PUT` debe incluir `nombre`, `email` y `password`; `pais` es opcional. Se crea el usuario con un ID generado por la base de datos: **el ID de la ruta no se reutiliza**. La respuesta es `201 Created` con la representación completa y el ID generado. Un email duplicado produce `409 Conflict`.

## Productos

| Endpoint | Método | Request | Response de éxito |
|---|---|---|---|
| `/productos` | POST | `{nombre, precio, descripcion?, categoria?, stock?}` | `201 Created`: `{id, nombre, descripcion, categoria, precio, stock, fecha_creacion}` |
| `/productos/{id}` | GET | — | `200 OK`: `{id, nombre, descripcion, categoria, precio, stock, fecha_creacion}` |
| `/productos` | GET | Filtros opcionales `categoria`, `precio_min`, `precio_max` | `200 OK`: lista simple de productos completos |
| `/productos/{id}/stock` | PUT | `{ajuste}` | `200 OK`: producto completo actualizado |

### Reglas de Productos

- `POST /productos` requiere únicamente `nombre` y `precio`. `descripcion` y `categoria` son opcionales y anulables; `stock` es opcional y por defecto vale `0`.
- `nombre` se recorta; no puede quedar vacío ni superar 150 caracteres. La longitud se comprueba después del recorte.
- `precio` es un importe decimal no negativo, representable por `NUMERIC(10,2)`: máximo 8 dígitos enteros y 2 decimales. Más de dos decimales o exceder el rango produce error de validación; la API no redondea.
- `descripcion` se conserva exactamente. Omitirla o enviar `null` guarda `null`; la cadena vacía es distinta de `null`.
- `categoria` omitida o `null` se guarda como `null`. Si es una cadena, se recorta y normaliza a minúsculas; si queda vacía o supera 50 caracteres después del recorte, se rechaza.
- `stock` inicial debe ser entero entre 0 y el máximo de `INT` de PostgreSQL (`2147483647`). Los negativos, decimales y valores superiores se rechazan.
- `GET /productos` devuelve todos los resultados en una lista simple, sin paginación ni metadatos, ordenados por `id` ascendente. Sin filtros devuelve todos los productos; sin coincidencias devuelve `200 OK` y `[]`.
- El filtro `categoria` se recorta y normaliza a minúsculas antes de buscar, y la coincidencia ignora mayúsculas/minúsculas. Si se proporciona y queda vacío o supera 50 caracteres tras normalizarlo, se rechaza.
- `precio_min` y `precio_max` pueden usarse por separado o juntos. Cada uno es no negativo y respeta el límite de `NUMERIC(10,2)`. Los límites son inclusivos: `precio >= precio_min` y `precio <= precio_max`. Si ambos se envían, debe cumplirse `precio_min <= precio_max`.
- En `GET /productos/{id}`, ID no positivo produce error de validación; un ID positivo inexistente devuelve `404 Not Found`.
- `PUT /productos/{id}/stock` recibe un `ajuste` entero distinto de cero. Positivo suma y negativo resta. El nuevo stock debe permanecer entre 0 y `2147483647`.
- Si el ajuste dejaría el stock negativo, devuelve `409 Conflict` y no modifica el stock. Si el resultado supera el máximo de `INT`, devuelve error de validación y no modifica el stock. Un producto inexistente devuelve `404 Not Found`.

## Ventas

| Endpoint | Método | Request | Response de éxito |
|---|---|---|---|
| `/ventas` | POST | `{usuario_id, items: [{producto_id, cantidad}]}` | `201 Created`: `{id, usuario_id, fecha, total, estado, items}` |
| `/ventas/{id}` | GET | — | `200 OK`: `{id, usuario_id, fecha, total, estado, items}` |
| `/ventas` | GET | Query obligatorio `usuario_id` | `200 OK`: lista simple de ventas completas |

Cada elemento de `items` en respuestas de Ventas contiene `{producto_id, cantidad, precio_unitario}`. `total` y `precio_unitario` son cadenas decimales. Los estados posibles son `pendiente`, `completada` y `cancelada`.

### Reglas de Ventas

- `usuario_id` debe ser un entero positivo dentro del rango de `INT` de PostgreSQL. Ventas lo conserva como referencia lógica y no consulta Usuarios para comprobar su existencia.
- `items` debe contener al menos una línea. Cada `producto_id` debe aparecer una sola vez; duplicados producen error de validación.
- Cada `producto_id` debe ser un entero entre 1 y `2147483647`. Cada `cantidad` debe ser un entero entre 1 y `2147483647`.
- Ventas consulta Productos para verificar existencia, precio actual y stock suficiente de todas las líneas. Un producto inexistente devuelve `404 Not Found`; stock insuficiente durante la validación devuelve `409 Conflict`. En ambos casos no se crea una venta ni se ajusta stock.
- El total se calcula usando las cantidades y precios actuales obtenidos de Productos. Debe poder representarse en `NUMERIC(10,2)` —máximo 8 dígitos enteros y 2 decimales—; si excede el rango, se rechaza antes de crear la venta o modificar stock.
- Tras validar todas las líneas, Ventas crea una fila `pendiente` y solicita a Productos un ajuste negativo por cada línea. Si todos los ajustes funcionan, cambia la venta a `completada` y responde `201 Created` con el detalle completo.
- Si un ajuste falla tras la validación, Ventas intenta restaurar los descuentos ya efectuados. Si la compensación funciona, la venta queda `cancelada` y la API devuelve `409 Conflict` con el ID de la venta en `detail`.
- Si Productos no responde o está temporalmente inaccesible, Ventas devuelve `503 Service Unavailable`. Si ya hay una venta pendiente y se habían efectuado descuentos, intenta compensarlos y no confirma la venta.
- Si falla una compensación, la venta queda `cancelada`, se devuelve `500 Internal Server Error` con el ID de venta en `detail` y se registra una fila por compensación fallida en `ventas_db.incidencias_compensacion`. Cada fila incluye al menos `venta_id`, `producto_id`, cantidad pendiente de restaurar y error.
- `GET /ventas/{id}` exige ID positivo; un ID no positivo produce error de validación y uno positivo inexistente devuelve `404 Not Found`.
- `GET /ventas` exige `usuario_id` entero positivo dentro del rango de `INT`. No comprueba que exista en Usuarios. Devuelve una lista simple sin paginación, con todos los estados, ordenada por `id` descendente. Si no hay ventas (incluido un usuario inexistente en Usuarios), devuelve `200 OK` y `[]`.

## Resumen de estados HTTP

- `200 OK`: consultas y actualizaciones completadas.
- `201 Created`: altas de Usuarios, Productos y Ventas; también creación por `PUT` de Usuarios.
- `404 Not Found`: recurso individual inexistente o producto referenciado que no existe.
- `409 Conflict`: email duplicado, stock insuficiente o conflicto de stock durante un ajuste.
- `422 Unprocessable Entity`: errores de validación según FastAPI.
- `500 Internal Server Error`: fallo de compensación de stock, con incidencia persistida.
- `503 Service Unavailable`: Productos no responde o está temporalmente inaccesible durante la operación de Ventas.
