import os
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import select,func
from app import create_app
from app.models import db,now,SolicitudTutoria,SesionTutoria,Estudiante

@pytest.fixture
def app(tmp_path):
    url=os.getenv('TEST_DATABASE_URL','sqlite:///'+str(tmp_path/'peer_test.db'))
    if url.startswith('postgresql') and not url.endswith('/peer_tutoring_test'):
        raise RuntimeError('Tests require the isolated peer_tutoring_test database.')
    app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':url})
    with app.app_context():db.drop_all();db.create_all()
    yield app
    with app.app_context():db.session.remove();db.drop_all()

@pytest.fixture
def client(app):return app.test_client()

def post(c,r,body,status=201):
    result=c.post('/api/v1/'+r,json=body)
    assert result.status_code==status,result.json
    return result.json

@pytest.fixture
def setup(client):
    c=client
    students=[post(c,'estudiantes',dict(nombre=n,correo=n+'@example.test',carrera='Computación',anio_ingreso=2024)) for n in ['Ana','Luis','Marta','Diego']]
    tutors=[post(c,'tutores',dict(id_estudiante=s['id_estudiante'],promedio=9.0)) for s in students[1:3]]
    for code in ['C1','C2']:post(c,'cursos',dict(codigo_curso=code,nombre_curso=code,departamento='Ciencias',creditos=4))
    base=now().replace(minute=0,second=0,microsecond=0)+timedelta(days=2)
    for t in tutors:
        post(c,'calificaciones',dict(id_tutor=t['id_tutor'],codigo_curso='C1',fecha_certificacion=(base-timedelta(days=30)).date().isoformat()))
        post(c,'disponibilidades',dict(id_tutor=t['id_tutor'],inicio=(base-timedelta(days=10)).isoformat(),fin=(base+timedelta(days=10)).isoformat()))
    q=post(c,'solicitudes',dict(id_estudiante=students[0]['id_estudiante'],codigo_curso='C1',tema='Repaso'))
    body=dict(id_solicitud=q['id_solicitud'],id_tutor=tutors[0]['id_tutor'],inicio=base.isoformat(),fin=(base+timedelta(hours=1)).isoformat(),lugar='Sala A')
    return {'students':students,'tutors':tutors,'base':base,'q':q,'body':body}

def test_student_crud_and_normalized_email(client):
    s=post(client,'estudiantes',dict(nombre='Ana',correo='ANA@EXAMPLE.TEST',carrera='Física',anio_ingreso=2024))
    assert s['correo']=='ana@example.test'
    url='/api/v1/estudiantes/'+str(s['id_estudiante'])
    assert client.patch(url,json={'nombre':'Ana Torres'}).status_code==200
    assert client.get(url).json['nombre']=='Ana Torres'
    assert client.delete(url).status_code==204
    assert client.get(url).status_code==404

def test_duplicate_and_validation(client,setup):
    s=setup['students'][0]
    post(client,'estudiantes',{k:v for k,v in s.items() if k!='id_estudiante'},409)
    post(client,'estudiantes',dict(nombre='A',correo='bad',carrera='X',anio_ingreso=2024),400)
    post(client,'tutores',dict(id_estudiante=setup['students'][1]['id_estudiante'],promedio=8),409)
    post(client,'tutores',dict(id_estudiante=9999,promedio=8),404)
    post(client,'solicitudes',dict(id_estudiante=9999,codigo_curso='C1',tema='X'),404)
    assert client.get('/api/v1/estudiantes?per_page=101').status_code==400

def test_create_session_and_atomic_status(client,setup):
    s=post(client,'sesiones',setup['body'])
    assert s['estado']=='programada'
    assert client.get('/api/v1/solicitudes/'+str(setup['q']['id_solicitud'])).json['estado']=='asignada'
    assert client.get('/api/v1/sesiones?codigo_curso=C1&id_estudiante=1').json['total']==1
    assert client.delete('/api/v1/sesiones/'+str(s['id_sesion'])).status_code==204
    assert client.get('/api/v1/solicitudes/'+str(setup['q']['id_solicitud'])).json['estado']=='pendiente'

