from pathlib import Path
from typing import Annotated

import typer

from notarius.article.config import ARTICLE_CONFIG_PATH
from notarius.article.verification import verify_article_artifact


app = typer.Typer(
    add_completion=False,
    help="Verify the frozen code and configuration used by the article.",
)


@app.callback()
def main() -> None:
    """Inspect and verify the frozen article artifact."""


@app.command()
def verify(
    config: Annotated[
        Path,
        typer.Option(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to the paper artifact configuration.",
        ),
    ] = ARTICLE_CONFIG_PATH,
) -> None:
    """Validate corpus membership, runtime settings, prompts, and mappings."""
    report = verify_article_artifact(config)
    typer.echo(report.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
