"""Shared command-side helpers."""

from __future__ import annotations

from typing import Any

import click

from ..client import ApiClient
from ..config import Config
from ..output import emit_error


def get_client(ctx: click.Context) -> ApiClient:
    """Build the API client on first use; reuse on subsequent calls.

    Resolving the config lazily lets `--help` on subcommands work
    without REPORTGEN_URL / REPORTGEN_SESSION_ID being set.
    """
    client = ctx.obj.get("client")
    if client is not None:
        return client
    import sys

    try:
        config = Config.resolve(
            url=ctx.obj.get("_url"),
            session_id=ctx.obj.get("_session_id"),
            api_key=ctx.obj.get("_api_key"),
            verify_tls=not ctx.obj.get("_insecure", False),
            timeout=ctx.obj.get("_timeout", 30.0),
        )
    except RuntimeError as exc:
        emit_error(str(exc))
        sys.exit(2)
    client = ApiClient(config)
    ctx.obj["client"] = client
    return client


def merge_body(
    body_json: dict | None,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Combine --body JSON with explicit-field flags.

    Explicit flags take precedence over keys from --body. None values
    in overrides are dropped so unset flags do not nullify body keys.
    """
    base: dict[str, Any] = dict(body_json or {})
    for key, value in overrides.items():
        if value is not None:
            base[key] = value
    return base
