import re
from collections import defaultdict
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from .models import *

class Problem(Exception):
    def __init__(self, message, status=400, code='DATOS_INVALIDOS'):
        self.message, self.status, self.code = message, status, code

def conflict(message, code='REGLA_NEGOCIO'):
    raise Problem(message,409,code)

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def serialize(obj):
    result = {}
    for c in obj.__table__.columns:
        v = getattr(obj,c.name)
        if isinstance(v,datetime): v = utc(v).isoformat()
        elif isinstance(v,date): v = v.isoformat()
        elif isinstance(v,Decimal): v = float(v)
        result[c.name] = v
    return result

def get(model, key):
    obj = db.session.get(model,key)
    if obj is None: raise Problem('El registro no existe.',404,'NO_ENCONTRADO')
    return obj

def parse_datetime(value):
    try:
        v = datetime.fromisoformat(value.replace('Z','+00:00'))
        if v.tzinfo is None: raise ValueError()
        return v.astimezone(timezone.utc)
    except (ValueError,TypeError,AttributeError):
        raise Problem('Use una fecha ISO 8601 con zona horaria.')

def clean(model, payload, create):
    if not isinstance(payload,dict) or not payload: raise Problem('Envíe un objeto JSON con campos.')
    from sqlalchemy import Integer, Numeric, DateTime, Date, String
    columns = {c.name:c for c in model.__table__.columns}
    readonly = {'fecha_solicitud','fecha'}
    readonly |= {c.name for c in model.__table__.primary_key if c.type.python_type is int and len(model.__table__.primary_key)==1}
    if not create: readonly |= {c.name for c in model.__table__.primary_key}
    if set(payload)-set(columns): raise Problem('Campo desconocido: '+', '.join(sorted(set(payload)-set(columns))))
    if set(payload)&readonly: raise Problem('Campo de solo lectura: '+', '.join(sorted(set(payload)&readonly)))
    data={}
    for key,value in payload.items():
        c=columns[key]
        if value is None:
            if not c.nullable: raise Problem(f'{key} es obligatorio.')
            data[key]=None;continue
        try:
            if isinstance(c.type,Integer):
                if type(value) is not int: raise ValueError()
                v=value
                if not -2147483648 <= v <= 2147483647: raise ValueError()
            elif isinstance(c.type,Numeric):
                if isinstance(value,bool): raise ValueError()
                v=Decimal(str(value))
                if not v.is_finite() or v.as_tuple().exponent < -2: raise ValueError()
            elif isinstance(c.type,DateTime): v=parse_datetime(value)
            elif isinstance(c.type,Date): v=date.fromisoformat(value)
            else:
                if not isinstance(value,str): raise ValueError()
                v=value.strip()
                if not v and not c.nullable: raise ValueError()
                if getattr(c.type,'length',None) and len(v)>c.type.length: raise ValueError()
                if key=='comentarios' and len(v)>5000: raise ValueError()
            data[key]=v
        except (ValueError,TypeError,InvalidOperation): raise Problem(f'Valor inválido para {key}.')
    if create:
        for key,c in columns.items():
            if key not in readonly and not c.nullable and c.default is None and key not in data:
                raise Problem(f'Falta el campo {key}.')
    if 'correo' in data:
        data['correo']=data['correo'].lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['correo']): raise Problem('Correo inválido.')
    ranges={'anio_ingreso':(2000,2100),'creditos':(1,32767),'promedio':(0,10),'calificacion':(1,5)}
    for key,(lo,hi) in ranges.items():
        if key in data and not lo<=data[key]<=hi: raise Problem(f'{key} debe estar entre {lo} y {hi}.')
    if 'estado' in data:
        allowed={'solicitud_tutoria':['pendiente','asignada','cerrada','cancelada'],'sesion_tutoria':['programada','completada','cancelada']}
        if data['estado'] not in allowed.get(model.__tablename__,[]): raise Problem('Estado inválido.')
    for key,value in data.items():
        for fk in columns[key].foreign_keys:
            target=next(m for m in RESOURCES.values() if m.__tablename__==fk.column.table.name)
            get(target,value)
    return data

