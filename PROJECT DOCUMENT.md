# East India Geo-Assistant

## My project status

I built a local school map and a prototype assistant. My test run passed 20 tests; two service tests were skipped. The assistant abstains when its confidence checks do not support an answer. I have not submitted or emailed the project.

I did not receive assessor-provided model identities, admissions documents or evaluation labels. I chose provisional open models and marked generated data as synthetic. I have not claimed that the assessor supplied these models.

## Data and model disclosure

- I used the supplied `schools.gpkg`. It contains 1,062 school building polygons, 623 with names. Points shown on the map are representative points inside polygons, not school entrances.
- I wrote 12 fictional admission notices in `evalsuite/fixtures/corpus/`. School names come from the GeoPackage, but boards, places, seat counts, age rules, cutoffs and dates are invented.
- I generated the benchmark files in `evalsuite/` to exercise the code. I generated entity labels with deterministic patterns and retrieval judgments from fixture links. Calibration labels and scores are illustrative. These files are not assessor gold data or real accuracy results.
- I used provisional local models: Qwen2.5-1.5B-Instruct Q4_K_M through llama.cpp, `intfloat/e5-small-v2`, `sentence-transformers/all-MiniLM-L6-v2`, and `cross-encoder/ms-marco-MiniLM-L-6-v2`. My synthetic comparison favored all-MiniLM-L6-v2: recall@5 was 0.35 versus 0.20, and throughput was 115 versus 57 chunks per second. These results apply only to my generated test set.
- I saved generated reports under `evidence/`. I keep synthetic results separate from real service checks.
- I do not use paid APIs or cloud inference.

## What I ran

I imported 1,062 school polygons and created 1,078 total chunks. The source has 623 named features. My 12 fictional circulars use school names from the source, but all policy details are invented. GeoServer serves the real school polygons and synthetic road and land-use examples.

I checked Elasticsearch 8.19.0, Kibana, llama.cpp and GeoServer 2.27.2. Elasticsearch was green. I checked access through `rag_app` and confirmed that anonymous GeoServer access was denied while authenticated WFS access worked. I ran ingestion twice and got the same counts. After synthetic road enrichment, the indices held 1,078 chunks, 1,156 entities and 142 relations. See `evidence/live_service_check.json`, `evidence/ingestion.json`, `evidence/geoserver_integration.json` and `evidence/synthetic_near_relations.json`.

I compared embeddings, approximate and exact search, reranking, graph traversal and confidence calibration using generated labels. My small LLM extractor was weak and less consistent than the rule-based baseline. I did not treat the generated labels as independent evidence.

My latest confidence run had test ECE 0.0133 and Brier score 0.0624 on generated labels. No fit threshold reached my 90% accuracy target. The assistant abstained on all 10 generated development questions, so coverage was 0%. I did not estimate answer or citation accuracy. In 150 generation runs, answer and citation consistency was 1.00 at temperature 0, 0.82 at 0.3 and 0.54 at 0.7. Citation IDs were valid in 100%, 100% and 96% of runs. This is a repeatability check, not a factuality score.

## My setup and source data

I used Windows, Python 3.10.5, an Intel i5-11400H, 12 logical processors, about 16 GB RAM and an NVIDIA RTX 2050. GPU acceleration has not been measured. The service check is in `evidence/live_service_check.json`.

The GeoPackage has 1,062 MULTIPOLYGON features in EPSG:4326. Of those, 623 have names and 439 do not. I keep unnamed features under their supplied `osm_id` and do not invent names. The dataset has no district boundaries, so I use coordinates to show its coverage.

The polygon GeoJSON exports contain the same school features. Polygon-to-line exports are school boundaries, not roads. `converted.pdf` has no extractable text, so I did not use it as an admissions source. I did not find assessor-provided admissions documents or evaluation files in the workspace paths I checked.

## How I reproduce the project

I documented setup, import, test, CLI and UI commands in [README.md](README.md). I pinned Python packages in `requirements.txt`. Downloaded model weights, local service files and private data are excluded from the archive. The UI binds to loopback and disables telemetry in its launch command.

## My configured choices

I configured Elasticsearch and Kibana 8.19.0, GeoServer 2.27.2, Qwen2.5-1.5B through llama.cpp, E5-small-v2, all-MiniLM-L6-v2 and the MS MARCO MiniLM cross-encoder. These are my provisional choices. I would replace them if the assessor provides required model versions. Both embedding models produce 384-dimensional normalized vectors. E5 uses query and passage prefixes; MiniLM does not.

Elasticsearch index names must be lowercase and cannot contain spaces. I mapped the logical names `East India_chunks`, `East India_entities` and `East India_relations` to `east_india_chunks`, `east_india_entities` and `east_india_relations`. See [the Elasticsearch index naming rules](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/indices-create-index.html).

## How I process and retrieve data

I decode text as UTF-8 and keep newline characters. Entity offsets are zero-based, half-open Unicode character offsets within each chunk. PDF offsets refer to extracted page text, not PDF bytes or visual positions. My default chunk size is 1,000 characters with 150 characters of overlap. I chose this as a starting point, not from a tuning result. Stable IDs use normalized input hashes.

I score entity spans with one-to-one matching so duplicate predictions cannot claim the same annotation twice. My school resolver uses normalized string similarity of at least 0.92 and a 0.03 ambiguity margin. This is a conservative rule, not a tuned result. The LLM extractor checks typed attributes and exact spans, then retries once if validation fails.

