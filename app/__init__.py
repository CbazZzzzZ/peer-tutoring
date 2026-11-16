import os
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from sqlalchemy import select, func, and_, or_, text, event
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from werkzeug.exceptions import HTTPException
from .models import *
from .service import Problem, mutate, serialize, get, parse_datetime

def create_app(config=None):
    app=Flask(__name__)
    uri=os.getenv('DATABASE_URL','sqlite:///peer_tutoring.db')
    app.config.update(SQLALCHEMY_DATABASE_URI=uri,SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=1024*1024)
    if config:app.config.update(config)
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS']={'isolation_level':'SERIALIZABLE','pool_pre_ping':True}
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name=='sqlite':
            @event.listens_for(db.engine,'connect')
            def configure(connection,record):
                connection.execute('PRAGMA foreign_keys=ON')
                connection.execute('PRAGMA busy_timeout=5000')

    @app.errorhandler(Problem)
    def handle_problem(e):return jsonify(error={'codigo':e.code,'mensaje':e.message}),e.status

    @app.errorhandler(HTTPException)
    def handle_http(e):return jsonify(error={'codigo':'HTTP_ERROR','mensaje':e.description}),e.code

    @app.get('/')
    def home():return render_template('index.html')

    @app.get('/health')
    def health():
        db.session.execute(text('SELECT 1'))
        return jsonify(status='ok',database=db.engine.dialect.name)

    @app.get('/api/v1/meta')
    def meta():return jsonify(metadata())

    def identify(resource,key):
        if resource not in RESOURCES:raise Problem('Recurso inexistente.',404,'NO_ENCONTRADO')
        model=RESOURCES[resource]
        if key is None:return model,None
        parts=key.split('/')
        cols=list(model.__table__.primary_key)
        if len(parts)!=len(cols):raise Problem('Identificador inválido.',404,'NO_ENCONTRADO')
        try:values=[c.type.python_type(v) for c,v in zip(cols,parts)]
        except (ValueError,TypeError):raise Problem('Identificador inválido.',404,'NO_ENCONTRADO')
        return model,tuple(values) if len(values)>1 else values[0]

    @app.route('/api/v1/<resource>',methods=['GET','POST'])
    @app.route('/api/v1/<resource>/<path:key>',methods=['GET','PATCH','DELETE'])
    def resource_route(resource,key=None):
        model,identity=identify(resource,key)
        if request.method=='GET':
            if identity is not None:return jsonify(serialize(get(model,identity)))
            return jsonify(list_records(model,resource))
        payload=request.get_json() if request.method!='DELETE' else None
        for attempt in range(3):
            try:
                if db.engine.dialect.name=='sqlite':db.session.execute(text('BEGIN IMMEDIATE'))
                result=mutate(resource,identity,payload,request.method)
                db.session.commit()
                if request.method=='DELETE':return '',204
                return jsonify(result),201 if request.method=='POST' else 200
            except IntegrityError:
                db.session.rollback()
                raise Problem('El registro está duplicado o tiene dependencias que impiden la operación.',409,'INTEGRIDAD')
            except DataError:
                db.session.rollback();raise Problem('Un valor no corresponde al tipo o rango permitido.')
            except OperationalError as e:
                db.session.rollback()
                state=getattr(e.orig,'sqlstate',None)
                if state in ('40001','40P01') or 'locked' in str(e).lower():
                    if attempt<2:time.sleep(.05*(attempt+1));continue
                    raise Problem('Otra operación modificó la agenda. Actualice e intente de nuevo.',409,'CONCURRENCIA')
                raise
            except Exception:
                db.session.rollback();raise

    @app.get('/api/v1/reportes/<kind>')
    def reports(kind):
        if kind not in ('demanda','desempeno'):raise Problem('Reporte inexistente.',404)
        start,end=period(required=True)
        if kind=='demanda':
            q=select(Curso.codigo_curso,Curso.nombre_curso,func.count(SolicitudTutoria.id_solicitud).label('solicitudes')).outerjoin(SolicitudTutoria,and_(SolicitudTutoria.codigo_curso==Curso.codigo_curso,SolicitudTutoria.fecha_solicitud>=start,SolicitudTutoria.fecha_solicitud<end)).group_by(Curso.codigo_curso,Curso.nombre_curso).order_by(func.count(SolicitudTutoria.id_solicitud).desc(),Curso.codigo_curso)
        else:
            q=select(Tutor.id_tutor,Estudiante.nombre,func.count(SesionTutoria.id_sesion).label('completadas'),func.count(Retroalimentacion.id_feedback).label('evaluadas'),func.avg(Retroalimentacion.calificacion).label('promedio')).join(Estudiante,Tutor.id_estudiante==Estudiante.id_estudiante).outerjoin(SesionTutoria,and_(SesionTutoria.id_tutor==Tutor.id_tutor,SesionTutoria.estado=='completada',SesionTutoria.fin>=start,SesionTutoria.fin<end)).outerjoin(Retroalimentacion,Retroalimentacion.id_sesion==SesionTutoria.id_sesion).group_by(Tutor.id_tutor,Estudiante.nombre).order_by(Tutor.id_tutor)
        rows=[dict(r) for r in db.session.execute(q).mappings()]
        for r in rows:
            if r.get('promedio') is not None:r['promedio']=round(float(r['promedio']),2)
        return jsonify(items=rows,desde=start.isoformat(),hasta=end.isoformat())

    @app.get('/api/v1/resumen')
    def summary():
        counts={k:db.session.scalar(select(func.count()).select_from(m)) for k,m in RESOURCES.items()}
        counts['pendientes']=db.session.scalar(select(func.count()).select_from(SolicitudTutoria).where(SolicitudTutoria.estado=='pendiente'))
        counts['programadas']=db.session.scalar(select(func.count()).select_from(SesionTutoria).where(SesionTutoria.estado=='programada'))
        return jsonify(counts)

    @app.get('/openapi.json')
    def openapi():return jsonify(api_spec())

    @app.get('/docs')
    def docs():return render_template('docs.html',resources=metadata())
    return app

