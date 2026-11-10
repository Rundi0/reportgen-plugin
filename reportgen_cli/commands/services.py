import sys

import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("services", help="Services within an audit; host links; export.")
def group() -> None:
    pass


@group.command("list")
@click.argument("audit_id", type=int)
@click.pass_context
def list_(ctx, audit_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/services"))


@group.command("get")
@click.argument("audit_id", type=int)
@click.argument("service_id", type=int)
@click.pass_context
def get(ctx, audit_id, service_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/services/{service_id}"))


def _body(body_json, name, version, banner, protocol, type_, domain, tech_stack, comment):
    return merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "name": name,
            "version": version,
            "banner": banner,
            "protocol": protocol,
            "type": type_,
            "domain": domain,
            "techStack": [t.strip() for t in tech_stack.split(",")] if tech_stack else None,
            "comment": comment,
        },
    )


@group.command("create")
@click.argument("audit_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--version")
@click.option("--banner")
@click.option("--protocol")
@click.option("--type", "type_")
@click.option("--domain")
@click.option("--tech-stack", help="Comma-separated, e.g. nginx,php")
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def create(ctx, audit_id, body_json, name, version, banner, protocol, type_, domain, tech_stack, comment):
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/services",
        json=_body(body_json, name, version, banner, protocol, type_, domain, tech_stack, comment),
    ))


@group.command("update")
@click.argument("audit_id", type=int)
@click.argument("service_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--version")
@click.option("--banner")
@click.option("--protocol")
@click.option("--type", "type_")
@click.option("--domain")
@click.option("--tech-stack")
@click.option("--comment", help="Free-form note for human readers.")
@click.pass_context
def update(ctx, audit_id, service_id, body_json, name, version, banner, protocol, type_, domain, tech_stack, comment):
    emit(get_client(ctx).patch(
        f"/api/audits/{audit_id}/services/{service_id}",
        json=_body(body_json, name, version, banner, protocol, type_, domain, tech_stack, comment),
    ))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.argument("service_id", type=int)
@click.pass_context
def delete(ctx, audit_id, service_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}/services/{service_id}")
    emit({"deleted": service_id})


@group.command("link-host", help="Link host to service with the given port. Pass --waf to upsert WAF on the link.")
@click.argument("audit_id", type=int)
@click.argument("service_id", type=int)
@click.argument("host_id", type=int)
@click.option("--port", required=True)
@click.option("--waf", default=None, help="Optional WAF label (upserts on existing link).")
@click.pass_context
def link_host(ctx, audit_id, service_id, host_id, port, waf):
    params = {"port": port}
    if waf is not None:
        params["waf"] = waf
    get_client(ctx).post(
        f"/api/audits/{audit_id}/services/{service_id}/hosts/{host_id}",
        params=params,
    )
    emit({"linked": {"serviceId": service_id, "hostId": host_id, "port": port, "waf": waf}})


@group.command("unlink-host")
@click.argument("audit_id", type=int)
@click.argument("service_id", type=int)
@click.argument("host_id", type=int)
@click.pass_context
def unlink_host(ctx, audit_id, service_id, host_id):
    get_client(ctx).delete(
        f"/api/audits/{audit_id}/services/{service_id}/hosts/{host_id}"
    )
    emit({"unlinked": {"serviceId": service_id, "hostId": host_id}})


@group.command("backfill-hosts", help="Auto-link hosts to services where ip == domain.")
@click.argument("audit_id", type=int)
@click.pass_context
def backfill_hosts(ctx, audit_id):
    emit(get_client(ctx).post(f"/api/audits/{audit_id}/services/backfill-hosts"))


@group.command("export-acunetix", help="Download Acunetix targets CSV. Use --output - for stdout.")
@click.argument("audit_id", type=int)
@click.option("--output", "out_path", default="-", help="File path or '-' for stdout")
@click.option("--service-ids", default=None, help="Comma-separated service ids; default is the whole audit")
@click.pass_context
def export_acunetix(ctx, audit_id, out_path, service_ids):
    path = f"/api/audits/{audit_id}/services/export-acunetix"
    if service_ids:
        query = "&".join(
            f"service_ids={int(sid)}"
            for sid in service_ids.split(",")
            if sid.strip()
        )
        if query:
            path = f"{path}?{query}"
    data = get_client(ctx).download(path)
    if out_path == "-":
        sys.stdout.buffer.write(data)
    else:
        with open(out_path, "wb") as fh:
            fh.write(data)
        emit({"saved": out_path, "bytes": len(data)})
