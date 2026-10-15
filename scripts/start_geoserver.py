"""Start only the project-owned GeoServer, bound to loopback with deny-by-default data access."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.start_elastic import load_private_environment,hidden

load_private_environment()
home=ROOT/'services/geoserver-2.27.2'
java=next((ROOT/'services/java').rglob('java.exe'))
security=home/'data_dir/security'
(security/'layers.properties').write_text('*.*.r=ADMIN\n*.*.w=ADMIN\neast_india.schools.r=RAG_GEO\neast_india.roads.r=RAG_GEO\neast_india.landuse.r=RAG_GEO\nmode=CHALLENGE\n')
(security/'services.properties').write_text('wfs.Transaction=ADMIN\nwfs.LockFeature=ADMIN\nwfs.CreateStoredQuery=ADMIN\nwfs.DropStoredQuery=ADMIN\n')
os.environ['GEOSERVER_DATA_DIR']=str(home/'data_dir')
command=[str(java),'-Xms256m','-Xmx768m','-Djava.awt.headless=true',
         '-DGEOSERVER_DATA_DIR='+str(home/'data_dir'),'-jar','start.jar','jetty.http.host=127.0.0.1','jetty.http.port=8080']
pid=hidden(command,home,ROOT/'services/geoserver-console.log')
(ROOT/'services/geoserver-process.json').write_text(json.dumps({'pid':pid,'port':8080}))
print('Started GeoServer process',pid)
