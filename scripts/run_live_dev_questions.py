"""Run the end-to-end safe pipeline on 10 synthetic dev prompts; record abstentions honestly."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import live_assistant
from app.settings import ROOT

def main():
    qa=[json.loads(x) for x in (ROOT/'evalsuite/dev_questions.jsonl').read_text(encoding='utf-8').splitlines() if x]
    assistant=live_assistant(ROOT/'evidence/live_synthetic_calibration_v3/calibrator.json')
    results=[]
    for row in qa:
        answer,trace=assistant.answer(row['query'])
        retrieved=trace.get('reranked',[])
        cited={c.chunk_id for c in answer.citations}
        retrieved_ids={x['chunk_id'] for x in retrieved}
        results.append({'id':row['id'],'question':row['query'],'synthetic_question':True,
                        'entities_found':trace.get('entities',[]),'top_passages':[{'chunk_id':x['chunk_id'],'score':x['score'],'text':assistant.chunks[x['chunk_id']].text[:500]} for x in retrieved],
                        'confidence':answer.confidence,'answer':answer.answer,'citations':[c.model_dump(mode='json') for c in answer.citations],
                        'citations_retrieved_check':bool(cited<=retrieved_ids),'answer_correct':None if answer.answer.startswith('I cannot answer') else None,
                        'citation_correct':None if not answer.citations else None,'abstained':answer.answer.startswith('I cannot answer'),
                        'trace_reason':trace.get('reason'),'synthetic':True})
        print(row['id'],'abstained' if results[-1]['abstained'] else 'answered',flush=True)
    count=len(results); answered=sum(not r['abstained'] for r in results)
    report={'synthetic_data':True,'warning':'Questions and policies are fictional. No independent human answer/citation labels were supplied.',
            'results':results,'summary':{'questions':count,'answered':answered,'coverage':answered/count if count else 0,
             'answer_accuracy':None,'citation_accuracy':None,'reason':'all outputs abstain because synthetic fit data did not support a >=90% accuracy threshold'}}
    path=ROOT/'evidence/live_synthetic_dev_results.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report['summary'],indent=2))
if __name__=='__main__':main()
