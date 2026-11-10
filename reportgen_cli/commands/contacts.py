import click

from ..output import emit, parse_json_arg
from ._helpers import get_client, merge_body


@click.group("contacts", help="Organization contacts.")
def group() -> None:
    pass


@group.command("list")
@click.argument("org_id", type=int)
@click.pass_context
def list_(ctx, org_id):
    emit(get_client(ctx).get(f"/api/organizations/{org_id}/contacts"))


@group.command("get")
@click.argument("org_id", type=int)
@click.argument("contact_id", type=int)
@click.pass_context
def get(ctx, org_id, contact_id):
    emit(get_client(ctx).get(f"/api/organizations/{org_id}/contacts/{contact_id}"))


def _body(body_json, name, email, phone, position):
    return merge_body(
        parse_json_arg(body_json, name="--body"),
        {"name": name, "email": email, "phone": phone, "position": position},
    )


@group.command("create")
@click.argument("org_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--email")
@click.option("--phone")
@click.option("--position")
@click.pass_context
def create(ctx, org_id, body_json, name, email, phone, position):
    emit(get_client(ctx).post(
        f"/api/organizations/{org_id}/contacts",
        json=_body(body_json, name, email, phone, position),
    ))


@group.command("update")
@click.argument("org_id", type=int)
@click.argument("contact_id", type=int)
@click.option("--body", "body_json")
@click.option("--name")
@click.option("--email")
@click.option("--phone")
@click.option("--position")
@click.pass_context
def update(ctx, org_id, contact_id, body_json, name, email, phone, position):
    emit(get_client(ctx).patch(
        f"/api/organizations/{org_id}/contacts/{contact_id}",
        json=_body(body_json, name, email, phone, position),
    ))


@group.command("delete")
@click.argument("org_id", type=int)
@click.argument("contact_id", type=int)
@click.pass_context
def delete(ctx, org_id, contact_id):
    get_client(ctx).delete(f"/api/organizations/{org_id}/contacts/{contact_id}")
    emit({"deleted": contact_id})
