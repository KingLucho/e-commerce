# Arquitectura — Fase 0

El diagrama refleja únicamente los componentes implementados en esta fase. Cada microservicio tiene una base PostgreSQL independiente. Los seis contenedores comparten la red Docker `ecommerce_net`.

```mermaid
flowchart LR
  subgraph net[Red Docker: ecommerce_net]
    U[API Usuarios<br/>HTTP :8080]
    UD[(PostgreSQL Usuarios<br/>usuarios_db :5432)]
    P[API Productos<br/>HTTP :8080]
    PD[(PostgreSQL Productos<br/>productos_db :5432)]
    V[API Ventas<br/>HTTP :8080]
    VD[(PostgreSQL Ventas<br/>ventas_db :5432)]
    U --- UD
    P --- PD
    V --- VD
  end

  C[Cliente local] -->|localhost:8001| U
  C -->|localhost:8002| P
  C -->|localhost:8003| V
  D[Herramienta SQL local] -->|localhost:5433| UD
  D -->|localhost:5434| PD
  D -->|localhost:5435| VD
```

En Fase 0 las APIs son placeholders con una ruta HTTP `/health`. Las líneas entre cada API y PostgreSQL del diagrama representan relaciones previstas de la arquitectura; los placeholders todavía no establecen conexiones con las bases de datos. Esa conexión se implementará al desarrollar la lógica de negocio.

## Alcance de usuarios PostgreSQL

El ejercicio exige una base de datos PostgreSQL independiente por servicio y la configuración mediante archivos `.env`, pero no exige usuarios PostgreSQL administrativos separados, roles adicionales ni una configuración de privilegios mínimos. En Fase 0 se mantienen `usuarios_app`, `productos_app` y `ventas_app` tal como están configurados, sin añadir permisos o roles adicionales.
