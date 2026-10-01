# Ejercicio Integrador — Simulación de una Empresa Moderna
### Caso: plataforma de e-commerce, de extremo a extremo

**Versión:** 2.0
**Fecha:** 2026-09-24
**Audiencia:** persona que sabe programar y conoce varias tecnologías, pero no tiene experiencia concreta en estos roles ni en cómo encajan entre sí
**Duración estimada:** 1 cuatrimestre/semestre
**Entorno:** 100% local, orquestado con Docker Compose
**Modo:** un alumno solo, recorre todos los roles en secuencia

---

## 1. Objetivo y cómo usar este documento

Vas a construir, vos solo, un e-commerce completo — no para que quede bonito, sino para que en el proceso entiendas qué hace cada rol de una empresa de tecnología y por qué. Cada fase te dice **qué tenés que diseñar y por qué importa**, te da **el modelo de datos exacto** cuando corresponde, y te sugiere **qué pedirle a tu LLM de confianza** (ChatGPT, Claude) cuando te trabas en la parte puramente de implementación — la parte de pensar el diseño y tomar la decisión es tuya, la de escribir el boilerplate te la puede facilitar la IA.

Cada fase tiene esta estructura:
- **Qué rol estás ocupando y qué hace ese rol en una empresa real** (2-3 líneas de contexto)
- **Qué tenés que diseñar** (modelos de datos, contratos, esquemas — exactos, no aproximados)
- **Qué tenés que construir** (lista concreta de componentes/endpoints/archivos)
- **Prompt sugerido para tu LLM** (una plantilla de qué pedirle si te atascás en la implementación)
- **Punto de decisión** (cuando aplica): dos caminos, trade-offs reales, elegís y documentás en un ADR
- **Checklist de verificación**: comandos exactos y qué resultado esperar
- **Entregable** de la fase

No se avanza de fase sin pasar el checklist anterior. Cada decisión se documenta en `decisiones/ADR-XXX-nombre.md` (media página: qué decidiste, qué alternativas había, por qué elegiste esa).

---

## 2. Arquitectura objetivo (vista final)

```
[ Web simple: HTML+JS ]
          |
          v
[ MS Usuarios ]   [ MS Productos ]   [ MS Ventas ]
  (Postgres)          (Postgres)        (Postgres)
     |                    |                  |
     +------ CDC (Debezium o poller) --------+
                          |
                          v
                 [ Redpanda (Kafka) ]
                          |
                          v
             [ Lakehouse: MinIO + Parquet ]
              (bronze -> silver -> gold)
                          |
                          v
                [ DWH: Postgres "analytics" ]
                (esquema estrella materializado)
                   |                    |
                   v                    v
          [ Dashboards BI ]     [ Notebook Data Science ]
           (Metabase)             (scikit-learn)
                   |
                   v
        [ Agente operativo interno ]
         (Python + Ollama local)
```

---

## 3. Estructura de repositorio

```
/decisiones/                 → un ADR .md por punto de decisión
/servicios/
  /usuarios/   (FastAPI + Postgres propia)
  /productos/  (FastAPI + Postgres propia)
  /ventas/     (FastAPI + Postgres propia)
/web/
/cdc/
/lakehouse/
/dwh/                         → scripts de materialización a Postgres analytics
/bi/
/data-science/
/agente/
/seguridad/
docker-compose.yml
README.md
```

---

## FASE 0 — Arquitectura y contrato entre servicios

**Rol: Arquitecto / CTO.** En una empresa real, antes de escribir una línea de código de negocio, alguien tiene que decidir cómo van a comunicarse las piezas del sistema entre sí, para que 5 equipos distintos puedan trabajar en paralelo sin pisarse. Vos vas a hacer ese trabajo, aunque después lo implementes todo vos mismo.

**Qué tenés que diseñar:**

El **contrato** de cada microservicio: para cada uno, una tabla con columna "endpoint", "método HTTP", "qué recibe", "qué devuelve". Ejemplo del formato esperado (completalo vos con los 3 servicios):

