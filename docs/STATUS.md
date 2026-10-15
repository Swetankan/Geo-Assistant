# My implementation and evidence status

Last updated: 2026-10-15. I label generated data and scores as synthetic in [PROJECT DOCUMENT.md](../PROJECT%20DOCUMENT.md). They are not assessor results.

## Checks I ran

- I checked Elasticsearch 8.19.0 and Kibana. Elasticsearch is green. I verified that `rag_app` can access only the three required indices. See `evidence/live_service_check.json`.
- I ran ingestion twice through `rag_app`. Both runs produced the same counts: 1,078 chunks, 1,156 entities and 142 relations after synthetic road enrichment. See `evidence/ingestion.json` and `evidence/live_service_check.json`.
- I compared Elasticsearch HNSW with exact NumPy search on 20 synthetic queries at 20, 50 and 100 candidates. I also checked an admin-only int8 index. See `evidence/synthetic_assessment/ann_results.json` and `evidence/live_quantized_comparison.json`.
- I checked GeoServer 2.27.2. Anonymous access returns 401 and authenticated access returns 200. It serves 1,062 supplied school polygons and 12 synthetic roads and land-use polygons. The synthetic shapes are only for testing.
- I ran Qwen2.5-1.5B Q4_K_M through local llama.cpp and received token log probabilities. The extraction output validates, but its accuracy is weak. See `evidence/llm_smoke.json` and the synthetic extraction report.
- My automated test run passed 20 tests. Two service integration tests were skipped.

## Synthetic evaluation

- I created 12 fictional circulars and synthetic benchmark files. Reports cover retrieval, embeddings, ANN search, reranking, entity extraction, graph metrics and confidence calibration.
- I generated the labels from the same fixtures used by the pipeline. The scores are pipeline checks, not independent quality results. I selected all-MiniLM-L6-v2 as the primary embedder based on this synthetic comparison. See `evidence/live_synthetic_embedding_comparison.json`.
- My fit-only calibration did not find a threshold that reached 90% accuracy. The assistant therefore abstained on all 10 generated development questions. Coverage was 0%; I did not estimate answer or citation accuracy because it produced no answer.
- I ran 150 generation consistency checks. Exact answer and citation consistency was 1.00, 0.82 and 0.54 at temperatures 0, 0.3 and 0.7. Citation IDs were valid in 100%, 100% and 96% of runs. This checks repeatability, not factual accuracy. See `evidence/live_synthetic_sampling.json`.

## Limits and remaining item

- I did not receive real admissions notices or assessor-provided gold labels. The school polygons contain no board, seat, cutoff or admission policy facts.
- I made the road and land-use examples synthetically. Do not use them for navigation or school advice.
- The small model's extraction quality is weak. No confidence threshold passed my target, so the app abstains.
- I still need my mobile number to create the required final archive filename. The project does not email or submit the archive.
- I staged a clean folder at `output/East_India_GeoAssistant_Submission_Ready`. Its `evidence/` folder has logs, but I have not added the required screenshots yet. I have not created a ZIP.