I use Elasticsearch BM25 for keyword search. My in-process BM25 is only for a labeled synthetic smoke test. I use NumPy cosine similarity for exact vector search and break ties by chunk ID. Reciprocal rank fusion uses `1 / (60 + rank)` by default. Graph candidates are sorted by chunk ID before fusion, which makes results deterministic but can add noise.

I apply metadata and distance filters to keyword, vector and graph candidates. My graph search can traverse stored relations in either direction, keeps the original edge direction, finds shortest first-discovered paths and stops cycles. I limit it to one or two hops, cap fan-out and cap total visited nodes. I create near relations from original polygons using EPSG:32646 and a 300 m threshold. Only actual road features qualify. I create supersedes relations only when the text says so.

## Metrics and confidence

I implemented the metrics in `evalsuite/metrics.py` without an external evaluation library. Relevant grades are 1 and 2; unjudged items count as 0. nDCG gain is `2^grade - 1`. Precision divides by `k`, even when fewer results exist. If there are no relevant items, recall and nDCG are zero. I remove duplicate retrieved IDs after their first appearance and break equal-score ties by chunk ID.

I use five equal-width reliability bins. Each bin includes its left edge, and the last bin includes 1. ECE weights the absolute accuracy-confidence gap by the number of samples in each bin. Brier score is the mean squared probability error. I return null accuracy when no questions are answered. I fit calibration only on the fit split. If no threshold reaches 90% accuracy with nonzero coverage, I return no threshold.

My confidence estimate predicts whether the top passage is relevant. It does not guarantee that an answer is correct. My production path abstains without a fitted calibrator and a supported threshold. When llama.cpp provides token log probabilities, I record them. Otherwise, five-answer agreement is only a lexical and citation proxy.

## Safety and citations

I check user scope and test for instruction injection before answering. I pass retrieved text as JSON data, separate from system instructions, and do not expose document text as executable tools. Pattern checks add a safeguard, but cannot prove that all attacks are blocked. I require citations to match retrieved metadata and excerpts. That verifies where a citation came from, not whether it fully supports the answer. When I cannot support an answer, the app abstains.

## Algorithm notes

**BM25.** BM25 ranks text by term matches. It gives more weight to rare terms, limits the effect of repeated terms and adjusts for document length. I use Elasticsearch BM25 for keyword search in Task 5. My small Python version is only for the synthetic smoke demo.

**HNSW.** HNSW builds a layered graph of nearby vectors and searches that graph to find likely neighbors without comparing every vector. Elasticsearch uses it for approximate nearest-neighbor search in `east_india_chunks`. I set `m=16` and `ef_construction=100`; `num_candidates` controls search effort. I compare its top 10 with exact NumPy cosine search.

**Reciprocal rank fusion.** RRF combines ranked lists using each item's rank, so I do not need to compare raw scores from different retrievers. I use it to combine keyword, vector and graph results in hybrid modes.

**Cross-encoder.** A cross-encoder reads the query and passage together and gives them a relevance score. I use it to rerank the short graph-hybrid candidate list in Task 6. Batching and truncation limit its cost. Its raw scores also feed my confidence estimate.

**Softmax with temperature.** Softmax divides logits by a temperature, exponentiates them and scales the results to sum to one. Higher temperatures make the probabilities more even. I describe softmax for comparison, but calibrate binary passage relevance with `sigmoid(logit / T)`. This calibration temperature differs from the LLM sampling temperature.

**Greedy decoding.** At temperature zero, Qwen selects the highest-scoring next token each time. I use it for extraction repeats and the answer baseline. I compare it with sampling at 0.3 and 0.7. Repeatability does not prove correctness.

**Graph traversal.** My bounded breadth-first search visits related entities in a fixed order and tracks visited nodes to stop cycles. I use it to explore one- and two-hop relations in Task 4 and to add related evidence during retrieval in Task 5. Fan-out and total-node limits keep the search bounded.

## Credit and contributors

- **Contribution split, my estimate:** Sweta, 60%; OpenAI Codex, 40%.
- **My contribution:** I supplied the GeoPackage and assessment brief, set the project goals and interface direction, tested the assistant and reported issues, and chose the project scope and presentation. I am responsible for reviewing and explaining the implementation in the viva.
- **Codex contribution:** Codex assisted with repository review, code changes and debugging, synthetic fixtures and evaluation files, and documentation.
- **Data:** I used school geometry from the supplied `schools.gpkg`. I made the admissions policies and non-school geometry examples synthetically.
- **Third-party components:** I used Elasticsearch and Kibana, GeoServer, llama.cpp, Qwen2.5-1.5B-Instruct, `intfloat/e5-small-v2`, `sentence-transformers/all-MiniLM-L6-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2`, and the packages pinned in `requirements.txt`. I used no paid API or cloud inference.

## Remaining limits

I still need independent assessment data to measure real extraction and retrieval quality. My synthetic roads and land-use shapes are not real geography. The small model and calibration results do not support factual answers, so my app abstains. I have staged a clean folder at `output/East_India_GeoAssistant_Submission_Ready`, but I still need the required screenshots and my mobile number for the final archive name. I have not created a ZIP or submitted it by email.
