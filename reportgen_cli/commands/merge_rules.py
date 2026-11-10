import click

from ..output import emit, parse_json_arg
from ._helpers import get_client


@click.group("merge-rules", help="Vulnerability merge rules (deduplication).")
def group() -> None:
    pass


@group.command("list")
@click.pass_context
def list_(ctx):
    emit(get_client(ctx).get("/api/merge-rules"))


@group.command("create")
@click.option("--body", "body_json", required=True, help="Full JSON body")
@click.pass_context
def create(ctx, body_json):
    emit(get_client(ctx).post("/api/merge-rules", json=parse_json_arg(body_json, name="--body")))


@group.command("update")
@click.argument("rule_id", type=int)
@click.option("--body", "body_json", required=True)
@click.pass_context
def update(ctx, rule_id, body_json):
    emit(get_client(ctx).patch(f"/api/merge-rules/{rule_id}", json=parse_json_arg(body_json, name="--body")))


@group.command("delete")
@click.argument("rule_id", type=int)
@click.pass_context
def delete(ctx, rule_id):
    get_client(ctx).delete(f"/api/merge-rules/{rule_id}")
    emit({"deleted": rule_id})
