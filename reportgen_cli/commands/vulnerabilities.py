import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


def _resolve_prompt(text: str | None, path: str | None, label: str) -> dict | None:
    """Build a prompt-override dict from --text/--file options.

    Mutually exclusive: passing both --text and --file raises.
    Returns None when neither produces non-empty content (server uses default).
    """
    if text is not None and path is not None:
        raise click.UsageError(f"--{label}-prompt and --{label}-prompt-file are mutually exclusive")
    body: str | None = text
    if path is not None:
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
    content = (body or "").strip()
    if not content:
        return None
    return {"text": content}


@click.group("vulnerabilities", help="Audit-scoped vulnerabilities (severity 1=Info..5=Critical).")
def group() -> None:
    pass


@group.command("list")
@click.argument("audit_id", type=int)
@click.pass_context
def list_(ctx, audit_id):
    vulns = get_client(ctx).get(f"/api/audits/{audit_id}/vulnerabilities")
    children_by_parent: dict[int, list] = {}
    top_level = []
    for v in vulns:
        pid = v.get("parentVulnerabilityId")
        if pid is not None:
            children_by_parent.setdefault(pid, []).append(v)
        else:
            top_level.append(v)
    for v in top_level:
        kids = children_by_parent.get(v["id"])
        if kids:
            v["children"] = kids
    emit(top_level)


@group.command("get")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.pass_context
def get(ctx, audit_id, vuln_id):
    emit(get_client(ctx).get(f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}"))


def _body(body_json, name, severity, description, resolution, cve, proofs):
    return merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "name": name,
            "severity": severity,
            "description": description,
            "resolution": resolution,
            "cve": [c.strip() for c in cve.split(",")] if cve else None,
            "proofs": proofs,
        },
    )


@group.command("create")
@click.argument("audit_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--severity", type=click.IntRange(1, 5))
@click.option("--description")
@click.option("--resolution")
@click.option("--cve", help="Comma-separated CVE list, e.g. CVE-2024-1,CVE-2024-2")
@click.option("--proofs")
@click.pass_context
def create(ctx, audit_id, body_json, name, severity, description, resolution, cve, proofs):
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities",
        json=_body(body_json, name, severity, description, resolution, cve, proofs),
    ))


@group.command("update")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--severity", type=click.IntRange(1, 5))
@click.option("--description")
@click.option("--resolution")
@click.option("--cve")
@click.option("--proofs")
@click.pass_context
def update(ctx, audit_id, vuln_id, body_json, name, severity, description, resolution, cve, proofs):
    emit(get_client(ctx).patch(
        f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}",
        json=_body(body_json, name, severity, description, resolution, cve, proofs),
    ))


@group.command("delete")
@click.argument("audit_id", type=int)
@click.argument("vuln_id", type=int)
@click.pass_context
def delete(ctx, audit_id, vuln_id):
    get_client(ctx).delete(f"/api/audits/{audit_id}/vulnerabilities/{vuln_id}")
    emit({"deleted": vuln_id})


@group.command("bulk-delete")
@click.argument("audit_id", type=int)
@click.argument("ids", nargs=-1, type=int, required=True)
@click.pass_context
def bulk_delete(ctx, audit_id, ids):
    get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/bulk-delete",
        json={"ids": list(ids)},
    )
    emit({"deleted": list(ids)})


@group.command("merge", help="Group CHILD_IDS under PARENT_ID (single-level only).")
@click.argument("audit_id", type=int)
@click.argument("parent_id", type=int)
@click.argument("child_ids", nargs=-1, type=int, required=True)
@click.pass_context
def merge(ctx, audit_id, parent_id, child_ids):
    get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/bulk-merge",
        json={"parentId": parent_id, "childIds": list(child_ids)},
    )
    emit({"parent_id": parent_id, "child_ids": list(child_ids)})


@group.command("unmerge", help="Detach the given vulnerabilities from their parent.")
@click.argument("audit_id", type=int)
@click.argument("ids", nargs=-1, type=int, required=True)
@click.pass_context
def unmerge(ctx, audit_id, ids):
    get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/bulk-unmerge",
        json={"ids": list(ids)},
    )
    emit({"unmerged": list(ids)})


@group.command(
    "ai-suggest-merges",
    help="Ask the AI to suggest duplicate groups across given vulnerability IDs.",
)
@click.argument("audit_id", type=int)
@click.argument("vuln_ids", nargs=-1, type=int, required=True)
@click.option("--grouping-prompt", "grouping_prompt", default=None,
              help="Per-run grouping prompt text (replaces the built-in default).")
@click.option("--grouping-prompt-file", "grouping_prompt_file", default=None,
              type=click.Path(dir_okay=False, exists=True),
              help="Path to a file with the grouping prompt text.")
@click.pass_context
def ai_suggest_merges(ctx, audit_id, vuln_ids, grouping_prompt, grouping_prompt_file):
    body: dict = {"vulnerabilityIds": list(vuln_ids)}
    override = _resolve_prompt(grouping_prompt, grouping_prompt_file, "grouping")
    if override is not None:
        body["groupingPrompt"] = override
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/ai-suggest-merges",
        json=body,
    ))


@group.command(
    "ai-suggest-group-details",
    help="Ask the AI to synthesise description/resolution/severity for one merge group.",
)
@click.argument("audit_id", type=int)
@click.argument("name")
@click.argument("vuln_ids", nargs=-1, type=int, required=True)
@click.option("--details-prompt", "details_prompt", default=None,
              help="Per-run details prompt text (replaces the built-in default).")
@click.option("--details-prompt-file", "details_prompt_file", default=None,
              type=click.Path(dir_okay=False, exists=True),
              help="Path to a file with the details prompt text.")
@click.pass_context
def ai_suggest_group_details(ctx, audit_id, name, vuln_ids, details_prompt, details_prompt_file):
    body: dict = {"name": name, "vulnerabilityIds": list(vuln_ids)}
    override = _resolve_prompt(details_prompt, details_prompt_file, "details")
    if override is not None:
        body["detailsPrompt"] = override
    emit(get_client(ctx).post(
        f"/api/audits/{audit_id}/vulnerabilities/ai-suggest-group-details",
        json=body,
    ))
