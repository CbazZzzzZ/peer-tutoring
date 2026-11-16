"""Compare a pg_dump/pg_restore copy, without altering either database."""
import json
from pathlib import Path
from sqlalchemy import create_engine,select,text
from app import create_app
from app.models import db
app=create_app()
with app.app_context():
    assert db.engine.dialect.name=='postgresql'
    restored=create_engine(db.engine.url.set(database='peer_tutoring_restore'))
    results={}
    with db.engine.connect() as source,restored.connect() as target:
        for table in db.metadata.sorted_tables:
            query=select(table).order_by(*table.primary_key.columns)
            a=source.execute(query).all();b=target.execute(query).all()
            assert a==b,table.name
            results[table.name]={'original':len(a),'restored':len(b),'all_values_equal':True}
        invalid=target.execute(text("SELECT count(*) FROM pg_constraint WHERE NOT convalidated")).scalar_one()
        assert invalid==0
    output={'engine':'postgresql','method':'pg_dump custom + pg_restore into separate database','tables':results,'unvalidated_constraints':invalid,'status':'passed'}
    Path('docs/backup_postgresql.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output))
