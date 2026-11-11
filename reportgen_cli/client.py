"""HTTP client wrapping the Report Generator REST API.

Requests authenticate with an API key (X-API-Key header) when one is
configured, otherwise with the session_id cookie. The backend wraps
responses as {"result": ...} for most endpoints; this client unwraps
that envelope automatically. Non-2xx responses raise ApiError with the
server-supplied detail message when available.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from .config import Config


# Anything other than GET under /api/audits/{id} changes that audit.
_AUDIT_PATH = re.compile(r"^/api/audits/(\d+)(?:/|$)")


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message
        self.body = body


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            if "detail" in body:
                return str(body["detail"])
            if "message" in body:
                return str(body["message"])
        return response.text or response.reason_phrase
    except Exception:
        return response.text or response.reason_phrase


class ApiClient:
    def __init__(self, config: Config):
        self._config = config
        headers = {"X-API-Key": config.api_key} if config.api_key else {}
        cookies = (
            {"session_id": config.session_id} if config.session_id else {}
        )
        self._me: str | None = None
        self._http = httpx.Client(
            base_url=config.url,
            headers=headers,
            cookies=cookies,
            verify=config.verify_tls,
            timeout=config.timeout,
            follow_redirects=False,
        )

    def me(self) -> str:
        """`sub` of the user the CLI is acting as."""
        if self._me is None:
            self._me = self.get("/api/auth/me", unwrap=False)["sub"]
        return self._me

    def require_member(self, audit_id: int) -> None:
        """Refuse to change an audit the current user is not a pentester on."""
        pentesters = self.get(f"/api/audits/{audit_id}").get("pentestersIds") or []
        if self.me() not in pentesters:
            raise ApiError(
                403,
                f"You are not a pentester on audit {audit_id}; "
                "the CLI only changes audits you take part in.",
            )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        files: Any = None,
        data: Any = None,
        unwrap: bool = True,
    ) -> Any:
        if method != "GET" and (m := _AUDIT_PATH.match(path)):
            self.require_member(int(m[1]))
        response = self._http.request(
            method,
            path,
            params=params,
            json=json,
            files=files,
            data=data,
        )
        if response.status_code >= 400:
            raise ApiError(
                response.status_code,
                _extract_error(response),
                body=_safe_json(response),
            )
        if response.status_code == 204 or not response.content:
            return None
        body = response.json()
        if unwrap and isinstance(body, dict) and "result" in body:
            return body["result"]
        return body

    def get(self, path: str, **kw: Any) -> Any:
        return self._request("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> Any:
        return self._request("POST", path, **kw)

    def put(self, path: str, **kw: Any) -> Any:
        return self._request("PUT", path, **kw)

    def patch(self, path: str, **kw: Any) -> Any:
        return self._request("PATCH", path, **kw)

    def delete(self, path: str, **kw: Any) -> Any:
        return self._request("DELETE", path, **kw)

    def download(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        response = self._http.request("GET", path, params=params)
        if response.status_code >= 400:
            raise ApiError(
                response.status_code,
                _extract_error(response),
                body=_safe_json(response),
            )
        return response.content

    def post_raw(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        response = self._http.request(
            "POST", path, params=params, json=json
        )
        if response.status_code >= 400:
            raise ApiError(
                response.status_code,
                _extract_error(response),
                body=_safe_json(response),
            )
        return response.content


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None