| Servicio | Endpoint | Método | Request | Response |
|---|---|---|---|---|
| Usuarios | `/usuarios` | POST | `{nombre, email, password}` | `{id, nombre, email, fecha_registro}` |
| Usuarios | `/usuarios/{id}` | GET | — | `{id, nombre, email, fecha_registro, pais}` |

Esto es el documento que en una empresa real evita que Ventas asuma un campo que Usuarios no va a mandar nunca.

**Qué tenés que construir:**
- `docker-compose.yml` con: red común (`ecommerce_net`), y por ahora contenedores placeholder o vacíos, con `healthcheck` definido para cada uno (aunque sea un healthcheck trivial).
- Diagrama de arquitectura (el de la sección 2, adaptado si cambiaste algo).
- El documento de contratos de API (tabla de arriba, completa).

**Prompt sugerido para tu LLM:**
> "Estoy diseñando un sistema de microservicios (usuarios, productos, ventas) para un e-commerce simple. Te paso el contrato de API que definí [pegar tabla]. Revisá si hay inconsistencias o campos que un servicio necesita y otro no provee, y decime qué preguntas me faltó responder antes de empezar a programar."

**Punto de decisión — ADR-000:** ¿monolito modular que después separás, o microservicios reales desde el día uno?
- Monolito: arrancás más rápido, pero acoplás cosas que en la Fase 3 (CDC por servicio) vas a tener que desacoplar a la fuerza.
- Microservicios desde ya: más fricción inicial, pero coherente con todo lo que viene después.
Documentá tu elección y por qué, sabiendo que el resto de la guía asume microservicios separados.

**Checklist de verificación:**
- [ ] `docker compose up` levanta sin errores.
- [ ] `docker compose ps` muestra todos los contenedores `healthy` o `running`.
- [ ] Existe la tabla de contratos completa (los 3 servicios, todos los endpoints CRUD básicos).
- [ ] Existe `decisiones/ADR-000-arquitectura.md`.

**Entregable:** repo inicializado, `docker-compose.yml` base, tabla de contratos, diagrama, ADR-000.

---

## FASE 1 — Backend: los tres microservicios

**Rol: Ingeniero Backend.** Este es el rol que convierte una regla de negocio ("un cliente compra productos") en código que corre, persiste datos y no se cae. Es la base sobre la que se apoya absolutamente todo lo demás del ejercicio.

### 1.1 — MS Usuarios

**Modelo de datos (Postgres, base `usuarios_db`):**

```sql
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    pais VARCHAR(50),
    fecha_registro TIMESTAMP DEFAULT NOW()
);
```

**Endpoints a construir:**
- `POST /usuarios` → crea usuario. Recibe `{nombre, email, password}`, hashea el password antes de guardar (no lo guardes en texto plano — esto es intencional, es tu primer contacto con seguridad).
- `GET /usuarios/{id}` → devuelve el usuario (sin el hash del password).
- `GET /usuarios` → lista paginada (`?page=1&size=20`).
- `PUT /usuarios/{id}` → actualiza nombre/país.

### 1.2 — MS Productos

**Modelo de datos (Postgres, base `productos_db`):**

```sql
CREATE TABLE productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    categoria VARCHAR(50),
    precio NUMERIC(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT NOW()
);
```

**Endpoints a construir:**
- `POST /productos` → crea producto.
- `GET /productos/{id}` → detalle.
- `GET /productos?categoria=X&precio_min=Y&precio_max=Z` → listado filtrable.
- `PUT /productos/{id}/stock` → ajusta stock (sumando o restando, no reemplazando — pensá por qué esto importa para no perder consistencia si dos ventas llegan casi al mismo tiempo).

### 1.3 — MS Ventas

**Modelo de datos (Postgres, base `ventas_db`):**

