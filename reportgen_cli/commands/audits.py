import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("audits", help="Audits: list, create, update.")
def group() -> None:
    pass


def _no_pentesters(body: dict | None) -> dict | None:
    if body and "pentestersIds" in body:
        raise click.UsageError("Assigning pentesters is not available in the CLI; use the web UI.")
    return body


@group.command("list")
@click.pass_context
def list_(ctx):
    emit(get_client(ctx).get("/api/audits"))


@group.command("mine", help="Audits where the current user is one of the pentesters.")
@click.pass_context
def mine(ctx):
    client = get_client(ctx)
    me = client.get("/api/auth/me", unwrap=False)["sub"]
    emit([a for a in client.get("/api/audits") if me in (a.get("pentestersIds") or [])])


@group.command("list-by-org")
@click.argument("org_id", type=int)
@click.pass_context
def list_by_org(ctx, org_id):
    emit(get_client(ctx).get(f"/api/organizations/{org_id}/audits"))


@group.command("get")
@click.argument("audit_id", type=int)
@click.pass_context
def get(ctx, audit_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}"))


@group.command("create", help="Create audit under organization, with you as its pentester.")
@click.argument("org_id", type=int)
@click.option("--body", "body_json", help="Full JSON body")
@click.option("--type", "type_", type=click.Choice(["scan", "assessor"]))
@click.option(
    "--status",
    type=click.Choice(
        ["pending", "scanning", "assessing", "reporting", "rescanning", "drafting", "closed"]
    ),
)
@click.option("--notes")
@click.option("--started-at", help="ISO date, e.g. 2026-01-15")
@click.option("--finished-at", help="ISO date, e.g. 2026-01-20")
@click.option("--quartal-year", type=int)
@click.option("--quartal-number", type=int)
@click.pass_context
def create(ctx, org_id, body_json, type_, status, notes, started_at, finished_at, quartal_year, quartal_number):
    body = merge_body(
        _no_pentesters(parse_json_arg(body_json, name="--body")),
        {
            "type": type_,
            "status": status,
            "notes": notes,
            "startedAt": started_at,
            "finishedAt": finished_at,
            "quartalYear": quartal_year,
            "quartalNumber": quartal_number,
        },
    )
    client = get_client(ctx)
    # The creator is the audit's pentester, so they can keep working on it.
    body["pentestersIds"] = [client.me()]
    emit(client.post(f"/api/organizations/{org_id}/audits", json=body))


@group.command("patch", help="Partial update — only provided fields are changed.")
@click.argument("audit_id", type=int)
@click.option("--body", "body_json", help="Full JSON body")
@click.option("--type", "type_", type=click.Choice(["scan", "assessor"]))
@click.option(
    "--status",
    type=click.Choice(
        ["pending", "scanning", "assessing", "reporting", "rescanning", "drafting", "closed"]
    ),
)
@click.option("--notes")
@click.option("--started-at")
@click.option("--finished-at")
@click.option("--quartal-year", type=int)
@click.option("--quartal-number", type=int)
@click.pass_context
def patch(ctx, audit_id, body_json, type_, status, notes, started_at, finished_at, quartal_year, quartal_number):
    body = merge_body(
        _no_pentesters(parse_json_arg(body_json, name="--body")),
        {
            "type": type_,
            "status": status,
            "notes": notes,
            "startedAt": started_at,
            "finishedAt": finished_at,
            "quartalYear": quartal_year,
            "quartalNumber": quartal_number,
        },
    )
    emit(get_client(ctx).patch(f"/api/audits/{audit_id}", json=body))