def test_not_qualified_and_no_partial_write(client,setup):
    q=post(client,'solicitudes',dict(id_estudiante=1,codigo_curso='C2',tema='X'))
    post(client,'sesiones',{**setup['body'],'id_solicitud':q['id_solicitud']},409)
    assert client.get('/api/v1/sesiones').json['total']==0
    assert client.get('/api/v1/solicitudes/'+str(q['id_solicitud'])).json['estado']=='pendiente'

def test_availability_and_interval(client,setup):
    b=setup['body'];base=setup['base']
    post(client,'sesiones',{**b,'fin':b['inicio']},400)
    post(client,'sesiones',{**b,'inicio':(base+timedelta(days=20)).isoformat(),'fin':(base+timedelta(days=20,hours=1)).isoformat()},409)

def test_overlap_and_contiguous(client,setup):
    post(client,'sesiones',setup['body'])
    q=post(client,'solicitudes',dict(id_estudiante=4,codigo_curso='C1',tema='X'))
    base=setup['base']
    body={**setup['body'],'id_solicitud':q['id_solicitud'],'inicio':(base+timedelta(minutes=30)).isoformat(),'fin':(base+timedelta(hours=1,minutes=30)).isoformat()}
    post(client,'sesiones',body,409)
    post(client,'sesiones',{**body,'inicio':(base+timedelta(hours=1)).isoformat(),'fin':(base+timedelta(hours=2)).isoformat()})

def test_student_overlap_other_tutor_and_self(client,setup):
    post(client,'sesiones',setup['body'])
    q=post(client,'solicitudes',dict(id_estudiante=1,codigo_curso='C1',tema='X'))
    post(client,'sesiones',{**setup['body'],'id_solicitud':q['id_solicitud'],'id_tutor':2},409)
    q=post(client,'solicitudes',dict(id_estudiante=2,codigo_curso='C1',tema='X'))
    post(client,'sesiones',{**setup['body'],'id_solicitud':q['id_solicitud']},409)

def test_cross_role_overlap(client,setup):
    post(client,'sesiones',setup['body'])
    q=post(client,'solicitudes',dict(id_estudiante=2,codigo_curso='C1',tema='X'))
    post(client,'sesiones',{**setup['body'],'id_solicitud':q['id_solicitud'],'id_tutor':2},409)

def test_complete_future_cancel_and_terminal(client,setup):
    s=post(client,'sesiones',setup['body']);url='/api/v1/sesiones/'+str(s['id_sesion'])
    assert client.patch(url,json={'estado':'completada'}).status_code==409
    assert client.patch(url,json={'estado':'cancelada'}).status_code==200
    assert client.patch(url,json={'estado':'completada'}).status_code==409
    assert client.get('/api/v1/solicitudes/1').json['estado']=='cancelada'

def completed(c,setup):
    past=now()-timedelta(days=2)
    s=post(c,'sesiones',{**setup['body'],'inicio':past.isoformat(),'fin':(past+timedelta(hours=1)).isoformat()})
    assert c.patch('/api/v1/sesiones/'+str(s['id_sesion']),json={'estado':'completada'}).status_code==200
    return s

def test_feedback_state_range_unique_and_crud(client,setup):
    s=post(client,'sesiones',setup['body']);url='/api/v1/sesiones/'+str(s['id_sesion'])
    post(client,'retroalimentaciones',dict(id_sesion=s['id_sesion'],calificacion=5),409)
    assert client.delete(url).status_code==204
    s=completed(client,setup)
    post(client,'retroalimentaciones',dict(id_sesion=s['id_sesion'],calificacion=6),400)
    f=post(client,'retroalimentaciones',dict(id_sesion=s['id_sesion'],calificacion=5,comentarios='Bien'))
    post(client,'retroalimentaciones',dict(id_sesion=s['id_sesion'],calificacion=4),409)
    furl='/api/v1/retroalimentaciones/'+str(f['id_feedback'])
    assert client.patch(furl,json={'comentarios':'Muy claro'}).status_code==200
    assert client.delete('/api/v1/sesiones/'+str(s['id_sesion'])).status_code==409
    assert client.delete(furl).status_code==204

