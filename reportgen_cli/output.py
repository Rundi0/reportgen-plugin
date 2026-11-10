"""Output formatting — JSON to stdout, errors as JSON to stderr.

The default is compact single-line JSON so AI agents and shell
pipelines (jq, grep) get clean, parseable output. Use --pretty for
human-readable indented JSON.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click


def emit(value: Any) -> None:
    pretty = click.get_current_context().obj.get("pretty", False)
    if value is None:
        if pretty:
            click.echo("null")
        else:
            click.echo("null")
        return
    if pretty:
        click.echo(json.dumps(value, indent=2, ensure_ascii=False, default=str))
    else:
        click.echo(json.dumps(value, ensure_ascii=False, default=str))


def emit_error(message: str, *, status: int | None = None, body: Any = None) -> None:
    payload: dict[str, Any] = {"error": message}
    if status is not None:
        payload["status"] = status
    if body is not None:
        payload["body"] = body
    click.echo(json.dumps(payload, ensure_ascii=False, default=str), err=True)


def parse_json_arg(value: str | None, *, name: str) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(
            f"{name}: invalid JSON ({exc.msg})"
        ) from exc
