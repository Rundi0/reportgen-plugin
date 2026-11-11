import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("organizations", help="Organizations CRUD and pentestadmin import.")
def group() -> None:
    pass


@group.command("list")
@click.pass_context
def list_(ctx):
    emit(get_client(ctx).get("/api/organizations"))


@group.command("get")
@click.argument("org_id", type=int)
@click.pass_context
def get(ctx, org_id):
    emit(get_client(ctx).get(f"/api/organizations/{org_id}"))


@group.command("create", help="Create organization. Use --body to pass full JSON.")
@click.option("--body", "body_json", help="Full JSON body, e.g. '{\"name\":\"X\",\"edrpo\":\"123\",\"domains\":[\"a.com\"],\"notes\":null}'")
@click.option("--name")
@click.option("--edrpo")
@click.option("--domains", help="Comma-separated list, e.g. a.com,b.com")
@click.option("--notes")
@click.pass_context
def create(ctx, body_json, name, edrpo, domains, notes):
    body = merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "name": name,
            "edrpo": edrpo,
            "domains": [d.strip() for d in domains.split(",")] if domains else None,
            "notes": notes,
        },
    )
    emit(get_client(ctx).post("/api/organizations", json=body))


@group.command("update")
@click.argument("org_id", type=int)
@click.option("--body", "body_json", required=True, help="JSON body with fields to update")
@click.pass_context
def update(ctx, org_id, body_json):
    body = parse_json_arg(body_json, name="--body")
    emit(get_client(ctx).patch(f"/api/organizations/{org_id}", json=body))


@group.command("workspaces", help="List pentestadmin workspaces for a source.")
@click.option(
    "--source",
    type=click.Choice(["pentestadmin_assessor", "pentestadmin_scanner",
                       "faraday_assessor", "faraday_scanner", "internal_db"]),
    required=True,
)
@click.pass_context
def workspaces(ctx, source):
    emit(get_client(ctx).get("/api/workspaces", params={"source": source}))


@group.command("import-pentestadmin", help="Import org+audit from pentestadmin into internal DB.")
@click.argument("pentestadmin_id", type=int)
@click.option(
    "--source",
    type=click.Choice(["pentestadmin_assessor", "pentestadmin_scanner"]),
    required=True,
)
@click.pass_context
def import_pentestadmin(ctx, pentestadmin_id, source):
    emit(get_client(ctx).post(
        f"/api/organizations/export/pentestadmin/{pentestadmin_id}",
        params={"source": source},
    ))
