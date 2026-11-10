import click

from ..output import emit
from ._helpers import get_client


@click.group("auth", help="Authentication / current user.")
def group() -> None:
    pass


@group.command("whoami", help="Return the user behind the active session.")
@click.pass_context
def whoami(ctx: click.Context) -> None:
    # /api/auth/me returns the user object directly (no {result: ...} wrap).
    emit(get_client(ctx).get("/api/auth/me", unwrap=False))