def mutate(resource,key,payload,method):
    model=RESOURCES[resource]
    obj=None if method=='POST' else get(model,key)
    if method=='DELETE':
        if isinstance(obj,SesionTutoria):
            if obj.estado!='programada': conflict('Se conserva el historial de sesiones terminadas.')
            get(SolicitudTutoria,obj.id_solicitud).estado='pendiente'
        if isinstance(obj,SolicitudTutoria) and obj.estado not in ['pendiente','cancelada']:
            conflict('La solicitud tiene historial; no puede eliminarse.')
        db.session.delete(obj)
        db.session.flush()
        validate_all()
        return None
    data=clean(model,payload,method=='POST')
    if obj is not None:
        if isinstance(obj,Tutor) and 'id_estudiante' in data and data['id_estudiante']!=obj.id_estudiante:
            conflict('La identidad del tutor no se modifica; cree otro perfil.')
        if isinstance(obj,Retroalimentacion) and 'id_sesion' in data and data['id_sesion']!=obj.id_sesion:
            conflict('No se puede trasladar una evaluación a otra sesión.')
        if isinstance(obj,SolicitudTutoria):
            if obj.estado!='pendiente': conflict('Solo se pueden editar solicitudes pendientes.')
            if data.get('estado','pendiente') not in ['pendiente','cancelada']: conflict('El estado se actualiza desde la sesión.')
        if isinstance(obj,SesionTutoria):
            if obj.estado!='programada': conflict('La sesión ya está completada o cancelada.')
            if 'id_solicitud' in data and data['id_solicitud']!=obj.id_solicitud: conflict('La solicitud de una sesión no se cambia.')
    else:
        if model is SolicitudTutoria and data.get('estado','pendiente')!='pendiente': conflict('Una solicitud nueva debe estar pendiente.')
        if model is SesionTutoria:
            if data.get('estado','programada')!='programada': conflict('Una sesión nueva debe estar programada.')
            if get(SolicitudTutoria,data['id_solicitud']).estado!='pendiente': conflict('La solicitud no está pendiente.')
        obj=model();db.session.add(obj)
    for k,v in data.items():setattr(obj,k,v)
    if isinstance(obj,(SesionTutoria,Disponibilidad)) and utc(obj.fin)<=utc(obj.inicio):
        raise Problem('La hora final debe ser posterior al inicio.')
    if isinstance(obj,SesionTutoria):
        if obj.estado is None:obj.estado='programada'
        get(SolicitudTutoria,obj.id_solicitud).estado={'programada':'asignada','completada':'cerrada','cancelada':'cancelada'}[obj.estado]
    db.session.flush()
    validate_all()
    return serialize(obj)

def validate_all():
    # Whole-schedule validation is deliberate for the small academic prototype.
    # All writes use SERIALIZABLE (PostgreSQL) or BEGIN IMMEDIATE (SQLite).
    sessions=db.session.scalars(select(SesionTutoria)).all()
    requests={r.id_solicitud:r for r in db.session.scalars(select(SolicitudTutoria)).all()}
    tutors={t.id_tutor:t for t in db.session.scalars(select(Tutor)).all()}
    cert={(c.id_tutor,c.codigo_curso):c.fecha_certificacion for c in db.session.scalars(select(Calificacion)).all()}
    available=defaultdict(list)
    for a in db.session.scalars(select(Disponibilidad)).all():available[a.id_tutor].append((utc(a.inicio),utc(a.fin)))
    occupied=defaultdict(list)
    sessionmap={s.id_sesion:s for s in sessions}
    for s in sessions:
        r=requests[s.id_solicitud]; tutor=tutors[s.id_tutor]
        expected={'programada':'asignada','completada':'cerrada','cancelada':'cancelada'}[s.estado]
        if r.estado!=expected:conflict('Estado de solicitud inconsistente.')
        if r.id_estudiante==tutor.id_estudiante:conflict('Un tutor no puede atenderse a sí mismo.','AUTOTUTORIA')
        start,end=utc(s.inicio),utc(s.fin)
        certified=cert.get((s.id_tutor,r.codigo_curso))
        if not certified or certified>start.astimezone(timezone(timedelta(hours=-5))).date():
            conflict('El tutor no está habilitado para ese curso en esa fecha.','TUTOR_NO_HABILITADO')
        # Cancelled sessions keep their certification history, but occupy no time.
        if s.estado=='cancelada':continue
        if s.estado=='programada' and not any(a<=start and end<=b for a,b in available[s.id_tutor]):
            conflict('La sesión no está dentro de la disponibilidad del tutor.','SIN_DISPONIBILIDAD')
        if s.estado=='completada' and end>now():conflict('La sesión todavía no ha finalizado.')
        for person in (r.id_estudiante,tutor.id_estudiante):occupied[person].append((start,end))
    for intervals in occupied.values():
        last=None
        for start,end in sorted(intervals):
            if last is not None and start<last:conflict('Una persona tiene una sesión superpuesta.','HORARIO_OCUPADO')
            last=end
    for f in db.session.scalars(select(Retroalimentacion)).all():
        s=sessionmap[f.id_sesion]
        if s.estado!='completada' or utc(s.fin)>now() or utc(f.fecha)<utc(s.fin):
            conflict('Solo se evalúan sesiones completadas después de su hora final.','SESION_NO_COMPLETADA')
