import sys
from pathlib import Path

import click
import httpx

from ..output import emit, parse_json_arg
from ._helpers import get_client


@click.group("reports", help="Doc templates, report generation, translations, scan-data import.")
def group() -> None:
    pass


@group.command("list-templates")
@click.pass_context
def list_templates(ctx):
    emit(get_client(ctx).get("/api/doc-templates"))


@group.command("generate", help="Generate a .docx report. Requires session cookie OR public path.")
@click.option("--source",
              type=click.Choice(["internal_db", "pentestadmin_assessor", "pentestadmin_scanner",
                                 "faraday_assessor", "faraday_scanner"]),
              default="internal_db", show_default=True)
@click.option("--workspace-id", type=int, required=True, help="Audit ID for internal_db, workspace ID otherwise")
@click.option("--template-id", type=int, required=True)
@click.option("--file-name", required=True, help="Output file name, e.g. report.docx")
@click.option("--user-name", help="Pentester display name override")
@click.option("--merge-rules", help="JSON array of merge rule overrides (advanced)")
@click.option("--output", "out_path", default=None, help="Save path; defaults to --file-name")
@click.pass_context
def generate(ctx, source, workspace_id, template_id, file_name, user_name, merge_rules, out_path):
    body = {
        "source": source,
        "workspace_id": workspace_id,
        "template_id": template_id,
        "file_name": file_name,
    }
    if user_name:
        body["user_name"] = user_name
    if merge_rules:
        body["merge_rules"] = parse_json_arg(merge_rules, name="--merge-rules")

    data = get_client(ctx).post_raw("/api/generate-report", json=body)
    target = out_path or file_name
    if target == "-":
        sys.stdout.buffer.write(data)
        return
    Path(target).write_bytes(data)
    emit({"saved": target, "bytes": len(data)})


@group.command("check-translations", help="Find vulns lacking translations for the given source.")
@click.option("--source",
              type=click.Choice(["internal_db", "pentestadmin_assessor", "pentestadmin_scanner",
                                 "faraday_assessor", "faraday_scanner"]),
              required=True)
@click.option("--workspace-id", type=int, required=True)
@click.option("--with-cve", is_flag=True, help="Also fetch CVE descriptions from NVD (rate-limited)")
@click.option("--merge-rules", help="JSON array of merge rule overrides")
@click.pass_context
def check_translations(ctx, source, workspace_id, with_cve, merge_rules):
    body = {"source": source, "workspace_id": workspace_id}
    if merge_rules:
        body["merge_rules"] = parse_json_arg(merge_rules, name="--merge-rules")
    emit(get_client(ctx).post(
        "/api/check-translations",
        params={"cve": "true" if with_cve else "false"},
        json=body,
    ))


@group.command("upload-scan-data", help="Upload Acunetix .json or Nessus .nessus/.xml into an audit.")
@click.argument("audit_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def upload_scan_data(ctx, audit_id, file_path):
    p = Path(file_path)
    with p.open("rb") as fh:
        files = {"file": (p.name, fh, "application/octet-stream")}
        client = get_client(ctx)
        client.require_member(audit_id)
        response = client._http.post(
            "/api/upload",
            data={"auditId": str(audit_id)},
            files=files,
        )
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            response.text or response.reason_phrase,
            request=response.request,
            response=response,
        )
    emit({"uploaded": p.name, "auditId": audit_id})
