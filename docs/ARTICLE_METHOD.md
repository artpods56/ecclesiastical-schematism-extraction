# Article-to-code concordance

This document identifies the implementation behind the method described in
*The Use of Advanced Digital Tools in Documentary Work on the Historical
Geography of the Church*. The authoritative parameter values are in
`configs/article/paper-v1.yaml`; defaults elsewhere must agree with that file and
are checked by `schematism-artifact verify`.

| Article method | Implementation | Frozen setting |
| --- | --- | --- |
| 42-schematism evaluation corpus | `configs/article/paper-v1.yaml` and `scripts/dagster/run_evaluation_jobs.py` | Exact list of 42 appendix identifiers; `liber_crac_1529` excluded |
| PDF split into page images | `src/notarius/application/use_cases/ingestion/ingest_documents_from_pdf.py` | Page-level records retain source filename and page association |
| Vision-model OCR rendered as Markdown | `pred__llm_ocr_enriched_dataset__pydantic` in `src/notarius/orchestration/assets/transform/predict.py` | Task `ocr`, prompt version `0.0.1` |
| Tesseract word coordinates | `src/notarius/infrastructure/ocr/engine_adapter.py` | Languages `lat+pol+rus`; coordinates support LayoutLMv3 |
| Fine-tuned LayoutLMv3 hints | `pred__lmv3_enriched_dataset__pydantic` in `src/notarius/orchestration/assets/transform/predict.py` | Checkpoint `layoutlmv3_focalloss_4000`; disabled for the reported corpus run |
| Sequential multimodal extraction | `pred__llm_enriched_dataset__pydantic` in `src/notarius/orchestration/assets/transform/predict.py` | Gemini 3 Flash Preview through OpenRouter; temperature `0.1` |
| Previous-page state | `PageContext` in `src/notarius/domain/entities/schematism.py` and `PreviousPageDomainContextProvider` in `src/notarius/application/services/context/provider.py` | Active deanery, last page number, summary, optional review note |
| Current and following-page OCR | `PageContentContextProvider` in `src/notarius/application/services/context/provider.py` | Offsets `0` and `1` |
| Bounded conversation history | `SlidingWindowStrategy` in `src/notarius/application/services/context/strategy.py` | Five exchanges; images and duplicated next-page OCR stripped |
| Structured extraction instructions | `src/notarius/infrastructure/llm/prompts/tasks/structured_extraction/` | Prompt version `0.0.3`; hashes pinned in the paper config |
| Source-form to project-value parsing | `src/notarius/domain/services/parser.py` and `data/mappings/` | Dedication, building-material, and deanery dictionaries |
| Record pairing | `HungarianAligner` in `src/notarius/application/services/data/aligning.py` | Threshold `0.5`; four field weights pinned in the paper config |
| Source and parsed evaluation | `src/notarius/application/services/scoring/` and `src/notarius/orchestration/assets/load/export.py` | Normalized Levenshtein for source form; exact match for parsed form |

## Supported artifact boundary

The supported citation surface is the paper configuration, the modules named in
the table, their transitive runtime dependencies, the frozen prompts, the mapping
dictionaries, and the Włocławek running example. Other inherited notebooks,
alternative provider configurations, development services, and source-generation
experiments remain in Git history for provenance; they do not define the reported
42-schematism run.

The 1529 Kraków book of endowments is a different source type and is outside the
reported evaluation. Its outputs must not be included when aggregating the 42
diocesan schematisms.

## Reproducibility boundary

The repository can reconstruct the pipeline and submit a new run, but it cannot
guarantee byte-identical output from a remote generative model. The accompanying
research-data package therefore preserves the evaluated source-form predictions,
parsed predictions, reference tables, per-source metrics, and manifests. The code
tag records how those artifacts were produced; the data deposition records what
was actually evaluated.
