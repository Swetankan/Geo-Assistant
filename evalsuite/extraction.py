"""Run both extractors against explicitly mapped gold spans; record all failures."""
import time
from evalsuite.metrics import entity_scores


def spans(entities,chunks):
    records=[]
    for entity in entities:
        for mention in entity.mentions:
            chunk=chunks[mention.chunk_id]
            records.append(dict(type=entity.type.value,document_id=chunk.document_id,page=chunk.page,
                                start=chunk.start+mention.start,end=chunk.start+mention.end))
    # Overlapping chunks may repeat the identical mention; deduplicate before scoring.
    return [dict(items) for items in sorted({tuple(sorted(r.items())) for r in records},key=str)]


def compare_extractors(chunks,gold,rules,llm):
    results=[]
    by_id={c.id:c for c in chunks}
    previous=None
    for name,extractor,temperature in [('rules',rules,None),('llm_greedy_1',llm,0),('llm_greedy_2',llm,0),('llm_sampled',llm,.7)]:
        entities,failures,timing=[],[],[]
        for chunk in chunks:
            started=time.perf_counter()
            try:
                entities.extend(extractor.extract(chunk) if temperature is None else extractor.extract(chunk,temperature))
            except ValueError as error:
                failures.append({'chunk_id':chunk.id,'error_type':type(error).__name__})
            timing.append({'chunk_id':chunk.id,'seconds':time.perf_counter()-started,
                           'usage':getattr(getattr(extractor,'llm',None),'last_usage',{})})
        predicted=spans(entities,by_id)
        result=dict(name=name,temperature=temperature,exact=entity_scores(predicted,gold),relaxed=entity_scores(predicted,gold,True),
                    failures=failures,timing=timing,predicted=predicted)
        if name=='llm_greedy_1':
            previous=predicted
        if name=='llm_greedy_2':
            result['identical_to_first_greedy']=predicted==previous
        results.append(result)
    return results
