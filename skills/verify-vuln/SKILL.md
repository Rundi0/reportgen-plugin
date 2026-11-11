---
name: verify-vuln
description: Verify a single vulnerability — triage all its `new` instances as approved or false_positive, write proofs.
trigger: Only when the user directly asks to verify, check, or triage a vulnerability (by ID or name) in a Report Generator audit, or a workflow they started says to. Never on your own initiative.
---

# Verify a vulnerability

This skill walks through one vulnerability end-to-end: understand it, check every `new` instance, set statuses, and write proofs.

## Prerequisites

Load the `reportgen-cli` skill first — it explains how to call the CLI and format proofs/params.

## Step 0 — Fetch the vulnerability

```bash
reportgen vulnerabilities get <AUDIT_ID> <VULN_ID>
```

Read: `name`, `severity`, `description`, `instances`, `children` (merged vulns carry their instances in children).

Collect **all** instances with `status: "new"` — from the vuln itself AND from every child. Already `approved`/`false_positive`/`fixed` instances are settled; skip them.

## Step 1 — Understand the vulnerability

Before touching any instance, understand **what this vulnerability is** and **how to confirm or refute it**:

- Read `description` and `rawData` on instances (scanner output: `rawData.description`, `rawData.details`, `rawData.request`, `rawData.response`, `rawData.refs`).
- Determine the verification method: what single benign request proves the issue is present? What response proves it's absent or mitigated?
- If the vulnerability is version-based (e.g. "WordPress 4.9.x Directory Traversal"), confirmation = verifying the target still runs the affected version, NOT reproducing the exploit.
- If the vulnerability is configuration-based (TLS, headers, cookies), confirmation = one request showing the misconfiguration.

## Step 2 — Check each `new` instance

For every `new` instance, do **one** minimal check:

1. Look at `serviceId` → resolve to host:port via `services get`.
2. Look at `path` and `params` — they tell you WHERE and WHAT.
3. Run **one benign request** to confirm or refute. One `curl`, one `sslscan`, one `nmap` — whatever fits. Don't fan out across payload variants.
4. Classify:
   - **Confirmed** → set `approved`.
   - **Not present / wrong product / genuinely fixed** → set `false_positive`.
   - **WAF/captcha/anti-bot blocks the check** → this is NOT a false positive. Set `approved` with a comment noting the third-party control.
   - **Target unreachable** — before calling it unreachable, consider whether your own IP got rate-limited by aggressive checks: re-check once, gently and sequentially, before concluding. If genuinely down, leave as `new` and tell the user.

Apply status:
```bash
reportgen instances update <AUDIT_ID> <VULN_ID> <INSTANCE_ID> --body '{"status": "approved"}'
# or for bulk:
reportgen instances bulk-status <AUDIT_ID> <VULN_ID> --status approved <ID1> <ID2> ...
```

### Version-based instances — set `params`

When the vulnerability is about an outdated or vulnerable version (library, CMS, framework, protocol), write the resource name and detected version into `params` on each approved instance:

```bash
reportgen instances update <AUDIT_ID> <VULN_ID> <INSTANCE_ID> --params "jQuery 1.6.3"
# or: "Joomla 3.9.23", "WordPress 4.9.9", "TLSv1.0", "Moment.js 2.10.6"
```

Keep it short — just `<resource> <version>`. No prose, no URLs, no scanner attribution.

### Non-version instances — set `params` to the vulnerable parameter

When the vulnerability is not version-based (e.g. SQLi, XSS), `params` should name the vulnerable input:
- If the payload is already in `path` (e.g. `/news/1'"1000`), the path speaks for itself — leave `params` empty.
- If `path` is clean (e.g. `/digestlist/`), the payload went into a GET/POST parameter or header — set `params` to that parameter name (e.g. `pgn`, `email`, `User-Agent`). Extract it from `rawData.details`.

### `params` format rules (STRICT)

**Max ~50 characters.** If it doesn't fit in one short phrase, it doesn't belong in `params`.

`params` holds exactly ONE of these:
- A library version: `jQuery 1.6.3`, `Joomla 3.9.23`, `TLSv1.0`
- A vulnerable parameter name: `pgn`, `email`, `User-Agent`, `client_id`
- A short issue label: `introspection enabled`, `batching enabled`
- Empty — when none of the above applies

**NEVER put these in `params`:**
- Sentences or clauses with verbs — if it reads like a description, it's wrong
  - BAD: `table parameter: SQL injection via unparameterized table name` → GOOD: `table`
  - BAD: `Session cookie without Secure flag` → GOOD: `missing=Secure`
  - BAD: `Login form submits without CSRF token` → GOOD: (empty)
  - BAD: `Accepts arbitrary parameters without validation` → GOOD: (empty)
  - BAD: `x-ray header exposes internal hostnames and routing` → GOOD: `X-Ray`
- Scanner payloads, query strings, POST bodies, multipart boundaries
- HTTP status codes (`HTTP 200`, `HTTP 403`)
- JSON blobs or request fragments
- Anything already in `path` or `service` or the vuln name

### Checking order

- Work **sequentially**, one instance at a time — parallel requests to the same target trip WAFs.
- Group instances by `serviceId` so you hit each host once if possible.

## Step 3 — Write proofs

After all instances are triaged, write `proofs` on the **parent** vulnerability (never on a child — children are read-only, see reportgen-cli skill).

Proofs format (concise command+output, NO prose):

```
# <what / where>
$ <command>

<output>
```

Rules:
- One representative block per distinct confirmed finding — not one per host when they're identical.
- Drop examples for `false_positive` or `fixed` instances — proofs show only real findings.
- Redact secrets/tokens with `...`.
- Blank line between command and output, blank line between blocks.
- No commentary, no interpretation, no dates, no remediation steps.
- No FP evidence — don't include blocks showing why something is a false positive (e.g. "site rebuilt as Next.js", "not Joomla").
- No WAF-blocked evidence — don't include blocks showing a 403 or WAF page with prose explaining it.

Apply:
```bash
reportgen vulnerabilities update <AUDIT_ID> <VULN_ID> --proofs "$(cat <<'PROOFS'
# <context>
$ <command>

<output>
PROOFS
)"
```

## Step 4 — Report

Tell the user what happened in a short summary:
- How many instances confirmed / FP / left as new.
- One-line per notable finding or grouping.

## Things to avoid

- Don't update/delete child (merged) vulnerabilities — edits go on the parent.
- Don't ask "should I create?" after confirming — create/update immediately.
- Don't write mega catch-all commands in proofs.
- Don't probe aggressively — one benign request per instance.
- Don't mark WAF-blocked findings as `false_positive`.
- Don't blindly confirm what the scanner labels — understand what you're actually seeing. A CSRF token in a URL is NOT a "Session ID in URL"; an example credential in documentation is NOT a "password disclosure". If the finding's name doesn't match the actual issue, it's a false positive (or needs renaming to what it really is).
- Don't use "Possible" or "ймовірно" in vulnerability names — the agent's job is to determine whether it's real or FP, not to hedge. If a scanner labels something "[Possible] Backup Folder", verify it: if the directory exists and contains sensitive content, rename to a definitive name (e.g. "Sensitive Files and Directories") and approve; if it's empty or harmless, mark FP.
- Don't leave "possible/ймовірний" sensitivity claims unresolved — check what the directory/file actually contains and state concretely what is sensitive (or mark FP if nothing is).
