# Peer Tutoring · Entrega final

Proyecto académico de Oscar Sebastian Pinchao Hidalgo, Bases de Datos, Yachay Tech.

Aplicación Flask + Flask-SQLAlchemy con ocho tablas, API JSON, interfaz web y dos reportes. La versión final del 21 de noviembre de 2026 funciona con **PostgreSQL 17.12 en Docker** y conserva SQLite como alternativa local.

## Inicio recomendado para presentar el proyecto

1. Abrir Docker Desktop y esperar a que el motor esté listo.
2. Abrir `INICIAR_DOCKER.bat` desde la carpeta del proyecto.
3. Entrar en http://127.0.0.1:5055.

La primera ejecución construye la aplicación y descarga las imágenes. Los datos ficticios se cargan una sola vez. Las siguientes ejecuciones conservan los registros en el volumen `peer_data`.

**Evidencia actual:** 19 pruebas aprobadas en PostgreSQL y 19 en SQLite; reportes medidos con 10 000 sesiones y 10 000 evaluaciones; copia PostgreSQL restaurada y comparada campo por campo. Ver `docs/VALIDACION_FINAL.md` y el PDF `docs/Peer_Tutoring_Proyecto_Final.pdf`.

Repositorio privado: https://github.com/CbazZzzzZ/peer-tutoring

## Alternativa SQLite en Windows

1. Descomprimir el proyecto en una carpeta propia. Tener Python 3.12 o superior instalado (con el lanzador `py`).
2. Abrir `INICIAR.bat`. La primera ejecución instala las dependencias y requiere Internet.
3. Abrir http://127.0.0.1:5055. Mantener abierta la ventana del servidor.
4. Para detenerlo, presionar Ctrl+C en esa ventana. Los registros se conservan en `instance/peer_tutoring.db`.

En el equipo donde se preparó la entrega también existe `INICIAR_EN_ESTE_EQUIPO.ps1`, que aprovecha las dependencias locales ya descargadas. El proyecto empaquetado no depende de esa instalación específica.

Inicio manual:

```powershell
py -3 -m venv .venv-local
.venv-local\Scripts\python.exe -m pip install -r requirements.txt
.venv-local\Scripts\python.exe manage.py init
.venv-local\Scripts\python.exe manage.py seed
.venv-local\Scripts\python.exe run.py
```

La carga inicial es idempotente: si existen estudiantes, no los reemplaza. Incluye personas ficticias, cursos, dos tutores, disponibilidad para los siguientes 14 días, solicitudes, sesiones y evaluaciones. Las fechas se calculan al ejecutar la carga inicial. Si el proyecto se presenta semanas después, crear nuevos intervalos en Disponibilidad.

## Demostración de 5 a 7 minutos

1. **Inicio:** explicar los totales y la agenda. Identificar las ocho entidades en el diagrama del informe.
2. **Estudiantes:** crear un estudiante, editar su carrera y consultar el cambio. Intentar repetir un correo para demostrar el rechazo.
3. **Tutores y habilitaciones:** mostrar que un tutor corresponde a un estudiante y está habilitado para cursos determinados.
4. **Disponibilidad:** verificar un intervalo futuro del tutor. Los formularios de fecha usan la zona local del navegador; las listas se presentan en horario de Ecuador.
5. **Solicitudes:** crear una solicitud del estudiante para un curso habilitado. **Sesiones:** programarla dentro del horario disponible, con inicio anterior a fin. Comprobar que la solicitud pasa a asignada.
6. Crear otra solicitud e intentar reservar el mismo tutor en el mismo intervalo. Mostrar el error y que no se insertó una sesión parcial. Una sesión futura no se puede completar.
7. **Evaluaciones:** mostrar las evaluaciones de las sesiones completadas incluidas en la demostración. Para demostrar creación sin esperar, programar una sesión con un intervalo pasado habilitado y disponible, completarla y evaluarla. El sistema admite registrar tutorías históricas.
8. **Reportes:** seleccionar un periodo que incluya los registros y mostrar demanda por curso y promedio por tutor. Explicar que “Sin evaluaciones” no significa cero.
9. Mostrar http://127.0.0.1:5055/docs y los resultados de pruebas en `docs/resultado_pruebas.txt`.

## API y documentación

- Página legible: `/docs`.
- OpenAPI 3.0 importable en Postman: `/openapi.json` y `docs/openapi.json`.
- Recursos: `/api/v1/estudiantes`, `/tutores`, `/cursos`, `/calificaciones`, `/disponibilidades`, `/solicitudes`, `/sesiones`, `/retroalimentaciones` (todos bajo `/api/v1`).
- GET lista, POST crea; GET/PATCH/DELETE sobre `/{id}`. Habilitaciones: `/{id_tutor}/{codigo_curso}`.
- Listas: `page`, `per_page` (máximo 100), `q`. Filtros por columnas; sesiones agrega `id_estudiante` y `codigo_curso`.
- Reportes GET `/api/v1/reportes/demanda` y `/api/v1/reportes/desempeno`, con `desde` y `hasta` ISO 8601 con zona. Periodo [desde, hasta).
- HTTP 400: entrada inválida; 404: referencia inexistente; 409: duplicado, dependencia o regla de negocio. Los errores incluyen `error.codigo` y `error.mensaje`.

