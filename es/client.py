"""Local REST adapter: scoped runtime, explicit administrator provisioning separately."""
import json
import os
import httpx
from app.settings import local_url
from app.schemas import RankedResult


class ElasticStore:
    def __init__(self,settings,admin=False):
        self.settings=settings
        self.allowed=set(settings['indices'].values())
        self.admin=admin
        prefix='ES_ADMIN' if admin else 'ES_APP'
        user=os.getenv(prefix+'_USER','')
        password=os.getenv(prefix+'_PASSWORD','')
        if not admin and user!='rag_app':
            raise ValueError('Runtime requires scoped rag_app user')
        if not user or not password:
            raise ValueError(f'{prefix} credentials missing')
        self.http=httpx.Client(base_url=local_url(settings['es_url']),auth=(user,password),timeout=60,trust_env=False)

    def request(self,method,path,**kwargs):
        response=self.http.request(method,path,**kwargs)
        if response.is_error:
            # Do not log response bodies: service messages may contain sensitive data.
            raise RuntimeError(f'Elasticsearch request failed (HTTP {response.status_code})')
        return response.json() if response.content else {}

    def assert_index(self,index):
        if index not in self.allowed:
            raise ValueError('Index is outside configured application scope')

    def authenticate(self):
        info=self.request('GET','/_security/_authenticate')
        if not self.admin and (info.get('username')!='rag_app' or set(info.get('roles',[]))!={'rag_app'}):
            raise ValueError('Runtime identity must have only rag_app role')
        return {'username':info.get('username'),'roles':info.get('roles')}

    def bulk(self,index,records):
        self.assert_index(index)
        records=list(records)
        failures=[]
        for offset in range(0,len(records),200):
            lines=[]
            for row in records[offset:offset+200]:
                lines.extend([json.dumps({'index':{'_index':index,'_id':row['id']}}),json.dumps(row)])
            if lines:
                result=self.request('POST','/_bulk',content='\n'.join(lines)+'\n',headers={'Content-Type':'application/x-ndjson'},params={'refresh':'wait_for'})
                for item in result['items']:
                    entry=item['index']
                    if entry['status']>=300:
                        failures.append({'id':entry.get('_id'),'status':entry['status'],'type':entry.get('error',{}).get('type')})
        if failures:
            raise RuntimeError(f'Bulk item failures: {failures}')
        return len(records)

    def count(self,index):
        self.assert_index(index)
        return self.request('GET',f'/{index}/_count')['count']

    def search(self,query,vector=None,k=50,filters=None,num_candidates=50):
        index=self.settings['indices']['chunks']
        clauses=filters.elastic() if filters else []
        if vector is None:
            body={'size':k,'query':{'bool':{'must':[{'match':{'text':query}}],'filter':clauses}},'sort':[{'_score':'desc'},{'id':'asc'}]}
            mode='bm25'
        else:
            body={'size':k,'knn':{'field':'embedding','query_vector':list(map(float,vector)),
                  'k':k,'num_candidates':max(k,num_candidates),'filter':{'bool':{'filter':clauses}}},
                  'sort':[{'_score':'desc'},{'id':'asc'}]}
            mode='knn'
        result=self.request('POST',f'/{index}/_search',json=body)
        return [RankedResult(chunk_id=h['_id'],score=h['_score'],sources=[mode]) for h in result['hits']['hits']]

    def pages(self,index,query=None,size=100):
        """Stable PIT scan; this is not unlimited pagination of kNN candidates."""
        self.assert_index(index)
        pit=self.request('POST',f'/{index}/_pit',params={'keep_alive':'1m'})['id']
        after=None
        try:
            while True:
                body={'size':size,'pit':{'id':pit,'keep_alive':'1m'},'query':query or {'match_all':{}},'sort':[{'id':'asc'},{'_shard_doc':'asc'}]}
                if after is not None:
                    body['search_after']=after
                result=self.request('POST','/_search',json=body)
                pit=result.get('pit_id',pit)
                hits=result['hits']['hits']
                if not hits:
                    break
                yield hits
                after=hits[-1]['sort']
        finally:
            self.request('DELETE','/_pit',json={'id':pit})
