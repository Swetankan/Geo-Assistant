"""Demonstrate live Elasticsearch point-in-time plus search_after pagination."""
import json,sys
from itertools import islice
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import load_app_environment
from app.settings import ROOT,load_settings
from es.client import ElasticStore

def main():
    load_app_environment(); settings=load_settings(); store=ElasticStore(settings); identity=store.authenticate()
    pages=list(islice(store.pages(settings['indices']['chunks'],size=10),2))
    ids=[[x['_id'] for x in page] for page in pages]
    report={'identity':identity,'page_size':10,'first_page_ids':ids[0] if ids else [],'second_page_ids':ids[1] if len(ids)>1 else [],
            'pages_disjoint':len(ids)>1 and not(set(ids[0])&set(ids[1])),'both_pages_full':len(ids)>1 and all(len(x)==10 for x in ids[:2]),
            'method':'PIT with stable id and _shard_doc sorts; search_after from last hit'}
    (ROOT/'evidence/live_pit_paging.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
