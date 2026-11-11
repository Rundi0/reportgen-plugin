import sys
from pathlib import Path

import click
import httpx

from ..output import emit
from ._helpers import get_client


@click.group("files", help="Attachments for organizations, audits, vulnerabilities.")
def group() -> None:
    pass


@group.command("list-org")
@click.argument("org_id", type=int)
@click.pass_context
def list_org(ctx, org_id):
    emit(get_client(ctx).get(f"/api/organizations/{org_id}/files"))


@group.command("list-audit")
@click.argument("audit_id", type=int)
@click.pass_context
def list_audit(ctx, audit_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/files"))


@group.command("list-vuln")
@click.argument("vuln_id", type=int)
@click.pass_context
def list_vuln(ctx, vuln_id):
    emit(get_client(ctx).get(f"/api/vulnerabilities/{vuln_id}/files"))


def _upload(ctx, url: str, path: str):
    p = Path(path)
    if not p.is_file():
        raise click.UsageError(f"File not found: {path}")
    with p.open("rb") as fh:
        files = {"file": (p.name, fh, "application/octet-stream")}
        # http client supports the files= kwarg via _request
        client = get_client(ctx)
        response = client._http.post(url, files=files)
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            response.text or response.reason_phrase,
            request=response.request,
            response=response,
        )
    body = response.json() if response.content else None
    if isinstance(body, dict) and "result" in body:
        body = body["result"]
    emit(body)


@group.command("upload-org")
@click.argument("org_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def upload_org(ctx, org_id, file_path):
    _upload(ctx, f"/api/organizations/{org_id}/files", file_path)


@group.command("upload-audit")
@click.argument("audit_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def upload_audit(ctx, audit_id, file_path):
    get_client(ctx).require_member(audit_id)
    _upload(ctx, f"/api/audits/{audit_id}/files", file_path)


@group.command("upload-vuln")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def upload_vuln(ctx, audit_id, vuln_id, file_path):
    client = get_client(ctx)
    client.require_member(audit_id)
    if client.get(f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}")["auditId"] != audit_id:
        raise click.UsageError(f"Vulnerability {vuln_id} is not in audit {audit_id}")
    _upload(ctx, f"/api/vulnerabilities/{vuln_id}/files", file_path)


@group.command("download")
@click.argument("file_id", type=int)
@click.option("--output", "out_path", default="-", help="Save path or '-' for stdout")
@click.pass_context
def download(ctx, file_id, out_path):
    data = get_client(ctx).download(f"/api/files/{file_id}")
    if out_path == "-":
        sys.stdout.buffer.write(data)
    else:
        Path(out_path).write_bytes(data)
        emit({"saved": out_path, "bytes": len(data)})
