import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.settings import load_settings
from app.models import local_llm
from app.models import LlamaCppLLM
from app.schemas import Chunk
from ingest.extract import LLMExtractor

settings=load_settings()
llm=local_llm(settings)
result=llm.json('Return a JSON object only.','Return status: local inference works',0)
report={'synthetic':True,'assessment_quality_evaluation':False,'model':settings['llm_model'],
        'quantization':'Q4_K_M (GGUF filename; verify server metadata separately)',
        'context_configured':settings['llm_context'],'response':result,'usage':dict(llm.last_usage),'extractions':[]}
text='CBSE has 40 seats. Date: 2026-11-01.'
chunk=Chunk(id='smoke',document_id='synthetic',source='synthetic_llm_smoke',start=0,end=len(text),text=text,synthetic=True)
# Use a compact, explicit extraction contract; llama.cpp enforces JSON-object decoding.
for temperature in (0,0,.7):
    extractor=LLMExtractor(llm)
    try:
        entities=extractor.extract(chunk,temperature)
        row={'temperature':temperature,'entities':[e.model_dump(mode='json') for e in entities],'validated':True}
    except ValueError:
        row={'temperature':temperature,'validated':False}
    row['validation_failures']=extractor.failures
    row['usage']=dict(llm.last_usage)
    report['extractions'].append(row)
(ROOT/'evidence/llm_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