```sql
CREATE TABLE ventas (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL,          -- referencia lógica, NO hay FK física entre bases distintas
    fecha TIMESTAMP DEFAULT NOW(),
    total NUMERIC(10,2) NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente'  -- 'pendiente' | 'completada' | 'cancelada'
);

CREATE TABLE ventas_items (
    id SERIAL PRIMARY KEY,
    venta_id INT REFERENCES ventas(id),
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario NUMERIC(10,2) NOT NULL
);
```

**Endpoints a construir:**
- `POST /ventas` → recibe `{usuario_id, items: [{producto_id, cantidad}]}`. **Importante:** este servicio debe llamar por HTTP al servicio de Productos para obtener el precio actual y verificar stock disponible antes de confirmar la venta — este es tu primer ejemplo real de comunicación síncrona entre microservicios, y de por qué eso introduce acoplamiento (si Productos está caído, Ventas no puede vender).
- `GET /ventas/{id}` → detalle con items.
- `GET /ventas?usuario_id=X` → historial de un usuario.

### 1.4 — Web simple
Página HTML+JS que: liste productos (llamando a `GET /productos`), permita "agregar al carrito" en memoria del navegador, y al confirmar llame a `POST /ventas`.

**Prompt sugerido para tu LLM:**
> "Necesito un microservicio en FastAPI con SQLAlchemy para [usuarios/productos/ventas], con este esquema de tabla: [pegar el CREATE TABLE de arriba], y estos endpoints: [pegar lista]. La conexión a Postgres debe tomarse de variables de entorno (`DATABASE_URL`). Generame el modelo, el esquema Pydantic y los endpoints. No necesito autenticación todavía, eso lo agrego en la fase siguiente."

**Punto de decisión — ADR-001:** modelo de datos de Productos, ¿normalizado (tabla separada de categorías con su propio id) o desnormalizado (categoría como texto plano en la misma tabla, como está arriba)?
- Ya te di la versión desnormalizada como base. Si elegís normalizar, documentá el cambio y por qué — y tené en cuenta que en la Fase 4 vas a tener que reflejar esa decisión en el modelo analítico.

**Checklist de verificación:**
- [ ] `/docs` (Swagger) de cada servicio carga sin error y muestra todos los endpoints.
- [ ] `curl -X POST http://localhost:<puerto_usuarios>/usuarios -d '{...}'` devuelve `201` con el JSON del usuario creado.
- [ ] Crear un producto y luego hacer `GET /productos/{id}` devuelve exactamente lo que se guardó.
- [ ] Completar una compra desde la web resulta en una fila nueva en `ventas` y en `ventas_items` (verificable con `SELECT * FROM ventas;` dentro del contenedor de Postgres).
- [ ] Si intentás vender un producto con stock insuficiente, la API devuelve un error controlado (no un 500 crudo).
- [ ] Existe `decisiones/ADR-001-modelo-productos.md`.

**Entregable:** 3 microservicios + web, todo levantado con `docker compose up`.

---

## FASE 2 — Observabilidad y seguridad de base

**Rol: DevOps / Ingeniero de Seguridad.** En una empresa real, nadie "termina" el backend y después "agrega" seguridad — pero para este ejercicio lo separamos así justamente para que veas el antes y el después, y entiendas por qué en producción esto se hace desde el día uno.

**Qué tenés que diseñar:**
- Lista de variables de entorno que cada servicio necesita (`DATABASE_URL`, `JWT_SECRET`, etc.) y dónde viven (`.env`, nunca en el código).
- Estructura mínima de log por request: `timestamp, servicio, endpoint, método, status_code, duración_ms`.

**Qué tenés que construir:**
- Middleware de logging en cada microservicio que registre cada request con esos campos.
- `.env` por servicio, agregado a `.gitignore`.
- Autenticación entre servicios: generá un JWT al "loguearse" (`POST /usuarios/login` devuelve un token), y exigí ese token en los endpoints de escritura de Ventas (`POST /ventas`).
- Correr `gitleaks` sobre el repo completo.

