"""Record live local service and scoped identity checks without recording secrets."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
import psutil
from app.runtime import load_app_environment
from app.settings import ROOT,load_settings
from es.client import ElasticStore
from scripts.start_elastic import load_private_environment
from geoserver.client import GeoServer

def main():
    load_private_environment();load_app_environment();settings=load_settings()
    admin=ElasticStore(settings,admin=True); app=ElasticStore(settings); identity=app.authenticate()
    health=admin.request('GET','/_cluster/health'); version=admin.request('GET','/')
    role=admin.request('GET','/_security/role/rag_app')['rag_app']
    app_info={k:role.get(k) for k in ('cluster','indices')}
    with httpx.Client(trust_env=False,timeout=10) as c:
        kibana=c.get('http://127.0.0.1:5601/api/status')
        llm=c.get(settings['llm_url']+'/health')
    geo=GeoServer(settings); access=geo.access_check(); layers={n:len(geo.features(n)) for n in ('schools','roads','landuse')}
    process_file=ROOT/'services/llama-process.json'
    llm_pids=set()
    if process_file.exists():
        try: llm_pids.add(json.loads(process_file.read_text())['pid'])
        except (KeyError,ValueError): pass
    llm_pids.update(c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr and c.laddr.port==8081 and c.pid)
    llm_processes=[]
    for pid in sorted(llm_pids):
        try:
            proc=psutil.Process(pid)
            if proc.name().lower()=='llama-server.exe': llm_processes.append({'pid':pid,'rss_bytes':proc.memory_info().rss})
        except psutil.Error: pass
    llm_rss=sum(x['rss_bytes'] for x in llm_processes) if llm_processes else None
    model_path=ROOT/settings['llm_path']
    report={'elasticsearch':{'version':version['version']['number'],'health':health,'app_identity':identity,
                             'role_indices':app_info['indices'],'role_cluster_privileges':app_info['cluster'],
                             'counts':{k:app.count(i) for k,i in settings['indices'].items()}},
            'kibana':{'status_code':kibana.status_code,'available':kibana.status_code==200},
            'llama_cpp':{'health_status':llm.status_code,'available':llm.status_code==200,'configured_model':settings['llm_model'],
                         'parameter_count':'1.5B','quantization':'Q4_K_M','model_file_bytes':model_path.stat().st_size if model_path.exists() else None,
                         'context_length_configured':settings['llm_context'],'process_rss_bytes':llm_rss,'server_processes':llm_processes,
                         'tokens_per_second_from_smoke':json.loads((ROOT/'evidence/llm_smoke.json').read_text(encoding='utf-8'))['usage'].get('tokens_per_second')},
            'primary_embedding_model':settings['embedding_models'][0]['source'],
            'geoserver':{'version':'2.27.2','access':access,'feature_counts':layers,
                         'roads_landuse_synthetic':True}}
    (ROOT/'evidence/live_service_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
