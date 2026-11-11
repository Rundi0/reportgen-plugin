---
name: reportgen-cli
description: Use this skill whenever the user asks to query or modify Report Generator data (organizations, audits, hosts, services, vulnerabilities, scan tasks, contacts, files, action history, vuln templates, merge rules) or to generate reports. The skill explains how to call the `reportgen` CLI to talk to the backend and how to interpret its JSON output. Trigger on requests like "list audits", "show services for audit N", "create a vulnerability", "kick off a scan", "generate report", or anything that maps to the REST API at `/api/...`.
---

# Working with the Report Generator CLI

`reportgen` is an AI-friendly CLI that mirrors the Report Generator REST API one-to-one. It is the preferred way to fetch or change data when responding to user questions about audits, hosts, services, vulnerabilities, etc.

## How to invoke

```bash
reportgen <group> <command> [args]
```

`reportgen` is on `PATH` when this skill comes from the plugin; cwd does not matter. In a checkout of the source repository without the plugin, call the same wrapper as `./cli/reportgen`. The wrapper runs the CLI through `uv` (required), building and caching a venv on first run, so the first call takes a few seconds. **Do not** call `python -m reportgen_cli` directly with `PYTHONPATH=...` — use the wrapper.

## Output contract

- **stdout**: JSON. Compact one-line by default; add `--pretty` (placed *before* the group name) for indented JSON.
- **stderr**: errors as `{"error": "...", "status": 4xx, "body": ...}`.
- **exit code**: `0` on success, `1` on API/runtime error, `2` on bad config or usage.

The backend wraps responses as `{"result": ...}`; the CLI unwraps that envelope so you get the bare value.

Pipe straight into `jq` to extract fields; never grep raw text.

## Authentication

The wrapper loads `REPORTGEN_URL` and the credential from an env file automatically: `.env` next to the wrapper in a source checkout, otherwise `~/.config/reportgen/.env`. With the plugin, that file is rewritten at session start from the plugin's settings — if the URL or key is missing or wrong, tell the user to run `/plugin configure` for this plugin and start a new session, rather than editing the file.

The CLI authenticates in one of two ways:

- **API key (recommended for scripting).** `REPORTGEN_API_KEY` holds a key created in the web UI under Settings (or the backend's static `API_KEY`). It is sent as `X-API-Key` on every request, authenticates without a browser cookie, and does not expire. Programmatic HTTP clients can use either `Authorization: Bearer <key>` or `X-API-Key: <key>`. Caveat: `auth whoami` hits `/api/auth/me`, which reads the session cookie directly, so it reports the session user (or 401) rather than the API key — all resource commands work fine with the key.
- **Session cookie.** The CLI carries the `session_id` cookie via `REPORTGEN_SESSION_ID`. If `auth whoami` returns `Session expired` (HTTP 401), the cookie is stale — tell the user to refresh it from the browser (DevTools → Application → Cookies → `session_id`) and overwrite `REPORTGEN_SESSION_ID` in the env file. Don't try to renew it programmatically.

Either credential satisfies auth; if both are set the API key takes precedence.

For a local development stack the base URL is `http://localhost:3000` (the frontend, which proxies `/api/*` to the backend); port 8000 is **not** reachable directly on the host.

## Resource hierarchy

```
organizations
└── audits          (one org → many audits)
    ├── hosts       (audit-scoped)
    ├── services    (audit-scoped, linked to hosts via host_services)
    ├── vulnerabilities
    │   └── instances (per-service findings, status: new|approved|false_positive|fixed)
    ├── scan-tasks  (background jobs)
    ├── files       (audit-level attachments)
    └── history     (action log + comments)

vuln-templates      (global, reusable vulnerability translations)
merge-rules         (global, vulnerability deduplication)
users               (Keycloak users — read only)
```

Most paths take an `AUDIT_ID` first. Hosts and services within an audit do not collide across audits — IDs are global.

## Command reference

Run `reportgen <group> --help` for the authoritative arg list. Quick map:

| Group | Common commands |
| --- | --- |
| `auth` | `whoami` |
| `organizations` | `list`, `get ORG_ID`, `create`, `update ORG_ID`, `delete ORG_ID`, `workspaces --source ...`, `import-pentestadmin PA_ID --source ...` |
| `audits` | `list`, `list-by-org ORG_ID`, `get AUDIT_ID`, `create ORG_ID --type ... --status ...`, `patch AUDIT_ID`, `delete AUDIT_ID`, `clear-scan-data AUDIT_ID` |
| `contacts` | `list ORG_ID`, `get ORG_ID CONTACT_ID`, `create ORG_ID`, `update ORG_ID CONTACT_ID`, `delete ORG_ID CONTACT_ID` |
| `hosts` | `list AUDIT_ID`, `get AUDIT_ID HOST_ID`, `create AUDIT_ID --ip ...`, `update`, `delete`, `refresh-countries AUDIT_ID HOST_ID...` |
| `services` | `list AUDIT_ID`, `get`, `create`, `update`, `delete`, `link-host`, `unlink-host`, `backfill-hosts AUDIT_ID`, `export-acunetix AUDIT_ID --output FILE` |
| `vulnerabilities` | `list AUDIT_ID`, `get AUDIT_ID VULN_ID`, `create AUDIT_ID --severity 1..5 ...`, `update`, `delete`, `bulk-delete AUDIT_ID ID...` |
| `instances` | `create`, `update`, `delete`, `bulk-delete`, `bulk-status --status STATUS AUDIT_ID VULN_ID ID...` |
| `vuln-templates` | `list -q QUERY`, `list-names`, `get`, `by-name NAME`, `create`, `update`, `delete`, `save` (upsert by name), `translate --service openai|ollama --body '{...}'` |
| `scan-tasks` | `list AUDIT_ID --status STATUS`, `get`, `create AUDIT_ID --scan-type ... --params '{...}'`, `cancel`, `delete` |
| `files` | `list-org`, `list-audit`, `list-vuln`, `upload-org`, `upload-audit`, `upload-vuln`, `download FILE_ID --output FILE`, `delete` |
| `history` | `list AUDIT_ID`, `comment AUDIT_ID "text"` |
| `general-recommendations` | `get AUDIT_ID`, `patch AUDIT_ID FILE` (JSON list or `get` output, `-` = stdin), `generate AUDIT_ID`, `reset AUDIT_ID` |
| `users` | `list` |
| `merge-rules` | `list`, `create --body '{...}'`, `update`, `delete` |
| `reports` | `list-templates`, `upload-scan-data AUDIT_ID FILE`, `check-translations --source ... --workspace-id N`, `generate --workspace-id N --template-id N --file-name NAME` |
| `report-acts` | `get AUDIT_ID`, `set-notes AUDIT_ID --file notes.md`, `split AUDIT_ID`, `generate AUDIT_ID`, `set-act AUDIT_ID --file act.md` |

### Severity levels

Vulnerabilities and templates: `1=Info`, `2=Low`, `3=Medium`, `4=High`, `5=Critical`.

### Instance statuses

`new` (default for fresh findings), `approved` (real, in scope), `false_positive`, `fixed`.

### Sources for `reports` and `organizations workspaces`

`internal_db` (the project's own DB), `pentestadmin_assessor`, `pentestadmin_scanner`, `faraday_assessor`, `faraday_scanner`. For internal DB report generation, `--workspace-id` is the **audit ID**.

## Building request bodies

Every mutating command accepts either explicit flags (`--name`, `--severity`, ...) or a full `--body '{"name":"...","severity":4}'`. Fields in `--body` use **camelCase** (matches the API): `pentestersIds`, `quartalYear`, `techStack`, `serviceId`, `hostIds`, `scanType`, `timeoutSeconds`. Explicit flags override colliding `--body` keys.

When the user provides a long description or messy text, prefer building a body in code:

```bash
reportgen vulnerabilities create 17 --body "$(cat <<'JSON'
{
  "name": "Outdated TLS",
  "severity": 4,
  "description": "Server still negotiates TLS 1.0...",
  "resolution": "Disable TLS 1.0 and 1.1.",
  "cve": ["CVE-2014-3566"],
  "proofs": null
}
JSON
)"
```

## Writing vulnerability `proofs` and instance `params`

These two free-text fields end up verbatim in the client report, so keep them terse, evidence-only, and easy to read. Update with `vulnerabilities update AUDIT_ID VULN_ID --proofs "..."` and `instances update AUDIT_ID VULN_ID INSTANCE_ID --params "..."`.

**`proofs` — concise command + output blocks, no prose.** Show only *confirmed, relevant* evidence: drop examples that are actually fine (correctly-configured, `false_positive`, or `fixed` instances) and collapse repetition — one representative block per distinct real finding, not one per host. Never a mega catch-all command.

Each block follows this exact rhythm, and the **blank line between the command and its output is the required visual separator** (a bare `$` prompt alone blends into the output lines):

```
# <what / where>  — one-line context label
$ <single command>

<output line>
<output line>
```

Put a blank line between blocks too. Redact secrets/tokens with `...` (proofs are illustrative examples, not exact captures). When output lines carry a trailing annotation, align it with spaces so it reads in a monospace `<pre>` view:

```
# account.example.com /auth/logout — session cookies without HttpOnly/Secure
$ curl -sk -D - https://account.example.com/auth/logout -o /dev/null | grep -i set-cookie

Set-Cookie: sid=...; Domain=.example.com          (no HttpOnly, no Secure)
Set-Cookie: sid_avatar=...; Domain=.example.com   (no HttpOnly, no Secure)
```

**`params` — only the fact relevant to *this* (child) vuln.** A bare noun or value, never a sentence or clause with a verb (BAD: `table parameter: SQL injection via unparameterized table name` → GOOD: `table`; BAD: `Session cookie without Secure flag` → GOOD: `missing=Secure`). For split cookie/TLS-style findings, scope `params` to the single attribute this child is about (e.g. child "Not Marked as Secure" → `missing=Secure`, not the full `missing=HttpOnly,Secure`). Never duplicate what other fields already carry — the endpoint lives in `path`, so don't repeat "set via /wp-admin/...". Strip scanner attribution like `(per Acunetix)`; state the fact directly. Leave `params` empty when the vuln name + path already say everything, and always empty on `false_positive` instances.

## Importing scan results

```bash
reportgen reports upload-scan-data AUDIT_ID scan.json      # Acunetix export (.json)
reportgen reports upload-scan-data AUDIT_ID scan.nessus    # Nessus (.nessus or .xml)
```

The file type is taken from the extension; anything else is rejected with HTTP 400. The import adds hosts, services and vulnerabilities (instances arrive as `new`) to the audit and is logged in its history. It is a mutation, so confirm the audit ID with the user first. Large files take a while — pass `--timeout 300` (a global flag, before the group).

## Generating documents

Two different things are called an "act" here, so find out which one the user means:

- a **document from a template** (`.docx` or `.html`) built from the audit's hosts and vulnerabilities — `reports generate`;
- an **AI-drafted act text** written from the engineer's notes — `report-acts`.

### Document from a template

**Always check translations first.** The document takes each vulnerability's text from its translation template (`vuln-templates`); a vulnerability without one goes into the document untranslated, and generation does not warn about it.

```bash
reportgen reports check-translations --source internal_db --workspace-id AUDIT_ID
```

It returns the vulnerabilities that have no template, as `[{name, severity, description, resolution, cve}]`; `[]` means everything is translated. It looks at the same set the document will contain: severity above Info with at least one instance that is not `false_positive` or `fixed`.

If the list is not empty, **do not generate yet**. Tell the user how many vulnerabilities lack a translation and name them, say that they would appear untranslated, and ask whether to add the translations first (`vuln-templates save`, or `vuln-templates translate` for an AI draft) or to generate anyway. Generate only after they answer. If the user already said to generate regardless, still report the list alongside the result.

Then generate:

```bash
reportgen reports list-templates                      # [{id, name}], e.g. Scan_act.docx, Scan_report.docx
reportgen reports generate --workspace-id AUDIT_ID --template-id TEMPLATE_ID --file-name act.docx
```

For the internal DB, `--workspace-id` is the audit ID and `--source` defaults to `internal_db`. The file is saved to `--output`, or to `--file-name` in the current directory, and the command prints `{"saved": ..., "bytes": ...}`. Give the name the template's extension (`.html` for the interactive report). On a large audit both commands can exceed the default 30 s timeout; use `--timeout 300`.

### AI-drafted act text

```bash
reportgen report-acts set-notes AUDIT_ID --file notes.md   # store the engineer's notes (markdown)
reportgen report-acts split AUDIT_ID                       # notes -> section outline (sectionsMd), no drafting
reportgen report-acts generate AUDIT_ID                    # outline -> act text (actMd); --prompt/--prompt-file to steer
reportgen report-acts get AUDIT_ID                         # {notesMd, sectionsMd, actMd, aiModel, generatedAt, ...}
reportgen report-acts set-act AUDIT_ID --file act.md       # save an edited act
```

`split` and `generate` call an LLM on the server, so they are slower than other commands, and they overwrite the stored outline or act — don't re-run `generate` over an act the user has edited without asking.

## Patterns

### Find an audit by org + summarize hosts

```bash
ORG=$(reportgen organizations list | jq '.[] | select(.name=="ACME") | .id')
AUDIT=$(reportgen audits list-by-org "$ORG" | jq '.[0].id')
reportgen hosts list "$AUDIT" | jq 'length, [.[].ip]'
```

### Wait for a scan task

```bash
reportgen scan-tasks create 17 --scan-type discover_services \
  --params '{"target":"acme.com"}' | jq '.id'
# poll
while :; do
  s=$(reportgen scan-tasks get 17 88 | jq -r .status)
  case "$s" in completed|failed|cancelled) break;; esac
  sleep 5
done
```

### Bulk operations

```bash
# IDs go as positional args after the audit/vuln ID
reportgen vulnerabilities bulk-delete 17 101 102 103
reportgen instances bulk-status 17 99 --status fixed 5001 5002 5003
```

### Download artifacts

`export-acunetix` and `download` use `--output PATH` (or `-` for stdout). `reports generate` defaults `--output` to `--file-name`.

## Things that bite

- **Always check `exit code`**, not just stdout content. A timeout, expired session, or 4xx all yield non-zero.
- **`--pretty` is a global flag** — put it *before* the group: `reportgen --pretty audits list`. After the group it errors as unknown.
- **The `services delete` endpoint refuses if instances reference the service** (HTTP 409). Delete instances first or use `bulk-delete` on vulns.
- **Output can be huge.** A `services list` for a sizeable audit is tens of KB. Pipe through `jq` to project just what you need before showing the user.
- **Don't paste raw session cookies or API keys into chat.** When troubleshooting auth, refer to it as "the value in the env file" and never `cat` that file into responses.
- **Do not run mutations without explicit user authorization.** Reads (`list`, `get`) are safe; `create`, `update`, `delete`, `clear-scan-data`, `bulk-*`, `cancel`, scan task creation all change state — confirm first when the user's request is ambiguous.
- **Merged (child) vulnerabilities are read-only.** `vulnerabilities list` nests children inside their parent's `children` array — they do not appear at the top level. Do not update, delete, or create instances on child vulnerabilities; all edits (name, severity, proofs, instances) go on the **parent**. To move a child out, `unmerge` it first.

## When the CLI lacks an operation

The CLI is meant to mirror the API exactly. If an operation is missing, call the API directly via `curl` with the same credential (`X-API-Key: <key>`), and tell the user the CLI is missing a wrapper. In a checkout of the source repository, `backend/src/presentation/*/rest.py` shows what the backend exposes and `cli/reportgen_cli/commands/` is where to add the wrapper. Never go around the API by editing the database.
