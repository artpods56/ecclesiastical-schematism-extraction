from pathlib import Path
from typing import ClassVar, Literal, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from notarius.shared.constants import REPOSITORY_ROOT


ARTICLE_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "article" / "paper-v1.yaml"


class FrozenConfigModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class DatasetConfig(FrozenConfigModel):
    repository: Literal["artpods56/KUL_IDUB_EcclessiaSchematisms"]
    configuration: Literal["default"]
    split: Literal["train"]
    schematism_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_article_corpus(self) -> Self:
        if len(self.schematism_ids) != 42:
            raise ValueError(
                "The paper corpus must contain exactly 42 diocesan schematisms."
            )
        if len(set(self.schematism_ids)) != len(self.schematism_ids):
            raise ValueError("The paper corpus contains duplicate identifiers.")
        if "liber_crac_1529" in self.schematism_ids:
            raise ValueError(
                "liber_crac_1529 is a separate source type and is not part of the "
                + "42-schematism corpus."
            )
        return self


class VisionModelConfig(FrozenConfigModel):
    provider: Literal["openrouter"]
    model_id: Literal["google/gemini-3-flash-preview"]
    base_url: Literal["https://openrouter.ai/api/v1"]
    api_key_environment_variable: Literal["OPENROUTER_API_KEY"]
    temperature: float = Field(ge=0.0, le=2.0)
    top_p: float = Field(ge=0.0, le=1.0)
    max_tokens: Literal[4096]

    @model_validator(mode="after")
    def validate_generation_parameters(self) -> Self:
        if self.temperature != 0.1 or self.top_p != 0.9:
            raise ValueError("The paper model requires temperature=0.1 and top_p=0.9.")
        return self


class PromptFileConfig(FrozenConfigModel):
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PromptConfig(FrozenConfigModel):
    version: str
    system: PromptFileConfig
    user: PromptFileConfig


class OCRConfig(FrozenConfigModel):
    vision_markdown_enabled: Literal[True]
    tesseract_languages: Literal["lat+pol+rus"]
    tesseract_role: Literal["word_coordinates_for_layoutlmv3"]
    prompt: PromptConfig


class LayoutLMv3Config(FrozenConfigModel):
    checkpoint: Literal["layoutlmv3_focalloss_4000"]
    enabled_for_corpus_evaluation: Literal[False]
    role: Literal["optional_untrusted_hints"]


class ExtractionConfig(FrozenConfigModel):
    task_name: Literal["structured_extraction"]
    context_strategy: Literal["sliding_window"]
    context_window_size: Literal[5]
    pass_previous_page_context: Literal[True]
    pass_next_page_ocr: Literal[True]
    strip_images_from_retained_history: Literal[True]
    strip_next_page_ocr_from_retained_history: Literal[True]
    prompt: PromptConfig


class ParsingConfig(FrozenConfigModel):
    enabled: Literal[True]
    mapping_files: dict[Literal["building_material", "dedication", "deanery"], Path]


class AlignmentConfig(FrozenConfigModel):
    algorithm: Literal["hungarian"]
    threshold: float = Field(ge=0.0, le=1.0)
    weights: dict[
        Literal["deanery", "parish", "dedication", "building_material"], float
    ]

    @model_validator(mode="after")
    def validate_field_weights(self) -> Self:
        if self.threshold != 0.5:
            raise ValueError("The paper alignment threshold must be 0.5.")
        expected_fields = {"deanery", "parish", "dedication", "building_material"}
        if set(self.weights) != expected_fields:
            raise ValueError(
                "Alignment weights must cover exactly the four extracted entry fields."
            )
        if any(weight <= 0 for weight in self.weights.values()):
            raise ValueError("Alignment weights must be positive.")
        return self


class EvaluationConfig(FrozenConfigModel):
    fields: tuple[
        Literal[
            "page_number",
            "deanery",
            "parish",
            "dedication",
            "building_material",
        ],
        ...,
    ]
    source_form_scorer: Literal["normalized_levenshtein"]
    parsed_form_scorer: Literal["exact_match"]
    parsed_match_threshold: float = Field(ge=0.0, le=1.0)
    random_seed: Literal[42]

    @model_validator(mode="after")
    def validate_parsed_match_threshold(self) -> Self:
        if self.parsed_match_threshold != 1.0:
            raise ValueError("The parsed-form match threshold must be 1.0.")
        return self


class ArticleArtifactConfig(FrozenConfigModel):
    artifact_version: Literal["1.0.0"]
    article_title: Literal[
        "The Use of Advanced Digital Tools in Documentary Work on the Historical Geography of the Church"
    ]
    dataset: DatasetConfig
    vision_model: VisionModelConfig
    ocr: OCRConfig
    layoutlmv3: LayoutLMv3Config
    extraction: ExtractionConfig
    parsing: ParsingConfig
    alignment: AlignmentConfig
    evaluation: EvaluationConfig


def load_article_config(path: Path = ARTICLE_CONFIG_PATH) -> ArticleArtifactConfig:
    try:
        raw_config = cast(
            object,
            yaml.safe_load(path.read_text(encoding="utf-8")),
        )
    except OSError as error:
        raise OSError(f"Unable to read article config at {path}: {error}") from error
    return ArticleArtifactConfig.model_validate(raw_config)
