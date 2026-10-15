"""Capture real command results without credentials or private source text."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.cli import demo_assistant
from es.mappings import mappings
from retrieve.safety import redact

result=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'command':'python -m pytest -q',
        'return_code':result.returncode,'stdout':redact(result.stdout),'stderr':redact(result.stderr)}
(ROOT/'evidence/tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assistant=demo_assistant()
answer,trace=assistant.answer('How many seats at Lotus Demo School?')
(ROOT/'evidence/synthetic_smoke.json').write_text(json.dumps({'synthetic':True,'answer':answer.model_dump(mode='json'),'trace':trace},indent=2),encoding='utf-8')
for name,mapping in mappings().items():
    (ROOT/'es'/f'{name}.mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
print(report['stdout'])
sys.exit(result.returncode)
