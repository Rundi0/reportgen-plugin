import click

from ..output import emit
from ._helpers import get_client


@click.group("users", help="Keycloak users (read-only).")
def group() -> None:
    pass


@group.command("list")
@click.pass_context
def list_(ctx):
    emit(get_client(ctx).get("/api/users"))
