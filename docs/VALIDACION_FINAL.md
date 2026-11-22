# Validación final - 21/11/2026

19/19 escenarios aprobados en PostgreSQL y 19/19 en SQLite, sin fallos ni omisiones.
Resultados: junit_postgresql_final.xml y junit_sqlite_final.xml.
Se añadieron conservación de habilitación de sesiones canceladas y filtros combinados de historial.

Rendimiento: 10 000 sesiones y 10 000 evaluaciones, cinco muestras por reporte.
Todos los máximos menores a dos segundos. Archivos performance_*_final.json.
Se mide cliente Flask y JSON; no navegación por Internet ni carga multiusuario.

Respaldo: pg_dump custom, pg_restore sobre peer_tutoring_restore; ocho tablas idénticas
campo por campo y cero restricciones sin validar. Ver backup_postgresql_final.json.

GUI: comprobaciones interactivas de filtros, programación, edición, rechazo de cierre futuro,
cierre pasado, evaluación, reportes y vista móvil. Ver validacion_gui_final.json y capturas 07-09.

Los diagramas y el diccionario conservan las ocho tablas; no se requiere migración del esquema.
Las relaciones se identifican como R1-R9 y la normalización se justifica bajo las dependencias indicadas.

Alcance: aplicación local de operador, sin autenticación institucional ni cuentas por rol.
La publicación GitHub conserva la configuración privada. La entrega a EVA y defensa son pasos humanos.
