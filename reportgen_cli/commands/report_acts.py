import click

from ..output import emit
from ._helpers import get_client


def _resolve_prompt(text: str | None, path: str | None) -> dict | None:
    """Build a prompt-override dict from --prompt/--prompt-file options.

    Mutually exclusive: passing both raises. Returns None when neither
    produces non-empty content (server uses the built-in default).
    """
    if text is not None and path is not None:
        raise click.UsageError("--prompt and --prompt-file are mutually exclusive")
    body: str | None = text
    if path is not None:
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
    content = (body or "").strip()
    if not content:
        return None
    return {"text": content}


@click.group("report-acts", help="Per-audit act drafting (notes → AI act markdown).")
def group() -> None:
    pass


@group.command("get")
@click.argument("audit_id", type=int)
@click.pass_context
def get(ctx, audit_id):
    """Fetch the act for an audit (creates an empty row on first access)."""
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/act"))


@group.command("set-notes")
@click.argument("audit_id", type=int)
@click.option("--text", "text", default=None, help="Notes markdown text.")
@click.option("--file", "path", default=None,
              type=click.Path(dir_okay=False, exists=True),
              help="Path to a file with the notes markdown.")
@click.pass_context
def set_notes(ctx, audit_id, text, path):
    """Replace the engineer's notes markdown for an audit."""
    if text is not None and path is not None:
        raise click.UsageError("--text and --file are mutually exclusive")
    if path is not None:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    if text is None:
        raise click.UsageError("Provide --text or --file")
    emit(get_client(ctx).patch(
        f"/api/audits/{audit_id}/act",
        json={"notesMd": text},
    ))


@group.command("set-act")
@click.argument("audit_id", type=int)
@click.option("--text", "text", default=None, help="Act markdown text.")
@click.option("--file", "path", default=None,
              type=click.Path(dir_okay=False, exists=True),
              help="Path to a file with the act markdown.")
@click.pass_context
def set_act(ctx, audit_id, text, path):
    """Replace the (human-editable) act markdown for an audit."""
    if text is not None and path is not None:
        raise click.UsageError("--text and --file are mutually exclusive")
    if path is not None:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    if text is None:
        raise click.UsageError("Provide --text or --file")
    emit(get_client(ctx).patch(
        f"/api/audits/{audit_id}/act",
        json={"actMd": text},
    ))


@group.command("split", help="Split the stored notes into a sectioning plan (no drafting).")
@click.argument("audit_id", type=int)
@click.pass_context
def split(ctx, audit_id):
    """Plan the act outline from the notes without drafting the act text."""
    emit(get_client(ctx).post(f"/api/audits/{audit_id}/act/sections", json=None))


@group.command("generate", help="Generate the act markdown from the stored notes.")
@click.argument("audit_id", type=int)
@click.option("--prompt", "prompt", default=None,
              help="Per-run prompt text (replaces the built-in default).")
@click.option("--prompt-file", "prompt_file", default=None,
              type=click.Path(dir_okay=False, exists=True),
              help="Path to a file with the prompt text.")
@click.pass_context
def generate(ctx, audit_id, prompt, prompt_file):
    body: dict = {}
    override = _resolve_prompt(prompt, prompt_file)
    if override is not None:
        body["prompt"] = override
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/act/generate",
        json=body or None,
    ))
