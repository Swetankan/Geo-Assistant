"""Run the requested 150 local generations on ten synthetic development prompts."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import live_assistant
from app.settings import ROOT
from evalsuite.dev import sampling_runs
from retrieve.filters import QueryFilter

def main():
    assistant=live_assistant(); questions=[json.loads(x) for x in (ROOT/'evalsuite/dev_questions.jsonl').read_text(encoding='utf-8').splitlines() if x]
    def provider(query):
        hits,*_=assistant.retrieve(query,assistant.query_entities(query),QueryFilter(),'graph_hybrid')
        reranked=assistant.reranker.rerank(query,hits[:20],assistant.chunks,16) if hits else []
        return [{'chunk_id':h.chunk_id,'text':assistant.chunks[h.chunk_id].text[:700]} for h in reranked[:5]]
    rows=sampling_runs(assistant.llm,questions,provider)
    report={'synthetic_questions_and_corpus':True,'primary_embedding_model':assistant.settings['embedding_models'][0]['source'],
            'generation_repetitions':5,'temperatures':[0,.3,.7],
            'top_p':assistant.settings['generation_top_p'],'top_k':assistant.settings['generation_top_k'],
            'consistency_metric':'exact normalized answer plus citation-ID majority fraction; fact proxy uses required phrase substrings',
            'results':rows,'summary_by_temperature':{str(t):{'mean_majority_consistency':sum(r['majority_exact_text_citation_proxy'] for r in rows if r['temperature']==t)/sum(r['temperature']==t for r in rows),
              'citation_valid_run_fraction':sum(run['citations_valid'] for r in rows if r['temperature']==t for run in r['runs'])/50} for t in (0,.3,.7)}}
    path=ROOT/'evidence/live_synthetic_sampling.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary_by_temperature'],indent=2))
if __name__=='__main__':main()
