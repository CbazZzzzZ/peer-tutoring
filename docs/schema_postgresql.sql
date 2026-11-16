-- Esquema generado desde los modelos ORM: postgresql.
-- Validaciones cruzadas: app/service.py.


CREATE TABLE curso (
	codigo_curso VARCHAR(20) NOT NULL,
	nombre_curso VARCHAR(120) NOT NULL,
	departamento VARCHAR(120) NOT NULL,
	creditos SMALLINT NOT NULL,
	PRIMARY KEY (codigo_curso),
	CHECK (creditos > 0)
)

;

CREATE TABLE estudiante (
	id_estudiante SERIAL NOT NULL,
	nombre VARCHAR(120) NOT NULL,
	correo VARCHAR(254) NOT NULL,
	carrera VARCHAR(120) NOT NULL,
	anio_ingreso SMALLINT NOT NULL,
	PRIMARY KEY (id_estudiante),
	CHECK (anio_ingreso BETWEEN 2000 AND 2100),
	CHECK (correo = lower(trim(correo))),
	CHECK (trim(nombre) <> ''),
	UNIQUE (correo)
)

;

CREATE TABLE solicitud_tutoria (
	id_solicitud SERIAL NOT NULL,
	id_estudiante INTEGER NOT NULL,
	codigo_curso VARCHAR(20) NOT NULL,
	fecha_solicitud TIMESTAMP WITH TIME ZONE NOT NULL,
	tema VARCHAR(250) NOT NULL,
	estado VARCHAR(12) NOT NULL,
	PRIMARY KEY (id_solicitud),
	CHECK (estado IN ('pendiente','asignada','cerrada','cancelada')),
	FOREIGN KEY(id_estudiante) REFERENCES estudiante (id_estudiante) ON DELETE RESTRICT,
	FOREIGN KEY(codigo_curso) REFERENCES curso (codigo_curso) ON DELETE RESTRICT
)

;
CREATE INDEX idx_solicitud_curso_fecha ON solicitud_tutoria (codigo_curso, fecha_solicitud);
CREATE INDEX idx_solicitud_estudiante ON solicitud_tutoria (id_estudiante);

CREATE TABLE tutor (
	id_tutor SERIAL NOT NULL,
	id_estudiante INTEGER NOT NULL,
	promedio NUMERIC(4, 2) NOT NULL,
	PRIMARY KEY (id_tutor),
	CHECK (promedio BETWEEN 0 AND 10),
	UNIQUE (id_estudiante),
	FOREIGN KEY(id_estudiante) REFERENCES estudiante (id_estudiante) ON DELETE RESTRICT
)

;

CREATE TABLE calificacion (
	id_tutor INTEGER NOT NULL,
	codigo_curso VARCHAR(20) NOT NULL,
	fecha_certificacion DATE NOT NULL,
	PRIMARY KEY (id_tutor, codigo_curso),
	FOREIGN KEY(id_tutor) REFERENCES tutor (id_tutor) ON DELETE RESTRICT,
	FOREIGN KEY(codigo_curso) REFERENCES curso (codigo_curso) ON DELETE RESTRICT
)

;
CREATE INDEX idx_calificacion_curso ON calificacion (codigo_curso);

CREATE TABLE disponibilidad (
	id_disponibilidad SERIAL NOT NULL,
	id_tutor INTEGER NOT NULL,
	inicio TIMESTAMP WITH TIME ZONE NOT NULL,
	fin TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id_disponibilidad),
	CHECK (fin > inicio),
	UNIQUE (id_tutor, inicio, fin),
	FOREIGN KEY(id_tutor) REFERENCES tutor (id_tutor) ON DELETE RESTRICT
)

;
CREATE INDEX idx_disponibilidad_tutor_inicio ON disponibilidad (id_tutor, inicio);

CREATE TABLE sesion_tutoria (
	id_sesion SERIAL NOT NULL,
	id_solicitud INTEGER NOT NULL,
	id_tutor INTEGER NOT NULL,
	inicio TIMESTAMP WITH TIME ZONE NOT NULL,
	fin TIMESTAMP WITH TIME ZONE NOT NULL,
	lugar VARCHAR(200) NOT NULL,
	estado VARCHAR(12) NOT NULL,
	PRIMARY KEY (id_sesion),
	CHECK (fin > inicio),
	CHECK (estado IN ('programada','completada','cancelada')),
	UNIQUE (id_solicitud),
	FOREIGN KEY(id_solicitud) REFERENCES solicitud_tutoria (id_solicitud) ON DELETE RESTRICT,
	FOREIGN KEY(id_tutor) REFERENCES tutor (id_tutor) ON DELETE RESTRICT
)

;
CREATE INDEX idx_sesion_inicio ON sesion_tutoria (inicio);
CREATE INDEX idx_sesion_tutor_inicio ON sesion_tutoria (id_tutor, inicio);

CREATE TABLE retroalimentacion (
	id_feedback SERIAL NOT NULL,
	id_sesion INTEGER NOT NULL,
	calificacion SMALLINT NOT NULL,
	comentarios TEXT,
	fecha TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id_feedback),
	CHECK (calificacion BETWEEN 1 AND 5),
	UNIQUE (id_sesion),
	FOREIGN KEY(id_sesion) REFERENCES sesion_tutoria (id_sesion) ON DELETE RESTRICT
)

;
