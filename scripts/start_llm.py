"""Start the portable local model server hidden, with fixed bounded context."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.settings import load_settings

settings=load_settings()
model=ROOT/settings['llm_path']
executable=ROOT/'services/llama/llama-server.exe'
if not model.exists() or not executable.exists():
    raise SystemExit('Portable llama-server or configured GGUF is missing')
log=ROOT/'services/llama-server.log'
with log.open('a',encoding='utf-8') as handle:
    process=subprocess.Popen([str(executable),'-m',str(model),'--host','127.0.0.1','--port','8081',
                              '-c',str(settings['llm_context']),'-t','6','-ngl','0','--alias',settings['llm_model']],
                             cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
(ROOT/'services/llama-process.json').write_text(json.dumps({'pid':process.pid,'port':8081}))
print('Started local llama.cpp process',process.pid)
