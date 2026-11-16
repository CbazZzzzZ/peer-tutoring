import sys
import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from sqlalchemy.schema import CreateTable,CreateIndex
from app import create_app,api_spec
from app.models import *

app=create_app()
def seed():
    if db.session.scalar(select(Estudiante.id_estudiante).limit(1)):
        print('La base ya contiene registros; no se modificaron.');return
    people=[Estudiante(nombre=n,correo=e,carrera=c,anio_ingreso=2024) for n,e,c in [('Ana Torres','ana@example.test','Computación'),('Luis Mendoza','luis@example.test','Matemáticas'),('Marta Ruiz','marta@example.test','Física'),('Diego Vera','diego@example.test','Computación')]]
    db.session.add_all(people);db.session.flush()
    tutors=[Tutor(id_estudiante=people[i].id_estudiante,promedio=g) for i,g in [(1,9.2),(2,9.5)]]
    courses=[Curso(codigo_curso=code,nombre_curso=n,departamento=d,creditos=4) for code,n,d in [('BD101','Bases de Datos','Computación'),('MAT101','Cálculo I','Matemáticas'),('FIS101','Física I','Física')]]
    db.session.add_all(tutors+courses);db.session.flush()
    today=now().replace(hour=15,minute=0,second=0,microsecond=0)
    for t in tutors:
        for code in ['BD101','MAT101','FIS101']:db.session.add(Calificacion(id_tutor=t.id_tutor,codigo_curso=code,fecha_certificacion=(today-timedelta(days=60)).date()))
        for days in range(1,15):db.session.add(Disponibilidad(id_tutor=t.id_tutor,inicio=today+timedelta(days=days)-timedelta(hours=1),fin=today+timedelta(days=days,hours=7)))
    for i,(code,days,state) in enumerate([('BD101',-2,'completada'),('MAT101',-1,'completada'),('BD101',1,'programada'),('FIS101',2,'programada')]):
        q=SolicitudTutoria(id_estudiante=people[0 if i%2==0 else 3].id_estudiante,codigo_curso=code,tema=['Consultas JOIN y relaciones','Derivadas e integrales','Normalización a 3FN','Movimiento y fuerzas'][i],estado='cerrada' if state=='completada' else 'asignada',fecha_solicitud=today-timedelta(days=4))
        db.session.add(q);db.session.flush()
        s=SesionTutoria(id_solicitud=q.id_solicitud,id_tutor=tutors[i%2].id_tutor,inicio=today+timedelta(days=days),fin=today+timedelta(days=days,hours=1),lugar='Biblioteca · sala '+str(i+1),estado=state)
        db.session.add(s);db.session.flush()
        if state=='completada':db.session.add(Retroalimentacion(id_sesion=s.id_sesion,calificacion=5 if i==0 else 4,comentarios='La explicación me ayudó a resolver los ejercicios.',fecha=now()))
    db.session.add(SolicitudTutoria(id_estudiante=people[0].id_estudiante,codigo_curso='FIS101',tema='Vectores y leyes de Newton'))
    from app.service import validate_all
    db.session.flush();validate_all();db.session.commit();print('Datos ficticios cargados correctamente.')

with app.app_context():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'init'
    if cmd=='init':db.create_all();print('Esquema listo.')
    elif cmd=='seed':db.create_all();seed()
    elif cmd=='export':
        Path('docs').mkdir(exist_ok=True)
        Path('docs/openapi.json').write_text(json.dumps(api_spec(),ensure_ascii=False,indent=2),encoding='utf-8')
        from sqlalchemy.dialects import postgresql,sqlite
        for name,dialect in [('postgresql',postgresql.dialect()),('sqlite',sqlite.dialect())]:
            sql='-- Esquema generado desde los modelos ORM: '+name+'.\n-- Validaciones cruzadas: app/service.py.\n\n'
            if name=='sqlite':sql+='PRAGMA foreign_keys=ON;\n'
            for table in db.metadata.sorted_tables:
                sql+=str(CreateTable(table).compile(dialect=dialect))+';\n'
                for index in sorted(table.indexes,key=lambda x:x.name):sql+=str(CreateIndex(index).compile(dialect=dialect))+';\n'
            Path('docs/schema_'+name+'.sql').write_text('\n'.join(line.rstrip() for line in sql.splitlines()).rstrip()+'\n',encoding='utf-8')
        print('OpenAPI y SQL exportados.')
    else:raise SystemExit('Uso: python manage.py init|seed|export')
