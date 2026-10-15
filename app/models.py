"""Lazy local-only adapters. Downloading assets is a separate explicit setup action."""
import json
import os
import time
from pathlib import Path
import httpx
import numpy as np
from app.settings import local_url
from app.schemas import RankedResult


class LocalEmbeddings:
    def __init__(self,config):
        path=Path(config['path'])
        if not path.is_dir():
            raise FileNotFoundError(f'Local embedding model missing: {path}')
        os.environ['HF_HUB_OFFLINE']='1'
        os.environ['TRANSFORMERS_OFFLINE']='1'
        from sentence_transformers import SentenceTransformer
        self.config=config
        self.model=SentenceTransformer(str(path.resolve()),local_files_only=True,trust_remote_code=False)
        if self.model.get_embedding_dimension()!=config['dimensions']:
            raise ValueError('Embedding dimension differs from configured mapping')

    def encode(self,texts,query=False,batch_size=32):
        prefix=self.config['query_prefix' if query else 'document_prefix']
        return self.model.encode([prefix+t for t in texts],batch_size=batch_size,
                                 normalize_embeddings=self.config['normalize'],show_progress_bar=False)


class LocalReranker:
    def __init__(self,config):
        path=Path(config['path'])
        if not path.is_dir():
            raise FileNotFoundError(f'Local reranker missing: {path}')
        os.environ['HF_HUB_OFFLINE']='1'
        from sentence_transformers import CrossEncoder
        import torch
        self.model=CrossEncoder(str(path.resolve()),max_length=config['max_length'],local_files_only=True,
                                trust_remote_code=False,activation_fn=torch.nn.Identity())
        self.config=config

    def rerank(self,query,hits,chunks,batch_size=16):
        if not hits:
            return []
        scores=self.model.predict([(query,chunks[h.chunk_id].text) for h in hits],batch_size=batch_size,show_progress_bar=False)
        values=np.asarray(scores).reshape(-1)
        if len(values)!=len(hits) or not np.isfinite(values).all():
            raise ValueError('Reranker requires one finite score per passage')
        return sorted([RankedResult(chunk_id=h.chunk_id,score=float(s),sources=h.sources+['cross_encoder'])
                       for h,s in zip(hits,values)],key=lambda h:(-h.score,h.chunk_id))


class OllamaLLM:
    def __init__(self,settings):
        self.url=local_url(settings['llm_url'])
        self.settings=settings
        self.last_usage={}

    def json(self,system,data,temperature=0):
        started=time.perf_counter()
        options=dict(temperature=temperature,top_p=self.settings['generation_top_p'],
                     top_k=self.settings['generation_top_k'],seed=self.settings['seed'],num_predict=2048)
        with httpx.Client(timeout=180,trust_env=False) as client:
            response=client.post(self.url+'/api/chat',json=dict(model=self.settings['llm_model'],stream=False,format='json',
                              messages=[dict(role='system',content=system),dict(role='user',content=data)],options=options))
            response.raise_for_status()
            body=response.json()
        self.last_usage=dict(elapsed_seconds=time.perf_counter()-started,eval_count=body.get('eval_count'),
                             tokens_per_second=body.get('eval_count',0)/(body['eval_duration']/1e9) if body.get('eval_duration') else None,
                             decoding=options,log_probabilities_supported=False)
        return json.loads(body['message']['content'])


class LlamaCppLLM:
    """OpenAI-compatible protocol on loopback; this never calls the OpenAI API."""
    def __init__(self,settings):
        self.url=local_url(settings['llm_url'])
        self.settings=settings
        self.last_usage={}

    def json(self,system,data,temperature=0):
        started=time.perf_counter()
        options={'temperature':temperature,'top_p':self.settings['generation_top_p'],
                 'top_k':self.settings['generation_top_k'],'seed':self.settings['seed'],'max_tokens':1200}
        with httpx.Client(timeout=180,trust_env=False) as client:
            response=client.post(self.url+'/v1/chat/completions',json={
                'model':self.settings['llm_model'],'messages':[{'role':'system','content':system},{'role':'user','content':data}],
                'response_format':{'type':'json_object'},'stream':False,'logprobs':True,**options})
            response.raise_for_status()
            body=response.json()
        choice=body['choices'][0]
        logprobs=choice.get('logprobs') or {}
        values=[x['logprob'] for x in logprobs.get('content',[]) if x.get('logprob') is not None]
        elapsed=time.perf_counter()-started
        count=body.get('usage',{}).get('completion_tokens')
        self.last_usage={'elapsed_seconds':elapsed,'eval_count':count,'tokens_per_second':count/elapsed if count else None,
                         'throughput_scope':'end-to-end request, includes prompt processing',
                         'decoding':options,'log_probabilities_supported':bool(values),
                         'mean_token_log_probability':float(np.mean(values)) if values else None}
        return json.loads(choice['message']['content'])


def local_llm(settings):
    return LlamaCppLLM(settings) if settings.get('llm_backend')=='llama_cpp' else OllamaLLM(settings)
