import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("hosts", help="Hosts within an audit.")
def group() -> None:
    pass


@group.command("list")
@click.argument("audit_id", type=int)
@click.pass_context
def list_(ctx, audit_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/hosts"))


@group.command("get")
@click.argument("audit_id", type=int)
@click.argument("host_id", type=int)
@click.pass_context
def get(ctx, audit_id, host_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/hosts/{host_id}"))


@group.command("create")
@click.argument("audit_id", type=int)
@click.option("--body", "body_json")
@click.option("--ip")
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def create(ctx, audit_id, body_json, ip, comment):
    body = merge_body(parse_json_arg(body_json, name="--body"), {"ip": ip, "comment": comment})
    emit(get_client(ctx).post(f"/api/audits/{audit_id}/hosts", json=body))


@group.command("update")
@click.argument("audit_id", type=int)
@click.argument("host_id", type=int)
@click.option("--body", "body_json")
@click.option("--ip")
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def update(ctx, audit_id, host_id, body_json, ip, comment):
    body = merge_body(parse_json_arg(body_json, name="--body"), {"ip": ip, "comment": comment})
    emit(get_client(ctx).patch(f"/api/audits/{audit_id}/hosts/{host_id}", json=body))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.argument("host_id", type=int)
@click.pass_context
def delete(ctx, audit_id, host_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}/hosts/{host_id}")
    emit({"deleted": host_id})


@group.command("refresh-countries", help="Re-resolve country via GeoIP for given host IDs.")
@click.argument("audit_id", type=int)
@click.argument("host_ids", nargs=-1, type=int, required=True)
@click.pass_context
def refresh_countries(ctx, audit_id, host_ids):
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/hosts/refresh-countries",
        json={"hostIds": list(host_ids)},
    ))
