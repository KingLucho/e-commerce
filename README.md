# E-commerce — ejercicio integrador

Proyecto local de e-commerce desarrollado por fases con microservicios independientes y bases de datos PostgreSQL propias.

## Estado actual

La Fase 0 configura el esqueleto de Usuarios, Productos y Ventas, sus bases de datos y healthchecks. Las APIs actuales son placeholders: solo exponen `GET /health`; los endpoints de negocio se implementarán en la Fase 1.

## Arranque local

Cada servicio necesita su propio `.env`. Los archivos `.env.example` son plantillas sin credenciales reales:

```powershell
Copy-Item servicios/usuarios/.env.example servicios/usuarios/.env
Copy-Item servicios/productos/.env.example servicios/productos/.env
Copy-Item servicios/ventas/.env.example servicios/ventas/.env
```

Reemplaza los valores de ejemplo de las credenciales antes de iniciar el entorno. En cada archivo `.env`, la contraseña incluida en `DATABASE_URL` debe coincidir con `POSTGRES_PASSWORD` del mismo servicio. Después ejecuta:

```powershell
docker compose up --build -d
docker compose ps
```

Las APIs quedan disponibles en `http://localhost:8001`, `http://localhost:8002` y `http://localhost:8003`. Cada una responde en `/health`. PostgreSQL se publica en los puertos `5433`, `5434` y `5435`, respectivamente.

## Documentación

- [Contratos API](docs/contratos-api.md)
- [Arquitectura de Fase 0](docs/arquitectura.md)
- [ADR-000: arquitectura](decisiones/ADR-000-arquitectura.md)
- [Enunciado del ejercicio](ejercicio_integrador_v2.md)
