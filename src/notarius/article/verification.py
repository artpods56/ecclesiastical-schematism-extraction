import hashlib
from pathlib import Path
from typing import ClassVar, cast

import yaml
from pydantic import BaseModel, ConfigDict

from notarius.article.config import (
    ARTICLE_CONFIG_PATH,
    PromptConfig,
    load_article_config,
)
from notarius.schemas.configs.llm_model_config import LLMEngineConfig
from notarius.shared.constants import REPOSITORY_ROOT


RUNTIME_LLM_CONFIG_PATH = (
    REPOSITORY_ROOT / "configs" / "ml_models" / "llm" / "llm_model_config.yaml"
)


class ArtifactVerification(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    artifact_version: str
    model_id: str
    temperature: float
    schematism_count: int
    prompt_sha256: dict[str, str]


def verify_article_artifact(
    config_path: Path = ARTICLE_CONFIG_PATH,
) -> ArtifactVerification:
    config = load_article_config(config_path)
    prompt_hashes: dict[str, str] = {}

    prompt_groups: dict[str, PromptConfig] = {
        "ocr": config.ocr.prompt,
        "structured_extraction": config.extraction.prompt,
    }
    for group_name, prompt_config in prompt_groups.items():
        for role, prompt_file in (
            ("system", prompt_config.system),
            ("user", prompt_config.user),
        ):
            prompt_path = REPOSITORY_ROOT / prompt_file.path
            try:
                prompt_bytes = prompt_path.read_bytes()
            except OSError as error:
                raise OSError(
                    f"Unable to read {group_name} {role} prompt at {prompt_path}: {error}"
                ) from error

            actual_hash = hashlib.sha256(prompt_bytes).hexdigest()
            if actual_hash != prompt_file.sha256:
                raise ValueError(
                    f"SHA-256 mismatch for {prompt_path}: expected "
                    + f"{prompt_file.sha256}, got {actual_hash}."
                )

            prompt_text = prompt_bytes.decode("utf-8")
            version_marker = f"<PROMPT_VERSION>{prompt_config.version}</PROMPT_VERSION>"
            if version_marker not in prompt_text:
                raise ValueError(
                    f"Prompt version {prompt_config.version} is not declared in "
                    + f"{prompt_path}."
                )
            prompt_hashes[f"{group_name}.{role}"] = actual_hash

    try:
        runtime_raw_config = cast(
            object,
            yaml.safe_load(RUNTIME_LLM_CONFIG_PATH.read_text(encoding="utf-8")),
        )
    except OSError as error:
        raise OSError(
            f"Unable to read runtime LLM config at {RUNTIME_LLM_CONFIG_PATH}: {error}"
        ) from error
    runtime_config = LLMEngineConfig.model_validate(runtime_raw_config)
    runtime_client = runtime_config.clients[runtime_config.backend.type]

    expected_model = config.vision_model
    runtime_values = (
        runtime_config.backend.type,
        runtime_client.model,
        runtime_client.base_url,
        runtime_client.api_key_env_var,
        runtime_client.params.temperature,
        runtime_client.params.top_p,
        runtime_client.params.max_tokens,
    )
    expected_values = (
        expected_model.provider,
        expected_model.model_id,
        expected_model.base_url,
        expected_model.api_key_environment_variable,
        expected_model.temperature,
        expected_model.top_p,
        expected_model.max_tokens,
    )
    if runtime_values != expected_values:
        raise ValueError(
            "Runtime LLM settings do not match configs/article/paper-v1.yaml. "
            + f"Expected {expected_values}, got {runtime_values}."
        )

    for mapping_path in config.parsing.mapping_files.values():
        absolute_mapping_path = REPOSITORY_ROOT / mapping_path
        if not absolute_mapping_path.is_file():
            raise FileNotFoundError(
                f"Required parsing dictionary is missing: {absolute_mapping_path}"
            )

    return ArtifactVerification(
        artifact_version=config.artifact_version,
        model_id=config.vision_model.model_id,
        temperature=config.vision_model.temperature,
        schematism_count=len(config.dataset.schematism_ids),
        prompt_sha256=prompt_hashes,
    )
