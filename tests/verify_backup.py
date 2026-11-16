"""Read-only snapshot of the demo database, restored into a separate test file."""
import sqlite3
import json
from pathlib import Path
src=sqlite3.connect('instance/peer_tutoring.db')
dst=sqlite3.connect('.test-runs/backup_verified.db')
src.backup(dst)
tables=[r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
counts={t:[src.execute('SELECT count(*) FROM '+t).fetchone()[0],dst.execute('SELECT count(*) FROM '+t).fetchone()[0]] for t in tables}
result={'integrity_check':dst.execute('PRAGMA integrity_check').fetchone()[0], 'foreign_key_check':dst.execute('PRAGMA foreign_key_check').fetchall(), 'counts_original_restored':counts}
assert result['integrity_check']=='ok' and not result['foreign_key_check']
assert all(a==b for a,b in counts.values())
Path('docs/resultado_respaldo.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result));dst.close();src.close()
