from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint, Index

db = SQLAlchemy()

def now():
    return datetime.now(timezone.utc)

class Estudiante(db.Model):
    __tablename__ = 'estudiante'
    id_estudiante = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(254), nullable=False, unique=True)
    carrera = db.Column(db.String(120), nullable=False)
    anio_ingreso = db.Column(db.SmallInteger, nullable=False)
    __table_args__ = (CheckConstraint('anio_ingreso BETWEEN 2000 AND 2100'),
                      CheckConstraint('correo = lower(trim(correo))'),
                      CheckConstraint("trim(nombre) <> ''"))

class Tutor(db.Model):
    __tablename__ = 'tutor'
    id_tutor = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante', ondelete='RESTRICT'), nullable=False, unique=True)
    promedio = db.Column(db.Numeric(4,2), nullable=False)
    __table_args__ = (CheckConstraint('promedio BETWEEN 0 AND 10'),)

class Curso(db.Model):
    __tablename__ = 'curso'
    codigo_curso = db.Column(db.String(20), primary_key=True)
    nombre_curso = db.Column(db.String(120), nullable=False)
    departamento = db.Column(db.String(120), nullable=False)
    creditos = db.Column(db.SmallInteger, nullable=False)
    __table_args__ = (CheckConstraint('creditos > 0'),)

class Calificacion(db.Model):
    __tablename__ = 'calificacion'
    id_tutor = db.Column(db.Integer, db.ForeignKey('tutor.id_tutor', ondelete='RESTRICT'), primary_key=True)
    codigo_curso = db.Column(db.String(20), db.ForeignKey('curso.codigo_curso', ondelete='RESTRICT'), primary_key=True)
    fecha_certificacion = db.Column(db.Date, nullable=False)
    __table_args__ = (Index('idx_calificacion_curso', 'codigo_curso'),)

class Disponibilidad(db.Model):
    __tablename__ = 'disponibilidad'
    id_disponibilidad = db.Column(db.Integer, primary_key=True)
    id_tutor = db.Column(db.Integer, db.ForeignKey('tutor.id_tutor', ondelete='RESTRICT'), nullable=False)
    inicio = db.Column(db.DateTime(timezone=True), nullable=False)
    fin = db.Column(db.DateTime(timezone=True), nullable=False)
    __table_args__ = (CheckConstraint('fin > inicio'), UniqueConstraint('id_tutor','inicio','fin'), Index('idx_disponibilidad_tutor_inicio','id_tutor','inicio'))

class SolicitudTutoria(db.Model):
    __tablename__ = 'solicitud_tutoria'
    id_solicitud = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante', ondelete='RESTRICT'), nullable=False)
    codigo_curso = db.Column(db.String(20), db.ForeignKey('curso.codigo_curso', ondelete='RESTRICT'), nullable=False)
    fecha_solicitud = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    tema = db.Column(db.String(250), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default='pendiente')
    __table_args__ = (CheckConstraint("estado IN ('pendiente','asignada','cerrada','cancelada')"), Index('idx_solicitud_curso_fecha','codigo_curso','fecha_solicitud'), Index('idx_solicitud_estudiante','id_estudiante'))

class SesionTutoria(db.Model):
    __tablename__ = 'sesion_tutoria'
    id_sesion = db.Column(db.Integer, primary_key=True)
    id_solicitud = db.Column(db.Integer, db.ForeignKey('solicitud_tutoria.id_solicitud', ondelete='RESTRICT'), nullable=False, unique=True)
    id_tutor = db.Column(db.Integer, db.ForeignKey('tutor.id_tutor', ondelete='RESTRICT'), nullable=False)
    inicio = db.Column(db.DateTime(timezone=True), nullable=False)
    fin = db.Column(db.DateTime(timezone=True), nullable=False)
    lugar = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default='programada')
    __table_args__ = (CheckConstraint('fin > inicio'), CheckConstraint("estado IN ('programada','completada','cancelada')"), Index('idx_sesion_tutor_inicio','id_tutor','inicio'), Index('idx_sesion_inicio','inicio'))

class Retroalimentacion(db.Model):
    __tablename__ = 'retroalimentacion'
    id_feedback = db.Column(db.Integer, primary_key=True)
    id_sesion = db.Column(db.Integer, db.ForeignKey('sesion_tutoria.id_sesion', ondelete='RESTRICT'), nullable=False, unique=True)
    calificacion = db.Column(db.SmallInteger, nullable=False)
    comentarios = db.Column(db.Text)
    fecha = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (CheckConstraint('calificacion BETWEEN 1 AND 5'),)

RESOURCES = {'estudiantes': Estudiante, 'tutores': Tutor, 'cursos': Curso,
             'calificaciones': Calificacion, 'disponibilidades': Disponibilidad,
             'solicitudes': SolicitudTutoria, 'sesiones': SesionTutoria,
             'retroalimentaciones': Retroalimentacion}
