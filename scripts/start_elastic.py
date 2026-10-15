"""Provision a new local portable Elasticsearch/Kibana installation.

Only touches this project's ignored services/ and .env. Never prints secrets.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import zipfile
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.settings import load_settings
from es.bootstrap import provision


def load_private_environment():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.startswith('#'):
                key,value=line.split('=',1)
                os.environ[key]=value
    required={'ES_ADMIN_USER':'elastic','ES_APP_USER':'rag_app','GEO_USER':'rag_geo'}
    for key,value in required.items():
        os.environ.setdefault(key,value)
    for key in ('ES_ADMIN_PASSWORD','ES_APP_PASSWORD','KIBANA_PASSWORD','GEO_PASSWORD','GEO_ADMIN_PASSWORD'):
        os.environ.setdefault(key,secrets.token_urlsafe(32))
    keys=list(required)+['ES_ADMIN_PASSWORD','ES_APP_PASSWORD','KIBANA_PASSWORD','GEO_PASSWORD','GEO_ADMIN_PASSWORD']
    if not path.exists():
        path.write_text('\n'.join(k+'='+os.environ[k] for k in keys)+'\n')


def extract(name):
    target=ROOT/'services'/name
    if not target.is_dir():
        archive=ROOT/'services'/(name+'-windows-x86_64.zip')
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                if not (ROOT/'services'/item.filename).resolve().is_relative_to((ROOT/'services').resolve()):
                    raise ValueError('Unsafe archive entry')
            bundle.extractall(ROOT/'services')
    return target


def hidden(command,cwd,log):
    with Path(log).open('a',encoding='utf-8') as handle:
        process=subprocess.Popen(command,cwd=cwd,env=os.environ.copy(),stdout=handle,stderr=subprocess.STDOUT,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
    return process.pid


def main():
    settings=load_settings()
    load_private_environment()
    es=extract('elasticsearch-'+settings['elasticsearch_version'])
    kibana=extract('kibana-'+settings['kibana_version'])
    config=es/'config/elasticsearch.yml'
    marker=es/'config/.geoassistant-configured'
    if not marker.exists():
        config.write_text('cluster.name: east-india-local\nnode.name: east-india-node\ndiscovery.type: single-node\nnetwork.host: 127.0.0.1\nhttp.port: 9200\nxpack.security.enabled: true\nxpack.security.autoconfiguration.enabled: false\nxpack.security.http.ssl.enabled: false\nxpack.security.transport.ssl.enabled: false\n',encoding='utf-8')
        (es/'config/jvm.options.d/heap.options').write_text('-Xms1g\n-Xmx1g\n')
        # Supply bootstrap password through stdin, never command arguments or logs.
        result=subprocess.run(['cmd.exe','/c',str(es/'bin/elasticsearch-keystore.bat'),'add','-x','-f','bootstrap.password'],
                              input=os.environ['ES_ADMIN_PASSWORD']+'\n',text=True,capture_output=True,cwd=es)
        if result.returncode:
            raise RuntimeError('Elasticsearch keystore configuration failed')
        marker.write_text('local configuration created\n')
    with httpx.Client(timeout=3,trust_env=False) as client:
        try:
            running=client.get(settings['es_url']).status_code in (200,401)
        except httpx.HTTPError:
            running=False
    if not running:
        pid=hidden(['cmd.exe','/c',str(es/'bin/elasticsearch.bat')],es,ROOT/'services/elasticsearch-console.log')
        print('Started Elasticsearch process',pid,flush=True)
    with httpx.Client(auth=('elastic',os.environ['ES_ADMIN_PASSWORD']),timeout=10,trust_env=False) as client:
        for attempt in range(90):
            try:
                response=client.get(settings['es_url'])
                if response.status_code==200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(2)
        else:
            raise RuntimeError('Elasticsearch did not become ready; inspect private service log')
        response=client.post(settings['es_url']+'/_security/user/kibana_system/_password',json={'password':os.environ['KIBANA_PASSWORD']})
        response.raise_for_status()
    report=provision(settings)
    (ROOT/'evidence/elasticsearch_bootstrap.json').write_text(json.dumps(report,indent=2))
    (kibana/'config/kibana.yml').write_text('server.host: "127.0.0.1"\nserver.port: 5601\nelasticsearch.hosts: ["http://127.0.0.1:9200"]\nelasticsearch.username: "kibana_system"\nelasticsearch.password: "${KIBANA_PASSWORD}"\ntelemetry.enabled: false\n',encoding='utf-8')
    pid=hidden(['cmd.exe','/c',str(kibana/'bin/kibana.bat')],kibana,ROOT/'services/kibana-console.log')
    print('Started Kibana process',pid,flush=True)
    print('Elasticsearch provisioned:',report['health']['status'],flush=True)


if __name__=='__main__':
    main()