## Reglas implementadas

- Un tutor es un estudiante único, sin duplicar sus datos personales. No hay autotutoría.
- Una solicitud tiene como máximo una sesión. El tutor debe estar certificado para el curso en la fecha de la sesión.
- La sesión programada debe caber en una disponibilidad. Se rechazan cruces de una persona, incluso entre sus dos roles. Se admiten intervalos contiguos.
- Programar asigna la solicitud; completar la cierra; cancelar la cancela. Eliminar una sesión programada devuelve la solicitud a pendiente. Los estados terminales se conservan.
- Una sesión no puede completarse antes de su fin. Solo se evalúan sesiones completadas, una vez, con puntuación 1 a 5.
- Las FK bloquean eliminaciones con dependencias. Se rechazan cambios de disponibilidad o habilitación que invaliden una sesión.
- SQLite activa FK y usa BEGIN IMMEDIATE en escrituras. PostgreSQL se configura con SERIALIZABLE y reintentos por conflicto. Todas las operaciones confirman o revierten sus cambios juntas.

El validador revisa la agenda completa para favorecer claridad y consistencia en el prototipo. No se afirma que esté optimizado para grandes despliegues. El promedio académico usa la escala propuesta 0 a 10.

## Pruebas

```powershell
.venv-local\Scripts\python.exe -m pytest tests -v
```

Las pruebas crean bases SQLite temporales; no borran la base de demostración. Para PostgreSQL, usar una base separada llamada exactamente `peer_tutoring_test` y definir TEST_DATABASE_URL. El informe de ejecución indica el motor realmente probado.

## PostgreSQL en Docker (inicio manual)

```powershell
docker compose up -d --build
docker compose exec web python manage.py seed
```

Abrir http://127.0.0.1:5055. Detener primero el servidor local si ocupa el puerto. PostgreSQL no expone un puerto al equipo; solo la web se vincula a 127.0.0.1. Los datos se guardan en el volumen `peer_data`. `docker compose down` detiene los servicios conservando el volumen. No añadir `-v` si se quieren conservar los datos.

## Archivos y entrega

- `app/models.py`: modelo relacional de ocho tablas.
- `app/service.py`: validaciones, estados y reglas de negocio.
- `app/__init__.py`: endpoints, reportes y contrato OpenAPI.
- `app/templates` y `app/static`: GUI, formularios, tablas y reportes.
- `tests/test_api.py`: pruebas reproducibles de API e integridad.
- `manage.py`: creación, carga ficticia y exportación del esquema.
- `docs`: SQL, documentación API y evidencia de pruebas.

El repositorio excluye `.env`, bases de datos, entornos y dependencias descargadas. El PDF final integra el diseño conceptual y lógico, la implementación y la evidencia actual. Los resultados de interfaz del 10 de noviembre se conservan con su fecha original; las capturas 07 a 09 corresponden a la revisión final del 21 de noviembre.

## Alcance y límites

Prototipo local para un operador académico, sin autenticación ni cuentas de estudiantes. Usar datos ficticios y no exponerlo a Internet. Las pruebas no acreditan validación institucional. La contraseña de Docker es de demostración; la configuración permite reemplazarla mediante `.env`.

Se utilizó asistencia de IA para el código, documentación y pruebas. El integrante debe comprender y revisar el proyecto antes de presentarlo.

## Material para la defensa

- `docs/Peer_Tutoring_Proyecto_Final.pdf`: informe final de 18 páginas.
- `docs/Peer_Tutoring_Guion_Detallado.pdf`: explicación por página, construcción, código, demostración y preguntas.
- `docs/VALIDACION_FINAL.md`: evidencia del 21/11/2026.
- `docs/junit_postgresql_final.xml` y `docs/junit_sqlite_final.xml`: 19 escenarios por motor.
- `docs/validacion_gui_final.json`: comprobaciones de navegador, separadas de las pruebas de API.

Filtros de historial visibles: estudiante, tutor, curso, estado y periodo según recurso.
El botón Programar de una solicitud pendiente abre la sesión con esa solicitud seleccionada.
Los selectores excluyen tutores no habilitados para el curso y sesiones no evaluables.
Disponibilidad, cruces y conflictos simultáneos siempre se validan en la API al guardar.

La base local existente conserva las acciones ficticias de demostración. En una instalación nueva,
`seed` crea sus propias fechas relativas; los identificadores y conteos pueden diferir de las capturas.
