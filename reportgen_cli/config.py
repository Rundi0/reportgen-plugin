"""CLI runtime config — base URL plus API key and/or session_id.

Resolution order: explicit flags, then env vars REPORTGEN_URL /
REPORTGEN_API_KEY / REPORTGEN_SESSION_ID. A URL is always required;
authentication is satisfied by either an API key or a session_id. If
neither is present the CLI fails fast with a clear error so AI agents do
not silently hit the wrong server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    url: str
    session_id: str | None = None
    api_key: str | None = None
    verify_tls: bool = True
    timeout: float = 30.0

    @classmethod
    def resolve(
        cls,
        url: str | None,
        session_id: str | None,
        api_key: str | None = None,
        verify_tls: bool = True,
        timeout: float = 30.0,
    ) -> "Config":
        url = url or os.environ.get("REPORTGEN_URL")
        session_id = session_id or os.environ.get("REPORTGEN_SESSION_ID")
        api_key = api_key or os.environ.get("REPORTGEN_API_KEY")

        if verify_tls:
            env_val = os.environ.get("REPORTGEN_VERIFY_TLS", "").lower()
            if env_val in ("0", "false", "no"):
                verify_tls = False

        missing: list[str] = []
        if not url:
            missing.append("--url / REPORTGEN_URL")
        if not api_key and not session_id:
            missing.append(
                "--api-key / REPORTGEN_API_KEY or "
                "--session-id / REPORTGEN_SESSION_ID"
            )
        if missing:
            raise RuntimeError(
                "Missing required config: " + ", ".join(missing)
            )

        return cls(
            url=url.rstrip("/"),
            session_id=session_id,
            api_key=api_key,
            verify_tls=verify_tls,
            timeout=timeout,
        )
