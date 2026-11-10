import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("audits", help="Audit CRUD; clearing scan data.")
def group() -> None:
    pass


@group.command("list")
@click.pass_context
def list_(ctx):
    emit(get_client(ctx).get("/api/audits"))


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


@group.command("create", help="Create audit under organization.")
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
@click.option("--pentesters", help="Comma-separated user IDs (Keycloak sub)")
@click.pass_context
def create(ctx, org_id, body_json, type_, status, notes, started_at, finished_at, quartal_year, quartal_number, pentesters):
    body = merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "type": type_,
            "status": status,
            "notes": notes,
            "startedAt": started_at,
            "finishedAt": finished_at,
            "quartalYear": quartal_year,
            "quartalNumber": quartal_number,
            "pentestersIds": [p.strip() for p in pentesters.split(",")] if pentesters else None,
        },
    )
    emit(get_client(ctx).post(f"/api/organizations/{org_id}/audits", json=body))


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
@click.option("--pentesters", help="Comma-separated user IDs")
@click.pass_context
def patch(ctx, audit_id, body_json, type_, status, notes, started_at, finished_at, quartal_year, quartal_number, pentesters):
    body = merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "type": type_,
            "status": status,
            "notes": notes,
            "startedAt": started_at,
            "finishedAt": finished_at,
            "quartalYear": quartal_year,
            "quartalNumber": quartal_number,
            "pentestersIds": [p.strip() for p in pentesters.split(",")] if pentesters else None,
        },
    )
    emit(get_client(ctx).patch(f"/api/audits/{audit_id}", json=body))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.pass_context
def delete(ctx, audit_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}")
    emit({"deleted": audit_id})


@group.command("clear-scan-data", help="Wipe hosts, services, vulnerabilities for the audit.")
@click.argument("audit_id", type=int)
@click.confirmation_option(prompt="This deletes all scan data for the audit. Continue?")
@click.pass_context
def clear_scan_data(ctx, audit_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}/scan-data")
    emit({"cleared": audit_id})
