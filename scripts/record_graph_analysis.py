"""Record named graph statistics and synthetic expansion benefit/noise examples."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import live_assistant
from app.settings import ROOT
from retrieve.filters import QueryFilter

def main():
    a=live_assistant(); stats=a.graph.statistics()
    degree=sorted(((a.entities[i].canonical_name,d,i) for i,d in stats['top_degree']),key=lambda x:(-x[1],x[0]))
    stats['top_degree_named']=[{'name':n,'degree':d,'id':i,'type':a.entities[i].type.value} for n,d,i in degree]
    pagerank=stats.pop('pagerank')
    stats['top_pagerank']=[{'name':a.entities[i].canonical_name,'id':i,'score':s} for i,s in sorted(pagerank.items(),key=lambda x:(-x[1],x[0]))[:5]]
    schools=[e for e in a.entities.values() if e.type.value=='School' and e.attributes.osm_id
             and any(a.entities[n['entity_id']].type.value=='Circular'
                     for n in a.graph.neighbours(e.id,2))]
    advantage=None
    for school in schools:
        for phrasing in ('Which policy applies to', 'What directive governs', 'What does the admission guidance say for'):
            q=f'{phrasing} {school.canonical_name}?'
            ids=a.query_entities(q)
            if not ids:continue
            kw,*_=a.retrieve(q,ids,QueryFilter(),'keyword'); gh,paths,*_=a.retrieve(q,ids,QueryFilter(),'graph_hybrid')
            kset={h.chunk_id for h in kw[:5]}; gset={h.chunk_id for h in gh[:5]}
            added=[i for i in gset-kset if a.chunks[i].synthetic and a.chunks[i].source.endswith('.md')]
            linked_circular_ids={n['entity_id'] for n in a.graph.neighbours(school.id,2) if a.entities[n['entity_id']].type.value=='Circular'}
            linked_chunks={m.chunk_id for eid in linked_circular_ids for m in a.entities[eid].mentions}
            added=[i for i in added if i in linked_chunks]
            if added:
                advantage={'query':q,'school':school.canonical_name,'keyword_top5':[{'id':i,'text':a.chunks[i].text[:180]} for i in sorted(kset)],
                           'graph_hybrid_top5':[{'id':i,'text':a.chunks[i].text[:180]} for i in sorted(gset)],
                           'synthetic_chunks_added':[{'id':i,'text':a.chunks[i].text[:260]} for i in added],
                           'path_count':len(paths)};break
        if advantage:break
    q='What does CBSE stand for?'; ids=a.query_entities(q)
    kw,*_=a.retrieve(q,ids,QueryFilter(),'keyword'); gh,paths,*_=a.retrieve(q,ids,QueryFilter(),'graph_hybrid')
    kset={h.chunk_id for h in kw[:5]}; gset={h.chunk_id for h in gh[:5]}
    noise={'query':q,'seed_entities':[a.entities[i].canonical_name for i in ids],
           'expanded_paths':len(paths),'synthetic_chunks_added':[{'id':i,'text':a.chunks[i].text[:240]} for i in sorted(gset-kset) if a.chunks[i].synthetic],
           'mitigation':'two-hop traversal with fan-out 20, top-5 evidence cap, plus reranker and fitted confidence/abstention'}
    report={'synthetic_policy_data':True,'nodes':stats['nodes'],'edges':stats['edges'],'components':stats['components'],
            'top_degree':stats['top_degree_named'],'top_pagerank':stats['top_pagerank'],'graph_expansion_benefit':advantage,'graph_expansion_noise':noise}
    (ROOT/'evidence/live_synthetic_graph_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('top_degree','top_pagerank')},indent=2))
if __name__=='__main__':main()