**Prompt sugerido para tu LLM:**
> "Quiero agregar autenticación JWT simple a este endpoint FastAPI [pegar código del endpoint POST /ventas]. Necesito un endpoint de login que devuelva un token, y un middleware/dependency que valide ese token en los endpoints protegidos. Explicame también qué debería ir en el `.env` y por qué no debe subirse al repo."

**Checklist de verificación:**
- [ ] `gitleaks detect --source .` no reporta hallazgos.
- [ ] `POST /ventas` sin header `Authorization` devuelve `401`.
- [ ] `POST /ventas` con un token válido devuelve `201` como antes.
- [ ] Los logs de cada servicio muestran, para cada request, los 5 campos definidos arriba.
- [ ] `git check-ignore .env` confirma que el archivo está ignorado.

**Entregable:** logging + `.env` + JWT entre servicios + reporte limpio de `gitleaks`.

---

## FASE 3 — CDC y streaming

**Rol: Ingeniero de Datos.** Acá aparece la pregunta central de la ingeniería de datos moderna: ¿cómo se entera el resto de la empresa (analítica, IA, reporting) de que algo cambió en una base operacional, sin tener que darle acceso directo a esa base?

**Qué tenés que diseñar:**
- Convención de nombres de topics: `ecommerce.usuarios`, `ecommerce.productos`, `ecommerce.ventas` (un topic por entidad).
- Formato del evento que viaja por Kafka/Redpanda — ejemplo mínimo esperado:
```json
{
  "operacion": "INSERT",
  "tabla": "ventas",
  "timestamp": "2026-09-24T10:15:00Z",
  "datos": { "id": 123, "usuario_id": 5, "total": 59.90, "estado": "completada" }
}
```

**Qué tenés que construir:**
- Redpanda en `docker-compose.yml`.
- Un mecanismo que capture cada INSERT/UPDATE en las 3 tablas principales (`usuarios`, `productos`, `ventas`) y publique un evento con el formato de arriba al topic correspondiente.

**Prompt sugerido para tu LLM:**
> "Quiero implementar Change Data Capture desde Postgres hacia Redpanda (compatible con Kafka). Te explico mi caso: [pegar tus 3 tablas]. Contame las diferencias prácticas entre usar Debezium con Kafka Connect versus escribir yo mismo un poller en Python que consulta filas nuevas y las publica — qué configuración necesita cada opción y qué tan complejo es levantarlo en Docker Compose."

**Punto de decisión — ADR-002:** Debezium real vía Kafka Connect, o poller Python simplificado.
- Debezium: más fiel a un entorno de producción real (captura desde el WAL de Postgres, no pierde eventos), pero más piezas para configurar (Kafka Connect, conectores, configuración de replicación lógica en Postgres).
- Poller Python: heredás la lógica vos mismo (más simple de entender y depurar), pero es menos robusto (puede perder eventos si el poller se cae entre lecturas, y depende de un campo de "última modificación" bien mantenido).

**Checklist de verificación:**
- [ ] `docker compose ps` muestra Redpanda `healthy`.
- [ ] Creás un usuario vía API → aparece un mensaje nuevo en el topic `ecommerce.usuarios` (verificable con `rpk topic consume ecommerce.usuarios` o la consola de Redpanda).
- [ ] El mensaje capturado tiene el formato JSON definido arriba, con los datos correctos.
- [ ] Repetís la prueba para productos y ventas.
- [ ] Existe `decisiones/ADR-002-cdc.md`.

**Entregable:** pipeline CDC de las 3 BBDD hacia Redpanda, funcionando.

---

## FASE 4 — Lakehouse y modelo analítico

**Rol: Ingeniero de Datos / CDO.** Acá es donde se separa por primera vez "el dato para que el negocio funcione" de "el dato para entender el negocio". Son necesidades distintas y por eso viven en sitios distintos.

**Qué tenés que diseñar — el modelo analítico (esquema estrella):**

