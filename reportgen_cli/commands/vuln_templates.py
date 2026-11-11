import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("vuln-templates", help="Reusable vulnerability translation templates.")
def group() -> None:
    pass


@group.command("list")
@click.option("-q", "--query", help="Substring filter on name")
@click.pass_context
def list_(ctx, query):
    params = {"q": query} if query else None
    emit(get_client(ctx).get("/api/vuln-templates", params=params))


@group.command("list-names")
@click.pass_context
def list_names(ctx):
    emit(get_client(ctx).get("/api/vuln-templates/names"))


@group.command("get")
@click.argument("template_id", type=int)
@click.pass_context
def get(ctx, template_id):
    emit(get_client(ctx).get(f"/api/vuln-templates/{template_id}"))


@group.command("by-name")
@click.argument("name")
@click.pass_context
def by_name(ctx, name):
    emit(get_client(ctx).get("/api/vuln-templates/by-name", params={"name": name}))


def _body(body_json, name, severity, description, resolution):
    return merge_body(
        parse_json_arg(body_json, name="--body"),
        {
            "name": name,
            "severity": severity,
            "description": description,
            "resolution": resolution,
        },
    )


@group.command("create")
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--severity", type=click.IntRange(1, 5))
@click.option("--description")
@click.option("--resolution")
@click.pass_context
def create(ctx, body_json, name, severity, description, resolution):
    emit(get_client(ctx).post(
        "/api/vuln-templates/create",
        json=_body(body_json, name, severity, description, resolution),
    ))


@group.command("update")
@click.argument("template_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--severity", type=click.IntRange(1, 5))
@click.option("--description")
@click.option("--resolution")
@click.pass_context
def update(ctx, template_id, body_json, name, severity, description, resolution):
    emit(get_client(ctx).patch(
        f"/api/vuln-templates/{template_id}",
        json=_body(body_json, name, severity, description, resolution),
    ))


@group.command("save", help="Upsert by name (POST /api/vuln-templates).")
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--severity", type=click.IntRange(1, 5))
@click.option("--description")
@click.option("--resolution")
@click.pass_context
def save(ctx, body_json, name, severity, description, resolution):
    get_client(ctx).post(
        "/api/vuln-templates",
        json=_body(body_json, name, severity, description, resolution),
    )
    emit({"saved": True})


@group.command("translate", help="Translate template via AI service (openai|ollama).")
@click.option("--service", type=click.Choice(["openai", "ollama"]), default="openai")
@click.option("--body", "body_json", required=True,
              help="JSON {name, severity, description, resolution, cve?}")
@click.pass_context
def translate(ctx, service, body_json):
    body = parse_json_arg(body_json, name="--body")
    emit(get_client(ctx).post("/api/translate", params={"service": service}, json=body))
