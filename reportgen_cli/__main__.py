"""CLI entry point — wires global options and registers command groups.

Run as: python -m reportgen_cli ... or, after install, reportgen ...

Connection comes from --url plus either --api-key or --session-id (or
env REPORTGEN_URL / REPORTGEN_API_KEY / REPORTGEN_SESSION_ID). Output is
JSON on stdout; errors are JSON on stderr with a non-zero exit code.
"""

from __future__ import annotations

import os
import sys

import click
import httpx
from dotenv import load_dotenv

from .client import ApiError
from .commands import (
    action_history,
    attachments,
    audits,
    auth,
    contacts,
    hosts,
    instances,
    merge_rules,
    organizations,
    report_acts,
    recommendations,
    reports,
    scan_tasks,
    services,
    users,
    vuln_templates,
    vulnerabilities,
)
from .config import Config
from .output import emit_error


def _load_env_file(path: str | None) -> None:
    """Load a .env file into os.environ.

    If --env-file is given, that file is loaded (and is required to
    exist). Otherwise we try, in order: $REPORTGEN_ENV_FILE; a .env in
    the current working directory; a .env walking up parents from cwd.
    Existing env vars are NOT overwritten so an explicit shell export
    still wins.
    """
    if path:
        if not os.path.isfile(path):
            raise click.BadParameter(
                f"env file not found: {path}", param_hint="--env-file"
            )
        load_dotenv(path, override=False)
        return

    explicit = os.environ.get("REPORTGEN_ENV_FILE")
    if explicit and os.path.isfile(explicit):
        load_dotenv(explicit, override=False)
        return

    # Walks parents from cwd; silently no-op if nothing is found.
    load_dotenv(override=False)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "AI-friendly CLI for the Report Generator backend.\n\n"
        "Authentication: pass --url plus --api-key (recommended for "
        "scripting; does not expire) or --session-id, or set the env vars "
        "REPORTGEN_URL and REPORTGEN_API_KEY / REPORTGEN_SESSION_ID (a .env "
        "file in the current directory or any parent is loaded "
        "automatically; use --env-file to point at a specific one).\n\n"
        "Output: JSON to stdout (compact by default, --pretty for "
        "indented). Errors are JSON to stderr with a non-zero exit."
    ),
)
@click.option("--env-file", "env_file", default=None, type=click.Path(dir_okay=False),
              help="Path to a .env file. If omitted, .env is auto-discovered from cwd upward.")
@click.option("--url", default=None, help="Backend base URL, e.g. https://reports.example.com")
@click.option("--api-key", "api_key", default=None,
              help="API key for programmatic access (or REPORTGEN_API_KEY).")
@click.option("--session-id", default=None, help="Session cookie value from /api/auth/login")
@click.option("--insecure", is_flag=True, help="Skip TLS certificate verification")
@click.option("--timeout", default=30.0, show_default=True, help="HTTP timeout in seconds")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output")
@click.pass_context
def cli(
    ctx: click.Context,
    env_file: str | None,
    url: str | None,
    api_key: str | None,
    session_id: str | None,
    insecure: bool,
    timeout: float,
    pretty: bool,
) -> None:
    _load_env_file(env_file)

    # Lazy: store raw config; the actual ApiClient is built when a
    # subcommand first accesses get_client(ctx). This way --help on
    # subcommands works without REPORTGEN_URL/SESSION_ID being set.
    ctx.obj = {
        "_url": url,
        "_api_key": api_key,
        "_session_id": session_id,
        "_insecure": insecure,
        "_timeout": timeout,
        "pretty": pretty,
        "client": None,
    }
    ctx.call_on_close(_close_client(ctx))


def _close_client(ctx: click.Context):
    def close():
        client = ctx.obj.get("client") if ctx.obj else None
        if client is not None:
            client.close()
    return close


cli.add_command(auth.group)
cli.add_command(organizations.group)
cli.add_command(audits.group)
cli.add_command(contacts.group)
cli.add_command(hosts.group)
cli.add_command(services.group)
cli.add_command(vulnerabilities.group)
cli.add_command(vuln_templates.group)
cli.add_command(instances.group)
cli.add_command(scan_tasks.group)
cli.add_command(attachments.group)
cli.add_command(action_history.group)
cli.add_command(users.group)
cli.add_command(merge_rules.group)
cli.add_command(report_acts.group)
cli.add_command(recommendations.group)
cli.add_command(reports.group)


def main() -> None:
    try:
        cli(standalone_mode=False)
    except click.exceptions.Exit as exc:
        sys.exit(exc.exit_code)
    except click.exceptions.Abort:
        sys.exit(130)
    except click.exceptions.UsageError as exc:
        emit_error(str(exc))
        sys.exit(2)
    except click.exceptions.ClickException as exc:
        emit_error(exc.format_message())
        sys.exit(exc.exit_code)
    except ApiError as exc:
        emit_error(exc.message, status=exc.status, body=exc.body)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        emit_error(str(exc), status=exc.response.status_code)
        sys.exit(1)
    except httpx.HTTPError as exc:
        # Timeouts, refused connections, TLS failures: no HTTP status to report.
        emit_error(f"{type(exc).__name__}: {exc}")
        sys.exit(1)
    except RuntimeError as exc:
        # Config.resolve: missing URL or credentials.
        emit_error(str(exc))
        sys.exit(2)
    except Exception as exc:
        emit_error(f"{type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