def period(required=False):
    a,b=request.args.get('desde'),request.args.get('hasta')
    if not a and not b and not required:return None,None
    if not a or not b:raise Problem('Envíe desde y hasta juntos.')
    a,b=parse_datetime(a),parse_datetime(b)
    if a>=b:raise Problem('desde debe ser anterior a hasta.')
    return a,b

def list_records(model,resource):
    try:
        page=int(request.args.get('page',1));size=int(request.args.get('per_page',20))
        if page<1 or not 1<=size<=100:raise ValueError()
    except ValueError:raise Problem('page debe ser positivo y per_page estar entre 1 y 100.')
    stmt=select(model)
    allowed={'page','per_page','q','desde','hasta'}|set(model.__table__.columns.keys())
    if resource in ('sesiones','tutores'):allowed|={'codigo_curso','id_estudiante'}
    if set(request.args)-allowed:raise Problem('Filtro desconocido.')
    if resource=='sesiones':stmt=stmt.join(SolicitudTutoria,SesionTutoria.id_solicitud==SolicitudTutoria.id_solicitud)
    if resource=='tutores' and request.args.get('codigo_curso'):
        stmt=stmt.join(Calificacion,Tutor.id_tutor==Calificacion.id_tutor).where(Calificacion.codigo_curso==request.args['codigo_curso'])
    for k,v in request.args.items():
        if k in {'page','per_page','q','desde','hasta'}:continue
        if resource=='tutores' and k=='codigo_curso':continue
        target=SolicitudTutoria if resource=='sesiones' and k in ('id_estudiante','codigo_curso') else model
        col=getattr(target,k,None)
        if col is None:raise Problem('Filtro inválido.')
        try:
            value=int(v) if col.type.python_type is int else v
        except ValueError:raise Problem(f'Filtro inválido: {k}.')
        stmt=stmt.where(col==value)
    if request.args.get('q'):
        terms=[c.ilike('%'+request.args['q']+'%') for c in model.__table__.columns if isinstance(c.type,db.String)]
        if terms:stmt=stmt.where(or_(*terms))
    start,end=period()
    if start:
        field=getattr(model,'inicio',getattr(model,'fecha_solicitud',getattr(model,'fecha',None)))
        if field is None:raise Problem('Este recurso no tiene filtro temporal.')
        stmt=stmt.where(field>=start,field<end)
    count=db.session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt=stmt.order_by(*model.__table__.primary_key.columns).offset((page-1)*size).limit(size)
    return {'items':[serialize(x) for x in db.session.scalars(stmt)],'total':count,'page':page,'per_page':size}