```
dim_tiempo
  fecha_id (PK)     -- formato YYYYMMDD
  fecha
  dia_semana
  mes
  anio

dim_usuario
  usuario_id (PK)
  nombre
  pais
  fecha_registro

dim_producto
  producto_id (PK)
  nombre
  categoria
  precio_actual

fact_ventas
  venta_id (PK)
  fecha_id (FK -> dim_tiempo)
  usuario_id (FK -> dim_usuario)
  producto_id (FK -> dim_producto)
  cantidad
  precio_unitario
  total_linea
```

Notá que `fact_ventas` está a nivel de línea de venta (un producto por fila), no a nivel de venta completa — es la granularidad correcta para poder sumar por producto, por usuario o por fecha sin perder información.

**Qué tenés que construir:**
- Consumidor de los topics de Redpanda que escribe los eventos crudos como archivos Parquet en MinIO, organizados así: `lake/bronze/<entidad>/dt=<YYYY-MM-DD>/archivo.parquet` (capa bronze = dato crudo, sin transformar).
- Proceso (script Python + DuckDB) que lee la capa bronze y construye las tablas del esquema estrella de arriba, escribiéndolas como Parquet en `lake/gold/`.
- Query de validación con DuckDB, por ejemplo:
```sql
SELECT dp.categoria, SUM(fv.total_linea) as ventas_totales
FROM read_parquet('lake/gold/fact_ventas/*.parquet') fv
JOIN read_parquet('lake/gold/dim_producto/*.parquet') dp
  ON fv.producto_id = dp.producto_id
GROUP BY dp.categoria
ORDER BY ventas_totales DESC;
```

**Prompt sugerido para tu LLM:**
> "Tengo eventos JSON llegando a topics de Kafka/Redpanda con este formato [pegar formato de la Fase 3]. Quiero un script Python que consuma esos eventos, los escriba como Parquet particionado por fecha en MinIO (capa bronze), y después otro script que lea esos Parquet con DuckDB y construya este esquema estrella [pegar el esquema de arriba] como nuevos archivos Parquet (capa gold). Ayudame con el código de lectura/escritura, no con el diseño del esquema, eso ya lo definí."

**Punto de decisión — ADR-003:** granularidad de la capa bronze — ¿guardar el evento crudo exactamente como llega (más trazable, pero necesitás más transformación después) o aplicar ya alguna limpieza mínima al escribirlo (más cómodo en la Fase 5-6, pero perdés la versión "cruda" original del dato)?

**Checklist de verificación:**
- [ ] Existen archivos Parquet en `lake/bronze/` para las 3 entidades.
- [ ] Existen las 4 tablas del esquema estrella en `lake/gold/`.
- [ ] La query de validación de arriba (o una equivalente) devuelve resultados coherentes con los datos que creaste en las fases anteriores.
- [ ] El número total de ventas en `fact_ventas` coincide con el número de filas en `ventas_items` de la base operacional.
- [ ] Existe `decisiones/ADR-003-granularidad-bronze.md`.

**Entregable:** lakehouse con capas bronze y gold pobladas, modelo estrella consultable con DuckDB.

---

## FASE 5 — Data Warehouse de servicio y BI

**Rol: Ingeniero de Datos (serving layer) / BI Analyst.** Herramientas de BI como Metabase están pensadas para conectarse a una base de datos relacional tradicional, no directamente a archivos Parquet — por eso en empresas reales suele existir una capa de "servicio" entre el lake y el dashboard.

**Punto de decisión — ADR-004 (decidilo primero, antes de construir):** ¿materializar el esquema estrella del gold en una base Postgres nueva llamada `dwh` (más simple de conectar con Metabase, un paso extra de sincronización) o conectar Metabase directo a los Parquet vía su driver comunitario de DuckDB (menos piezas, pero el driver es menos estable y puede darte más trabajo de configuración que de aprendizaje real)?
*(Recomendación: si es tu primera vez con BI, elegí materializar a Postgres — vas a aprender lo mismo sobre el concepto de "serving layer" con menos fricción de herramienta.)*

