"""Run a module with scoped credentials loaded from ignored local .env."""
import runpy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import load_app_environment
load_app_environment()
module=sys.argv[1]
sys.argv=sys.argv[1:]
runpy.run_module(module,run_name='__main__')
