import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("instances", help="Per-service vulnerability instances (status=new|approved|false_positive|fixed).")
def group() -> None:
    pass


def _body(body_json, service_id, params, path, scanner, status, comment):
    return merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "serviceId": service_id,
            "params": params,
            "path": path,
            "scanner": scanner,
            "status": status,
            "comment": comment,
        },
    )


@group.command("create")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.option("--body", "body_json")
@click.option("--service-id", type=int)
@click.option("--params")
@click.option("--path")
@click.option("--scanner")
@click.option("--status", type=click.Choice(["new", "approved", "false_positive", "fixed"]))
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def create(ctx, audit_id, vuln_id, body_json, service_id, params, path, scanner, status, comment):
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}/instances",
        json=_body(body_json, service_id, params, path, scanner, status, comment),
    ))


@group.command("update")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.argument("instance_id", type=int)
@click.option("--body", "body_json")
@click.option("--service-id", type=int)
@click.option("--params")
@click.option("--path")
@click.option("--scanner")
@click.option("--status", type=click.Choice(["new", "approved", "false_positive", "fixed"]))
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def update(ctx, audit_id, vuln_id, instance_id, body_json, service_id, params, path, scanner, status, comment):
    emit(get_client(ctx).patch(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}/instances/{instance_id}",
        json=_body(body_json, service_id, params, path, scanner, status, comment),
    ))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.argument("instance_id", type=int)
@click.pass_context
def delete(ctx, audit_id, vuln_id, instance_id):
    get_client(ctx).delete(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}/instances/{instance_id}"
    )
    emit({"deleted": instance_id})


@group.command("bulk-delete")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.argument("ids", nargs=-1, type=int, required=True)
@click.pass_context
def bulk_delete(ctx, audit_id, vuln_id, ids):
    get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}/instances/bulk-delete",
        json={"ids": list(ids)},
    )
    emit({"deleted": list(ids)})


@group.command("bulk-status")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.option("--status", required=True,
              type=click.Choice(["new", "approved", "false_positive", "fixed"]))
@click.argument("ids", nargs=-1, type=int, required=True)
@click.pass_context
def bulk_status(ctx, audit_id, vuln_id, status, ids):
    get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}/instances/bulk-status",
        json={"ids": list(ids), "status": status},
    )
    emit({"updated": list(ids), "status": status})
