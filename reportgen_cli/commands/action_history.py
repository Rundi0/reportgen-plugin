import click

from ..output import emit
from ._helpers import get_client


@click.group("history", help="Audit action history & comments.")
def group() -> None:
    pass


@group.command("list")
@click.argument("audit_id", type=int)
@click.pass_context
def list_(ctx, audit_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/history"))


@group.command("comment")
@click.argument("audit_id", type=int)
@click.argument("description")
@click.pass_context
def comment(ctx, audit_id, description):
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/history/comments",
        json={"description": description},
    ))
