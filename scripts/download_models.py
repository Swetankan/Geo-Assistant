"""Explicit asset download only. Runtime inference never accesses model registries."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'config/settings.json').read_text())
for model in config['embedding_models']+[config['reranker']]:
    print('Downloading provisional model:',model['source'],flush=True)
    snapshot_download(model['source'],local_dir=ROOT/model['path'],ignore_patterns=['*.onnx','onnx/*','openvino/*','*.h5','*.msgpack','*.ot'])
    print('Saved:',model['path'],flush=True)
