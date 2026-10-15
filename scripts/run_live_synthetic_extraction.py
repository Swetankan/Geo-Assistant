"""Compare rule and local LLM entity extraction on explicitly synthetic annotations."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models import local_llm
from app.runtime import load_app_environment
from app.schemas import Chunk,Entity
from app.settings import ROOT,load_settings
from evalsuite.extraction import compare_extractors
from ingest.extract import RuleExtractor,LLMExtractor

def main():
    load_app_environment()
    chunks=[Chunk.model_validate_json(x) for x in (ROOT/'data/private/corpus/chunks.jsonl').read_text(encoding='utf-8').splitlines() if x]
    selected_docs={json.loads(x)['doc_id'] for x in (ROOT/'evalsuite/gold_entities.jsonl').read_text(encoding='utf-8').splitlines() if x}
    chunks=[c for c in chunks if c.document_id in selected_docs]
    records=[json.loads(x) for x in (ROOT/'evalsuite/gold_entities.jsonl').read_text(encoding='utf-8').splitlines() if x]
    by_id={c.id:c for c in chunks}; gold=[]
    for row in records:
        chunk=by_id[row['chunk_id']]
        gold.extend({'type':e['type'],'document_id':chunk.document_id,'page':chunk.page,'start':chunk.start+e['start'],'end':chunk.start+e['end']} for e in row['entities'])
    schools=[Entity.model_validate_json(x) for x in (ROOT/'data/private/schools/entities.jsonl').read_text(encoding='utf-8').splitlines() if x]
    results=compare_extractors(chunks,gold,RuleExtractor(schools),LLMExtractor(local_llm(load_settings())))
    out=ROOT/'evidence/live_synthetic_extraction.json'
    out.write_text(json.dumps({'synthetic':True,'note':'Gold labels are generated from explicit fixture patterns, not assessor annotations.','results':results},indent=2),encoding='utf-8')
    print(json.dumps([{'name':r['name'],'temp':r['temperature'],'exact':r['exact'],'relaxed':r['relaxed'],'greedy_repeat_equal':r.get('identical_to_first_greedy'),'failures':len(r['failures'])} for r in results],indent=2))
if __name__=='__main__':main()
