# How I checked the assessment requirements

I use “synthetic” for data I generated. It does not mean assessor-provided gold data. “Live check” means I ran a command against a local service or model. See [PROJECT DOCUMENT.md](../PROJECT%20DOCUMENT.md) for the data limits.

| Requirement | What I used | Evidence | My status |
|---|---|---|---|
| Elasticsearch, Kibana and health | `scripts/start_elastic.py` | `evidence/live_service_check.json` | I verified green Elasticsearch and live Kibana. |
| Scoped `rag_app` access and secrets | `es/bootstrap.py`, `es/client.py` | Local service report | I verified the app role and index scope. |
| Local model, embeddings and reranker | `app/models.py` | `evidence/llm_smoke.json`, `evidence/model_smoke.json` | I ran smoke checks. Extraction quality is weak. |
| GeoServer login and WFS | `geoserver/` | `evidence/geoserver_integration.json`, `evidence/synthetic_geoserver_layers.json` | I verified access. Non-school shapes are synthetic. |
| Document and PDF parsing, chunk offsets | `ingest/documents.py` | Tests and corpus JSONL | I checked code and tests, but lack an assessor PDF corpus. |
| Entity types, schema and resolution | `app/schemas.py`, `ingest/extract.py` | Tests; `evidence/live_synthetic_extraction.json` | I evaluated synthetic examples. LLM extraction is weak. |
| Exact and relaxed entity metrics | `evalsuite/metrics.py`, `evalsuite/extraction.py` | Synthetic extraction report | I checked code on generated annotations only. |
| Stable IDs and repeat ingestion | `ingest/run.py` | `evidence/ingestion.json` | I verified matching counts on two live runs. |
| Two embedding models | `app/models.py` | `evidence/live_synthetic_embedding_comparison.json` | I compared them on generated judgments. |
| HNSW vs exact search | `scripts/run_ann_experiment.py` | `evidence/synthetic_assessment/ann_results.json` | I ran the live ES comparison on synthetic queries. |
| Quantized index and size | `scripts/run_quantized_comparison.py` | `evidence/live_quantized_comparison.json` | I checked int8 HNSW. App permissions did not change. |
| PIT and `search_after` paging | `es/client.py` | `evidence/live_pit_paging.json` | I verified two pages using the app identity. |
| Relations and bounded graph search | `ingest/relations.py`, `retrieve/graph.py` | Near-relations and graph reports | I checked traversal on synthetic examples. Road shapes are synthetic. |
| Four retrieval modes and ranking metrics | `app/pipeline.py`, `evalsuite/retrieval.py` | `evidence/live_synthetic_retrieval_v3/` | I evaluated with generated labels. |
| Cross-encoder reranking | `app/models.py`, `evalsuite/retrieval.py` | Reranker report | I ran the local model on generated labels. |
| Confidence, calibration and abstention | `retrieve/confidence.py`, `evalsuite/calibration.py` | `evidence/live_synthetic_calibration_v3/` | I tested generated labels. No threshold met my target. |
| Sampling temperature consistency | `evalsuite/dev.py` | `evidence/live_synthetic_sampling.json` | I ran 150 local generations. The result is a consistency check only. |
| End-to-end answer and citations | `app/pipeline.py` | `evidence/live_synthetic_dev_results.json` | I tested ten synthetic questions. The app abstained on all ten. |
| Safety and untrusted text | `retrieve/safety.py`, app pipeline | Automated tests | I checked test cases. This is not an exhaustive security audit. |
| UI and architecture diagram | `app/ui.py`, `diagram/` | `diagram/architecture.png`, source SVG/Mermaid | I built the UI and diagram; I visually checked the PNG. |
| Algorithms and disclosures | `PROJECT DOCUMENT.md` | Project document | I documented methods and limitations. |
| Submission folder and archive | `scripts/package.py` | `output/East_India_GeoAssistant_Submission_Ready/` | I staged the clean folder. I still need screenshots and my mobile number before I can create the final ZIP. |
