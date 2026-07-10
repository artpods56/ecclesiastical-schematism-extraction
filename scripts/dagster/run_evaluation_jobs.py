import dagster as dg
from dagster_graphql import DagsterGraphQLClient

from notarius.article import load_article_config
from notarius.config import DagsterConfig
from notarius.infrastructure.llm.utils import parse_model_name
from notarius.orchestration.assets.extract.ingest import (
    PdfToDatasetConfig,
    raw__pdf__dataset,
)
from notarius.orchestration.assets.load.export import (
    ParsedDataFrameExportConfig,
    PredsSourceExportConfig,
    SourceDataFrameExportConfig,
    eval__excel_export_parsed_dataframe__pandas,
    eval__excel_export_source_dataframe__pandas,
    pred__export_llm_enriched_dataset__json,
)
from notarius.orchestration.assets.transform.predict import (
    EnrichWithOCRUsingLLMConfig,
    LLMConfig,
    LMv3Config,
    pred__llm_enriched_dataset__pydantic,
    pred__llm_ocr_enriched_dataset__pydantic,
    pred__lmv3_enriched_dataset__pydantic,
)
from notarius.orchestration.assets.transform.preprocess import (
    PreprocessingConfig,
    preprocessed__hf__dataset,
)
from notarius.orchestration.constants import Environment, JobType
from notarius.orchestration.pipelines.evaluation import (
    ALL_EVALUATION_ASSETS_WITH_CONFIGS,
)
from notarius.shared.logger import get_logger


logger = get_logger(__name__)


def main() -> None:
    article_config = load_article_config()
    model_id = article_config.vision_model.model_id
    schematism_ids = list(article_config.dataset.schematism_ids)
    dagster_config = DagsterConfig()
    client = DagsterGraphQLClient(
        hostname=dagster_config.host,
        port_number=dagster_config.port,
    )

    run_config = dict(ALL_EVALUATION_ASSETS_WITH_CONFIGS)
    run_config.update(
        {
            preprocessed__hf__dataset: {
                "config": PreprocessingConfig(
                    filtered_schematisms=schematism_ids
                ).model_dump()
            },
            raw__pdf__dataset: {"config": PdfToDatasetConfig().model_dump()},
            pred__llm_ocr_enriched_dataset__pydantic: {
                "config": EnrichWithOCRUsingLLMConfig(
                    model_name=model_id,
                    task_name="ocr",
                    enable_cache=True,
                    group_by_schematism_name=True,
                    max_concurrent_async_requests=20,
                ).model_dump()
            },
            pred__lmv3_enriched_dataset__pydantic: {
                "config": LMv3Config(
                    skip=not article_config.layoutlmv3.enabled_for_corpus_evaluation,
                    checkpoint=article_config.layoutlmv3.checkpoint,
                    enable_cache=True,
                ).model_dump()
            },
            pred__llm_enriched_dataset__pydantic: {
                "config": LLMConfig(
                    model_name=model_id,
                    context_strategy=article_config.extraction.context_strategy,
                    context_window_size=article_config.extraction.context_window_size,
                    task_name=article_config.extraction.task_name,
                    enable_cache=True,
                    group_by_schematism_name=True,
                ).model_dump()
            },
            eval__excel_export_parsed_dataframe__pandas: {
                "config": ParsedDataFrameExportConfig(
                    file_name=(
                        f"{parse_model_name(model_id)}_parsed_schematism_comp.xlsx"
                    )
                ).model_dump()
            },
            eval__excel_export_source_dataframe__pandas: {
                "config": SourceDataFrameExportConfig(
                    file_name=(
                        f"{parse_model_name(model_id)}_source_schematism_comp.xlsx"
                    )
                ).model_dump()
            },
            pred__export_llm_enriched_dataset__json: {
                "config": PredsSourceExportConfig(
                    filename_prefix=f"predictions_{parse_model_name(model_id)}"
                ).model_dump()
            },
        }
    )

    run_id = client.submit_job_execution(
        job_name="evaluation_pipeline",
        run_config=dg.RunConfig(
            ops={
                asset.key.to_python_identifier(): config
                for asset, config in run_config.items()
                if config is not None
            },
        ),
        tags={
            "environment": Environment.DEV,
            "task": JobType.EVALUATION,
            "artifact_version": article_config.artifact_version,
            "model": model_id,
            "lmv3_used": article_config.layoutlmv3.enabled_for_corpus_evaluation,
            **{schematism_id: "" for schematism_id in schematism_ids},
        },
    )
    logger.info(
        "Submitted frozen article evaluation",
        run_id=run_id,
        model=model_id,
        schematism_count=len(schematism_ids),
    )


if __name__ == "__main__":
    main()
