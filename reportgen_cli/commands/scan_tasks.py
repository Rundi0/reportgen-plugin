import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("scan-tasks", help="Background scan tasks (subdomains, port-scan, fingerprint, waf, ...).")
def group() -> None:
    pass


@group.command("list")
@click.argument("audit_id", type=int)
@click.option("--status", help="Filter by status (pending|running|completed|failed|cancelled)")
@click.pass_context
def list_(ctx, audit_id, status):
    params = {"status_filter": status} if status else None
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/scan-tasks", params=params))


@group.command("get")
@click.argument("audit_id", type=int)
@click.argument("task_id", type=int)
@click.pass_context
def get(ctx, audit_id, task_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/scan-tasks/{task_id}"))


@group.command("create", help="Enqueue a scan task. --params expects JSON.")
@click.argument("audit_id", type=int)
@click.option("--scan-type", required=True, help="e.g. discover_services, check_waf, nmap_portscan")
@click.option("--tool", help="Override default tool for the scan type")
@click.option("--params", help='JSON object, e.g. \'{"target":"example.com"}\'')
@click.option("--priority", type=int, default=0, show_default=True)
@click.option("--max-retries", type=int, default=3, show_default=True)
@click.option("--timeout-seconds", type=int, default=3600, show_default=True)
@click.option("--body", "body_json", help="Full JSON body, overrides flags above")
@click.pass_context
def create(ctx, audit_id, scan_type, tool, params, priority, max_retries, timeout_seconds, body_json):
    body = merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "scanType": scan_type,
            "tool": tool,
            "params": parse_json_arg(params, name="--params") or {},
            "priority": priority,
            "maxRetries": max_retries,
            "timeoutSeconds": timeout_seconds,
        },
    )
    emit(get_client(ctx).post(f"/api/audits/{audit_id}/scan-tasks", json=body))


@group.command("cancel")
@click.argument("audit_id", type=int)
@click.argument("task_id", type=int)
@click.pass_context
def cancel(ctx, audit_id, task_id):
    emit(get_client(ctx).post(f"/api/audits/{audit_id}/scan-tasks/{task_id}/cancel"))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.argument("task_id", type=int)
@click.pass_context
def delete(ctx, audit_id, task_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}/scan-tasks/{task_id}")
    emit({"deleted": task_id})
