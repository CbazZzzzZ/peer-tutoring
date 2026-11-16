# Validación del avance del 16 de noviembre de 2026

## Base de datos, API y concurrencia

- PostgreSQL 17.12, Python 3.12.16, SQLAlchemy 2.0.46, Flask-SQLAlchemy 3.1.1, Flask 3.1.3, pytest 8.4.2, ejecutados en Docker.
- 17 pruebas aprobadas, sin errores ni omisiones, en 7,771 segundos. Evidencia: `junit_postgresql.xml`.
- Misma suite en SQLite/Windows: 17 pruebas aprobadas en 7,91 segundos. Evidencia: `junit_sqlite.xml` y `resultado_sqlite.txt`.
- Prueba de dos reservas simultáneas: solo una se confirma; la otra devuelve 409. La solicitud y la sesión quedan consistentes.
- Fallo controlado antes del commit: no persiste la sesión y la solicitud permanece pendiente.

## Rendimiento

Datos sintéticos aislados: 10 000 sesiones completadas y 10 000 evaluaciones. Cinco mediciones por reporte mediante el cliente de pruebas Flask, incluyendo respuesta JSON.

| Motor | Reporte | Promedio | Máximo |
|---|---|---:|---:|
| PostgreSQL | Demanda | 0,0049 s | 0,0074 s |
| PostgreSQL | Desempeño | 0,0182 s | 0,0254 s |
| SQLite | Demanda | 0,0021 s | 0,0031 s |
| SQLite | Desempeño | 0,0081 s | 0,0105 s |

Los resultados verificaron 5 000 solicitudes por curso y promedio 4,00. Se cumplió la meta local de dos segundos. No es una prueba de carga multiusuario ni una garantía de latencia en otro equipo. Evidencia: `performance_postgresql.json` y `performance_sqlite.json`.

## Respaldo PostgreSQL

Se ejecutó pg_dump en formato custom, se restauró mediante pg_restore en una base separada y se compararon todas las filas y columnas de las ocho tablas. Valores idénticos; cero restricciones sin validar. Evidencia: `backup_postgresql.json`.

## Interfaz

El 10 de noviembre se aprobaron 18 comprobaciones de navegador sobre SQLite: CRUD, persistencia, errores, pantallas, reportes, solicitud/programación y ancho móvil. Los resultados conservan su fecha original. El 16 de noviembre se inspeccionó el inicio y los reportes con PostgreSQL; capturas `05_postgresql_inicio.jpg` y `06_postgresql_reportes.jpg`.

## Alcance del avance

Se entrega una aplicación de operador local con las ocho entidades, CRUD, reportes e integración GUI/API. No incluye autenticación multiusuario ni integración institucional, fuera del alcance del prototipo. La publicación del repositorio debe comprobarse en GitHub; los documentos no sustituyen esa comprobación.
