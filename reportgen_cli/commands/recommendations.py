import json

import click

from ..output import emit
from ._helpers import get_client


@click.group("general-recommendations", help="General recommendations (загальні рекомендації) block of the act.")
def group() -> None:
    pass


def _path(audit_id: int) -> str:
    return f"/api/audits/{audit_id}/recommendations"


@group.command("get")
@click.argument("audit_id", type=int)
@click.pass_context
def get(ctx, audit_id):
    emit(get_client(ctx).get(_path(audit_id)))


@group.command("patch", help="Replace items. FILE: JSON list of strings, or an object with "
                             "'items' (e.g. saved `get` output); '-' reads stdin.")
@click.argument("audit_id", type=int)
@click.argument("file", type=click.File("r", encoding="utf-8"))
@click.pass_context
def patch(ctx, audit_id, file):
    data = json.load(file)
    items = data["items"] if isinstance(data, dict) else data
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise click.UsageError("expected a JSON list of strings or {\"items\": [...]}")
    emit(get_client(ctx).patch(_path(audit_id), json={"items": items}))


@group.command("generate", help="Re-filter template defaults by the audit's vulnerabilities.")
@click.argument("audit_id", type=int)
@click.pass_context
def generate(ctx, audit_id):
    emit(get_client(ctx).post(f"{_path(audit_id)}/generate"))


@group.command("reset", help="Reset items to the full template defaults.")
@click.argument("audit_id", type=int)
@click.pass_context
def reset(ctx, audit_id):
    emit(get_client(ctx).post(f"{_path(audit_id)}/reset"))
