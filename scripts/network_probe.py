"""Compact local service health probe; does not enumerate remote release downloads."""
import httpx

TARGETS={
    'elasticsearch':('http://127.0.0.1:9200',401),
    'kibana':'http://127.0.0.1:5601/api/status',
    'geoserver':('http://127.0.0.1:8080/geoserver/rest/about/version.json',401),
    'llama_cpp':'http://127.0.0.1:8081/health',
}

def main():
    report={}
    with httpx.Client(timeout=5,trust_env=False) as client:
        for name,target in TARGETS.items():
            expected=target[1] if isinstance(target,tuple) else 200
            url=target[0] if isinstance(target,tuple) else target
            try:
                response=client.get(url)
                report[name]={'status':response.status_code,'listening':True,
                              'expected_auth_required':name in ('elasticsearch','geoserver'),
                              'ok':response.status_code==expected}
            except httpx.HTTPError as exc:
                report[name]={'listening':False,'error':type(exc).__name__,'ok':False}
    for name,result in report.items():
        print(f"{name}: {'OK' if result['ok'] else 'CHECK'} ({result.get('status','not listening')})")

if __name__=='__main__':main()
