"""Evaluate the live Elasticsearch/local-model pipeline on the clearly synthetic judgments."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import live_assistant
from app.settings import ROOT
from evalsuite.datasets import load_questions
from evalsuite.retrieval import tune_then_holdout,reranker_comparison

def main():
    questions=load_questions(ROOT/'evalsuite/retrieval_judgments.jsonl')
    assistant=live_assistant()
    output=ROOT/'evidence/live_synthetic_retrieval_v3'
    chosen,holdout=tune_then_holdout(assistant,questions,output)
    rows=reranker_comparison(assistant,[q for q in questions if q.split=='holdout'],batch_sizes=(16,))
    (output/'reranker_results.json').write_text(json.dumps({'synthetic':True,'results':rows},indent=2),encoding='utf-8')
    print(json.dumps({'synthetic':True,'rrf_constant':chosen,'reranker_rows':len(rows),'output':str(output)},indent=2))
if __name__=='__main__':main()