**Qué tenés que construir (si elegiste materializar a Postgres):**
- Base Postgres nueva `dwh_db` con las mismas 4 tablas del esquema estrella de la Fase 4.
- Script que lee los Parquet de `lake/gold/` y hace el `INSERT`/`UPSERT` en `dwh_db`.
- Metabase en Docker Compose, conectado a `dwh_db`.
- 2-3 dashboards — no más. Cada dashboard debe tener como título la pregunta de negocio que responde, por ejemplo: "¿Qué categoría de producto genera más ingresos?", "¿Cuál es el ticket promedio por semana?".

**Prompt sugerido para tu LLM:**
> "Tengo estas 4 tablas de un esquema estrella en archivos Parquet [pegar esquema]. Quiero un script Python que las lea con DuckDB y las cargue en una base Postgres nueva, tabla por tabla, reemplazando el contenido cada vez que corre. Dame el script y explicame la diferencia entre hacer INSERT simple vs UPSERT para este caso."

**Checklist de verificación:**
- [ ] `dwh_db` tiene las 4 tablas pobladas con datos reales (no de ejemplo).
- [ ] Metabase se conecta sin error a `dwh_db` y el "data browser" muestra las 4 tablas.
- [ ] Existen 2-3 dashboards, cada uno con un título que es una pregunta de negocio y al menos un gráfico que la responde.
- [ ] Existe `decisiones/ADR-004-serving-layer.md`.

**Entregable:** `dwh_db` poblada + 2-3 dashboards funcionales en Metabase.

---

## FASE 6 — Caso de uso de Data Science

**Rol: Data Scientist.** La idea clave de esta fase: no armás infraestructura nueva, reutilizás la que ya existe. Un data scientist real rara vez monta su propio pipeline de datos desde cero — se conecta a lo que el equipo de datos ya construyó.

**Qué tenés que diseñar — elegí uno de estos dos casos de uso (documentalo en un ADR):**

**Opción A — Segmentación RFM (más simple, recomendada si es tu primera vez):**
Por cada usuario, calculás 3 métricas a partir de `fact_ventas`:
- **Recency**: días desde la última compra.
- **Frequency**: cantidad de compras en el período.
- **Monetary**: total gastado en el período.
Con esas 3 columnas, aplicás un clustering simple (K-Means, por ejemplo 3-4 clusters) para agrupar usuarios en segmentos tipo "clientes frecuentes de alto valor", "clientes ocasionales", "clientes en riesgo de abandono".

**Opción B — Predicción de recompra (más ambiciosa):**
Modelo de clasificación binaria: ¿este usuario va a comprar de nuevo en los próximos N días, dado su historial? Requiere definir una ventana de tiempo para "entrenamiento" y otra para "validación" — es más realista pero más trabajo de preparación de datos.

**Qué tenés que construir:**
- Notebook Jupyter que se conecta directo a `lake/gold/` (vía DuckDB) o a `dwh_db` (vía Postgres) — tu elección.
- Primera celda del notebook: 2-3 líneas explicando qué pregunta de negocio responde.
- Cálculo de las features (RFM u otras según la opción elegida).
- Modelo entrenado (`scikit-learn`) + al menos una métrica de evaluación reportada (para RFM: silhouette score del clustering; para clasificación: accuracy o AUC).
- Una celda final que interprete el resultado en lenguaje de negocio, no solo en números.

**Prompt sugerido para tu LLM:**
> "Quiero hacer segmentación RFM de clientes de un e-commerce, a partir de una tabla `fact_ventas` con columnas [pegar columnas]. Ayudame con el código en pandas para calcular Recency, Frequency y Monetary por usuario, y después aplicar K-Means con scikit-learn. Explicame cómo elegir el número de clusters con el método del codo o silhouette score."

**Checklist de verificación:**
- [ ] El notebook corre de punta a punta (`Run All`) sin errores.
- [ ] Reporta al menos una métrica de evaluación del modelo.
- [ ] La celda final interpreta el resultado en términos de negocio (ej. "el segmento 2 representa el 15% de los usuarios pero el 40% de los ingresos").
- [ ] Existe `decisiones/ADR-005-caso-uso-ds.md`.