def metadata():
    result={}
    for key,model in RESOURCES.items():
        fields=[]
        for c in model.__table__.columns:
            py=c.type.python_type
            kind='datetime' if py is datetime else 'date' if py.__name__=='date' else 'number' if py in (int, __import__('decimal').Decimal) else 'text'
            ref=None
            if c.foreign_keys:
                fk=next(iter(c.foreign_keys))
                ref=next(k for k,m in RESOURCES.items() if m.__tablename__==fk.column.table.name)
            auto=c.name in ('fecha','fecha_solicitud') or (c.primary_key and py is int and len(model.__table__.primary_key)==1)
            fields.append({'name':c.name,'type':kind,'required':not c.nullable,'pk':c.primary_key,'auto':auto,'reference':ref,'maxLength':getattr(c.type,'length',None),'default':c.default.arg if c.default and isinstance(c.default.arg,str) else None})
        result[key]={'fields':fields,'pk':[c.name for c in model.__table__.primary_key]}
    return result

def api_spec():
    paths={};schemas={}
    for key,meta in metadata().items():
        props={};writeprops={};required=[]
        for f in meta['fields']:
            t={'number':'number','text':'string','date':'string','datetime':'string'}[f['type']]
            if f['name'].startswith('id_') or f['name'] in ('creditos','anio_ingreso','calificacion'):t='integer'
            spec={'type':t}
            if f['type'] in ('datetime','date'):spec['format']='date-time' if f['type']=='datetime' else 'date'
            if f['maxLength']:spec['maxLength']=f['maxLength']
            if f['auto']:spec['readOnly']=True
            if not f['required']:spec['nullable']=True
            props[f['name']]=spec
            if not f['auto']:
                writeprops[f['name']]=spec
                if f['required'] and not f['default']:required.append(f['name'])
        schemas[key]={'type':'object','properties':props}
        create={'type':'object','additionalProperties':False,'properties':writeprops,'required':required}
        patch={'type':'object','additionalProperties':False,'properties':{k:v for k,v in writeprops.items() if k not in meta['pk']},'minProperties':1}
        errors={str(s):{'description':d} for s,d in [(400,'Datos inválidos'),(404,'No encontrado'),(409,'Duplicado, dependencia o regla de negocio')]}
        base='/api/v1/'+key
        paths[base]={'get':{'summary':'Listar '+key,'parameters':[{'name':n,'in':'query','schema':{'type':t}} for n,t in [('page','integer'),('per_page','integer'),('q','string')]],'responses':{'200':{'description':'Lista paginada'}}},'post':{'summary':'Crear '+key,'requestBody':{'required':True,'content':{'application/json':{'schema':create}}},'responses':{'201':{'description':'Creado'},**errors}}}
        path=base+''.join('/{'+name+'}' for name in meta['pk'])
        params=[{'name':n,'in':'path','required':True,'schema':props[n]} for n in meta['pk']]
        paths[path]={'parameters':params,'get':{'summary':'Consultar registro','responses':{'200':{'description':'Registro'},'404':errors['404']}},'patch':{'summary':'Actualizar registro','requestBody':{'required':True,'content':{'application/json':{'schema':patch}}},'responses':{'200':{'description':'Actualizado'},**errors}},'delete':{'summary':'Eliminar sin dependencias y si el estado lo permite','responses':{'204':{'description':'Eliminado'},**errors}}}
    for kind in ('demanda','desempeno'):
        paths['/api/v1/reportes/'+kind]={'get':{'summary':'Reporte de '+kind,'parameters':[{'name':n,'in':'query','required':True,'schema':{'type':'string','format':'date-time'}} for n in ('desde','hasta')],'responses':{'200':{'description':'items con resultados; desde inclusivo, hasta exclusivo'},'400':{'description':'Periodo inválido'}}}}
    return {'openapi':'3.0.3','info':{'title':'Peer Tutoring API','version':'1.0.0','description':'Prototipo local de operador. Sin autenticación. Los estados se controlan mediante sesiones; consultar README para transiciones y restricciones.'},'servers':[{'url':'http://localhost:5055'}],'paths':paths,'components':{'schemas':schemas}}