def test_dependency_deletion_and_invalidating_changes(client,setup):
    post(client,'sesiones',setup['body'])
    assert client.delete('/api/v1/cursos/C1').status_code==409
    assert client.delete('/api/v1/calificaciones/1/C1').status_code==409
    assert client.delete('/api/v1/disponibilidades/1').status_code==409
    assert client.patch('/api/v1/disponibilidades/1',json={'fin':(setup['base']-timedelta(hours=1)).isoformat()}).status_code==409
    assert client.get('/api/v1/disponibilidades/1').json['fin']>setup['body']['fin']

def test_reports_boundaries_and_null(client,setup):
    s=completed(client,setup)
    post(client,'retroalimentaciones',dict(id_sesion=s['id_sesion'],calificacion=5))
    params={'desde':(now()-timedelta(days=10)).isoformat(),'hasta':(now()+timedelta(days=10)).isoformat()}
    d=client.get('/api/v1/reportes/demanda',query_string=params).json['items']
    assert {x['codigo_curso']:x['solicitudes'] for x in d}=={'C1':1,'C2':0}
    rows=client.get('/api/v1/reportes/desempeno',query_string=params).json['items']
    assert rows[0]['promedio']==5 and rows[0]['evaluadas']==1
    assert rows[1]['promedio'] is None
    when=client.get('/api/v1/solicitudes/1').json['fecha_solicitud']
    d=client.get('/api/v1/reportes/demanda',query_string={'desde':when,'hasta':params['hasta']}).json['items'];assert d[0]['solicitudes']==1
    d=client.get('/api/v1/reportes/demanda',query_string={'desde':params['desde'],'hasta':when}).json['items'];assert all(x['solicitudes']==0 for x in d)

def test_remaining_resource_crud(client,setup):
    t=post(client,'tutores',dict(id_estudiante=4,promedio=8))
    assert client.patch('/api/v1/tutores/'+str(t['id_tutor']),json={'promedio':9}).status_code==200
    assert client.delete('/api/v1/tutores/'+str(t['id_tutor'])).status_code==204
    post(client,'cursos',dict(codigo_curso='X',nombre_curso='X',departamento='X',creditos=1))
    assert client.patch('/api/v1/cursos/X',json={'nombre_curso':'Nuevo'}).status_code==200
    post(client,'calificaciones',dict(id_tutor=1,codigo_curso='X',fecha_certificacion='2020-01-01'))
    assert client.patch('/api/v1/calificaciones/1/X',json={'fecha_certificacion':'2021-01-01'}).status_code==200
    assert client.delete('/api/v1/calificaciones/1/X').status_code==204
    assert client.delete('/api/v1/cursos/X').status_code==204
    assert client.patch('/api/v1/solicitudes/1',json={'tema':'Nuevo tema'}).status_code==200
    assert client.delete('/api/v1/solicitudes/1').status_code==204
    assert client.delete('/api/v1/disponibilidades/1').status_code==204

def test_concurrent_booking(app,client,setup):
    q=post(client,'solicitudes',dict(id_estudiante=4,codigo_curso='C1',tema='Otra'))
    barrier=Barrier(2)
    def book(body):
        with app.test_client() as c:
            barrier.wait()
            return c.post('/api/v1/sesiones',json=body).status_code
    with ThreadPoolExecutor(max_workers=2) as ex:
        a=ex.submit(book,setup['body']);b=ex.submit(book,{**setup['body'],'id_solicitud':q['id_solicitud']})
        assert sorted([a.result(),b.result()])==[201,409]
    assert client.get('/api/v1/sesiones').json['total']==1
    assert sum(q['estado']=='asignada' for q in client.get('/api/v1/solicitudes').json['items'])==1

def test_ui_docs_and_spec(client):
    assert client.get('/').status_code==200
    assert client.get('/static/app.js').status_code==200
    assert client.get('/docs').status_code==200
    assert client.get('/openapi.json').json['openapi']=='3.0.3'
    assert client.get('/health').json['status']=='ok'

