# ADR-000: microservicios reales desde el inicio

## Contexto y alternativas consideradas

El ejercicio plantea dos alternativas para la arquitectura inicial:

1. **Monolito modular que posteriormente se separa en microservicios.** Su ventaja es que permite arrancar de forma más rápida y sencilla. Se descarta porque, para continuar con las fases siguientes, habría que realizar posteriormente la separación de los servicios.
2. **Microservicios reales desde el inicio.** Supone mayor complejidad inicial, pero es coherente con las fases posteriores del ejercicio.

## Decisión

Se elige implementar desde el inicio tres microservicios separados: Usuarios, Productos y Ventas. Cada servicio tendrá responsabilidades y una base de datos propias.

## Motivo de la elección

La alternativa elegida es coherente con las fases posteriores y permite trabajar desde el principio con separación real de servicios, comunicación entre ellos y bases de datos independientes. Se acepta la mayor complejidad inicial porque forma parte del objetivo de aprendizaje.
