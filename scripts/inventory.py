"""Read-only inventory; never records environment variable values or credentials."""
import importlib.metadata
import json
import platform
import shutil
import socket
import sqlite3
import sys
from pathlib import Path
import psutil


def inventory(gpkg):
    report = dict(python=sys.version, platform=platform.platform(), cpu_count=psutil.cpu_count(),
                  ram_bytes=psutil.virtual_memory().total,
                  packages={p: importlib.metadata.version(p) for p in ['numpy','pydantic','pytest','httpx','shapely','pyproj','streamlit','pypdf','networkx']},
                  executables={p: bool(shutil.which(p)) for p in ['docker','ollama','java','git','nvidia-smi']})
    report['ports'] = {}
    for port in (9200,5601,8080,11434,8000,1234):
        with socket.socket() as sock:
            sock.settimeout(.3)
            report['ports'][str(port)] = sock.connect_ex(('127.0.0.1',port)) == 0
    with sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True) as db:
        report['gpkg'] = []
        for table, kind, srs in db.execute('SELECT table_name,data_type,srs_id FROM gpkg_contents'):
            quoted = '"' + table.replace('"','""') + '"'
            columns = [x[1] for x in db.execute(f'PRAGMA table_info({quoted})')]
            entry = dict(table=table,kind=kind,srs=srs,columns=columns,count=db.execute(f'SELECT count(*) FROM {quoted}').fetchone()[0])
            if 'name' in columns:
                entry['named_count'] = db.execute(f"SELECT count(*) FROM {quoted} WHERE name IS NOT NULL AND trim(name) != ''").fetchone()[0]
            report['gpkg'].append(entry)
    return report


if __name__ == '__main__':
    target = Path('evidence/inventory.json')
    target.parent.mkdir(exist_ok=True)
    report = inventory(Path(sys.argv[1]))
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