**Entregable:** notebook reproducible con el caso de uso elegido.

---

## FASE 7 — Agente operativo interno

**Rol: Ingeniero de IA / Agentes.** Esta pieza demuestra que todo lo anterior sirve para algo: el agente no genera valor por sí solo, se apoya en el DWH, en el modelo analítico y en las métricas que ya definiste en la Fase 5.

**Qué tenés que diseñar:**
- Qué preguntas de negocio responde el resumen diario (reutilizá las mismas 2-3 métricas de tus dashboards de BI).
- Formato de salida: markdown, con secciones fijas, por ejemplo:
```
# Resumen ejecutivo — 2026-09-24

## Ventas
- Total del día: $X
- Comparado con ayer: +Y%

## Producto destacado
- Más vendido: <nombre>, <cantidad> unidades

## Alerta
- <texto generado solo si hay una anomalía, ej. caída >20% vs promedio semanal>
```

**Qué tenés que construir:**
- Ollama en Docker Compose con un modelo liviano (`llama3.2:1b` o `phi3`).
- Script Python que:
  1. Consulta `dwh_db` (SQL directo, no vía LLM — los números los calculás vos, el LLM solo redacta) para obtener las métricas del día y del período de comparación.
  2. Arma un prompt con esos números ya calculados y se lo pasa al modelo local para que redacte el resumen en lenguaje natural.
  3. Guarda el resultado en `agente/resumenes/resumen_<fecha>.md`.

**Prompt sugerido para tu LLM (para ayudarte a construir el agente, no confundir con el prompt que el agente usa internamente):**
> "Quiero un script Python que calcule estas métricas de negocio con SQL sobre Postgres [pegar tus queries], y después use Ollama (modelo local) para redactar un resumen ejecutivo en markdown a partir de esos números ya calculados. Ayudame con la integración a la API de Ollama y con la plantilla de prompt para que la redacción sea consistente cada vez."

**Checklist de verificación:**
- [ ] Ejecutar el script produce un archivo markdown con datos reales (verificables contra tus dashboards de la Fase 5, no inventados por el modelo).
- [ ] El modelo corre en CPU local, sin llamadas a APIs externas de pago (verificable revisando que no hay llamadas salientes a `api.openai.com` ni similares en el código).
- [ ] Existen al menos 3 resúmenes generados en fechas distintas.

**Entregable:** agente funcional + 3 resúmenes de ejemplo.

---

## FASE 8 — Cierre: retrospectiva de dirección

**Rol: CTO / CDO.** Cerrás el círculo mirando tus propias decisiones con la distancia de quien dirige, no de quien programó cada línea.

**Qué tenés que construir:**
`decisiones/retrospectiva.md`, releyendo los ADRs de las fases 0, 1, 3, 4/5 y 6, respondiendo:
- ¿Qué decisión, con el sistema completo funcionando, volverías a tomar tal cual?
- ¿Cuál cambiarías, y por qué?
- ¿Qué decisión temprana te costó más de lo esperado en una fase posterior? Sé específico: ¿en qué fase exacta sentiste el costo, y qué tuviste que hacer distinto por eso?

**Checklist de verificación:**
- [ ] El documento referencia explícitamente al menos 3 ADRs anteriores por su número.
- [ ] Identifica al menos una consecuencia concreta y verificable (no hipotética) que una decisión temprana tuvo en una fase posterior.

**Entregable:** `decisiones/retrospectiva.md`.

---

## Anexo — Checklist rápido de arranque de cada fase

Antes de empezar cualquier fase, verificá:
1. `docker compose ps` — todo lo de la fase anterior sigue `healthy`.
2. El checklist de la fase anterior está 100% marcado.
3. Leíste completo "qué tenés que diseñar" antes de escribirle nada a tu LLM — la parte de diseño es tuya, no se la delegás.
