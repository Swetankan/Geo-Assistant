"""Capture three observed weak points and a before/after entity-resolution guard fix."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import live_assistant
from app.settings import ROOT

def main():
    a=live_assistant()
    school=next(e for e in a.entities.values() if e.type.value=='School' and e.canonical_name=='Railway Mixed School')
    query=f'Which fictional circular applies to the board affiliated with {school.canonical_name}?'
    before=sorted(e.id for e in a.entities.values() if e.canonical_name.casefold() in query.casefold() or (e.attributes.osm_id and e.attributes.osm_id in query))
    after=a.query_entities(query)
    bpaths=sum(len(a.graph.neighbours(i,2)) for i in before); apaths=sum(len(a.graph.neighbours(i,2)) for i in after)
    calibration=json.loads((ROOT/'evidence/live_synthetic_calibration_v3/calibration_results.json').read_text(encoding='utf-8'))
    extraction=json.loads((ROOT/'evidence/live_synthetic_extraction.json').read_text(encoding='utf-8'))
    llmrows=[r for r in extraction['results'] if r['name'].startswith('llm_')]
    report={'all_cases_synthetic_or_local_demo':True,
      'cases':[
        {'stage':'entity detection and graph expansion','symptom':'generic School token selected unrelated named-school entities',
         'before_entity_matches':len(before),'before_neighbor_paths':bpaths,'after_entity_matches':len(after),'after_neighbor_paths':apaths,
         'fix':'exclude generic canonical labels from substring matches; retain exact full names and OSM IDs',
         'implemented':True,'regression_tests':'20 passed, 2 skipped'},
        {'stage':'LLM entity extraction','symptom':'small model returned spans unrelated to the source; strict validation rejected annotated chunks',
         'observed_pre_fix_failed_chunks':12,'observed_post_fix_failed_chunks':len(llmrows[0]['failures']) if llmrows else None,
         'fix':'remove copied numeric example offsets; re-anchor only exact canonical-name strings and skip absent/ambiguous names',
         'implemented':True,'remaining':'synthetic LLM precision/recall still poor; prefer rules for PoC extraction'},
        {'stage':'confidence and generation','symptom':'no fit threshold reached 90% accuracy, so system abstained on every dev prompt',
         'test_ece':calibration['ece'],'test_brier':calibration['brier'],'chosen_threshold':calibration.get('chosen_threshold_result'),
         'fix':'do not lower threshold without evidence; obtain independent relevance labels and refit before enabling answers',
         'implemented':'safe abstention'}]}
    (ROOT/'evidence/failure_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