def test_reports_with_10000_sessions(app,client,setup):
    """Synthetic, isolated history; measure full endpoint and JSON response."""
    import json,time
    from pathlib import Path
    from app.models import Tutor,Curso,Calificacion,Retroalimentacion
    from datetime import date
    end=now()-timedelta(hours=1)
    start=end-timedelta(hours=10001)
    with app.app_context():
        db.session.get(Calificacion,(1,'C1')).fecha_certificacion=date(2000,1,1)
        db.session.add(Calificacion(id_tutor=1,codigo_curso='C2',fecha_certificacion=date(2000,1,1)))
        db.session.add_all([SolicitudTutoria(id_solicitud=100+i,id_estudiante=1,codigo_curso='C1' if i%2==0 else 'C2',fecha_solicitud=start+timedelta(hours=i),tema='Carga sintética',estado='cerrada') for i in range(10000)])
        db.session.flush()
        db.session.add_all([SesionTutoria(id_sesion=100+i,id_solicitud=100+i,id_tutor=1,inicio=start+timedelta(hours=i),fin=start+timedelta(hours=i+1),lugar='Prueba',estado='completada') for i in range(10000)])
        db.session.flush()
        db.session.add_all([Retroalimentacion(id_feedback=100+i,id_sesion=100+i,calificacion=5 if i%2==0 else 3,fecha=end) for i in range(10000)])
        db.session.commit()
        engine=db.engine.dialect.name
    params={'desde':start.isoformat(),'hasta':end.isoformat()}
    measurements={}
    for kind in ('demanda','desempeno'):
        elapsed=[]
        for _ in range(5):
            t=time.perf_counter();r=client.get('/api/v1/reportes/'+kind,query_string=params);elapsed.append(time.perf_counter()-t)
            assert r.status_code==200,r.json
            if kind=='demanda':assert {x['codigo_curso']:x['solicitudes'] for x in r.json['items']}=={'C1':5000,'C2':5000}
            else:
                row=next(x for x in r.json['items'] if x['id_tutor']==1)
                assert row['completadas']==10000 and row['evaluadas']==10000 and row['promedio']==4.0
        measurements[kind]={'seconds':elapsed,'max_seconds':max(elapsed),'mean_seconds':sum(elapsed)/len(elapsed)}
        assert max(elapsed)<2.0,measurements
    evidence={'engine':engine,'sessions':10000,'evaluations':10000,'samples_per_report':5,'measurements':measurements,'scope':'Flask test client, complete request and JSON, isolated synthetic database; not a load/concurrent-users benchmark'}
    Path('docs').mkdir(exist_ok=True)
    Path('docs/performance_'+engine+'.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')

def test_forced_failure_rolls_back(client,setup,monkeypatch):
    from app import service
    def fail():raise service.Problem('Fallo controlado antes de confirmar.',409,'PRUEBA_ROLLBACK')
    monkeypatch.setattr(service,'validate_all',fail)
    post(client,'sesiones',setup['body'],409)
    assert client.get('/api/v1/sesiones').json['total']==0
    assert client.get('/api/v1/solicitudes/1').json['estado']=='pendiente'


def test_cancelled_session_preserves_qualification(client,setup):
    s=post(client,'sesiones',setup['body'])
    assert client.patch('/api/v1/sesiones/'+str(s['id_sesion']),json={'estado':'cancelada'}).status_code==200
    assert client.delete('/api/v1/calificaciones/1/C1').status_code==409
    assert client.get('/api/v1/calificaciones/1/C1').status_code==200
    # Cancelled history does not prevent a fresh request using the same time.
    q=post(client,'solicitudes',dict(id_estudiante=1,codigo_curso='C1',tema='Nuevo intento'))
    post(client,'sesiones',{**setup['body'],'id_solicitud':q['id_solicitud']})


def test_session_history_filters(client,setup):
    s=post(client,'sesiones',setup['body'])
    base='/api/v1/sesiones'
    filters=dict(id_tutor=s['id_tutor'],id_estudiante=1,codigo_curso='C1',estado='programada',desde=setup['body']['inicio'],hasta=setup['body']['fin'])
    assert client.get(base,query_string=filters).json['total']==1
    assert client.get(base,query_string={**filters,'codigo_curso':'C2'}).json['total']==0
    assert client.get(base,query_string={**filters,'desde':setup['body']['fin'],'hasta':(setup['base']+timedelta(hours=2)).isoformat()}).json['total']==0
