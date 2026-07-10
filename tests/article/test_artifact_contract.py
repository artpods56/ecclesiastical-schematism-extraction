from notarius.article import load_article_config, verify_article_artifact
from notarius.application.services.message_builder import Jinja2MessageBuilder
from notarius.application.services.context.strategy import (
    SlidingWindowStrategy,
    get_context_strategy,
)
from notarius.infrastructure.llm.prompt_manager import Jinja2PromptRenderer


def test_frozen_article_artifact_is_internally_consistent() -> None:
    report = verify_article_artifact()

    assert report.artifact_version == "1.0.0"
    assert report.model_id == "google/gemini-3-flash-preview"
    assert report.temperature == 0.1
    assert report.schematism_count == 42
    assert set(report.prompt_sha256) == {
        "ocr.system",
        "ocr.user",
        "structured_extraction.system",
        "structured_extraction.user",
    }


def test_article_corpus_excludes_the_separate_1529_source() -> None:
    config = load_article_config()

    assert len(config.dataset.schematism_ids) == 42
    assert "liber_crac_1529" not in config.dataset.schematism_ids


def test_configured_sliding_window_reaches_runtime_strategy() -> None:
    config = load_article_config()
    message_builder = Jinja2MessageBuilder(
        task_name=config.extraction.task_name,
        prompt_renderer=Jinja2PromptRenderer(template_dir="prompts"),
    )

    strategy = get_context_strategy(
        strategy_literal=config.extraction.context_strategy,
        message_builder=message_builder,
        sliding_window_size=config.extraction.context_window_size,
    )

    assert isinstance(strategy, SlidingWindowStrategy)
    assert strategy.window_size == 5
