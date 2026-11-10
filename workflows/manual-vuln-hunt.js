export const meta = {
  name: 'manual-vuln-hunt',
  description: 'Manual vulnerability discovery — assess services, investigate areas, verify hypotheses',
  whenToUse: 'When the user asks to hunt/discover/find new vulnerabilities on services in an audit',
  phases: [
    { title: 'Scout', detail: 'List target services' },
    { title: 'Assess', detail: 'Per-service — identify attack areas' },
    { title: 'Investigate', detail: 'Per-area — probe and form hypotheses' },
    { title: 'Verify', detail: 'Per-hypothesis — independent confirmation' },
    { title: 'Consolidate', detail: 'Deduplicate and write results file' },
  ],
}

const auditId = args.auditId
if (!auditId) throw new Error('args.auditId is required')

const SERVICES_SCHEMA = {
  type: 'object',
  properties: {
    services: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'number' },
          name: { type: 'string' },
          domain: { type: ['string', 'null'] },
          type: { type: ['string', 'null'] },
          techStack: { type: ['array', 'null'], items: { type: 'string' } },
          hosts: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                ip: { type: ['string', 'null'] },
                port: { type: 'string' },
              },
              required: ['port'],
            },
          },
        },
        required: ['id', 'name'],
      },
    },
  },
  required: ['services'],
}

const AREAS_SCHEMA = {
  type: 'object',
  properties: {
    techStack: { type: 'array', items: { type: 'string' } },
    existingVulns: { type: 'array', items: { type: 'string' } },
    areas: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          rationale: { type: 'string' },
          tools: { type: 'string' },
        },
        required: ['name', 'rationale', 'tools'],
      },
    },
  },
  required: ['techStack', 'existingVulns', 'areas'],
}

const HYPOTHESES_SCHEMA = {
  type: 'object',
  properties: {
    hypotheses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          description: { type: 'string' },
          evidence: { type: 'string' },
          suggestedSeverity: { type: 'number' },
        },
        required: ['title', 'description', 'evidence'],
      },
    },
  },
  required: ['hypotheses'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    confirmed: { type: 'boolean' },
    title: { type: 'string' },
    severity: { type: 'number' },
    evidence: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['confirmed', 'title', 'severity', 'evidence'],
}

// --- Scout ---
phase('Scout')
const scout = await agent(
  `Load the reportgen-cli skill with the Skill tool (listed as "reportgen-cli", or "reportgen:reportgen-cli" when it comes from the plugin).

Run: reportgen services list ${auditId}

Return all services with id, name, domain, type, techStack, hosts (ip + port).`,
  { label: 'scout', schema: SERVICES_SCHEMA }
)

if (!scout || !scout.services.length) {
  log('No services found')
  return { findings: [], message: 'No services in this audit' }
}

let services = scout.services
if (args.serviceIds) {
  const allowed = new Set(args.serviceIds)
  services = services.filter(s => allowed.has(s.id))
}
if (args.limit) services = services.slice(0, args.limit)
log(`${services.length} services to hunt`)

// Pipeline: each service goes through assess → investigate+verify.
// Different services run in parallel; within one service, all probing is sequential (WAF-safe).
const allFindings = await pipeline(
  services,

  // Stage A: assess service → list of { service, area } pairs
  async (svc) => {
    const assessment = await agent(
      `Load the reportgen-cli skill with the Skill tool (listed as "reportgen-cli", or "reportgen:reportgen-cli" when it comes from the plugin).

Assess service #${svc.id} "${svc.name}" (audit ${auditId}).
Domain: ${svc.domain || 'none'} | Type: ${svc.type || '?'} | Tech: ${(svc.techStack || []).join(', ') || '?'}
Hosts: ${(svc.hosts || []).map(h => (h.ip || '?') + ':' + h.port).join(', ') || '?'}

## Task 1 — Detect tech stack

Make a request to the service and identify its technology stack: framework (Laravel, Django, Rails, Next.js, WordPress, etc.), language, web server, WAF/CDN, CMS, JS libraries. Use response headers, cookies, HTML meta tags, script paths, error page signatures, favicon hashes, etc.

If the service already has a techStack in the database, merge your findings with it (don't lose existing entries).
Save the updated tech stack:
reportgen services update ${auditId} ${svc.id} --tech-stack "item1,item2,item3"

Return the detected stack in the "techStack" field.

## Task 2 — List existing scanner findings

Run: reportgen vulnerabilities list ${auditId}
Collect names of all vulns that have instances (any status) on serviceId ${svc.id}.
Return these names in the "existingVulns" field — the investigation agents will use this to avoid re-discovering what scanners already found.

## Task 3 — Identify areas to check

Identify 3-7 security areas to check. Focus on areas that automated scanners CANNOT cover well:
- Default credentials on login/admin forms (admin/admin, tech-stack-specific defaults)
- Hardcoded secrets in JS bundles, HTML source, config endpoints
- IDOR — any numeric/predictable IDs in URLs or API endpoints → test adjacent IDs
- Open registration, direct IP access bypassing CDN, Host header tricks
- File upload without type validation (.php, .phtml execution)
- Business logic flaws (authentication bypass, privilege escalation, workflow bypasses)
- API security (excessive data exposure, mass assignment, broken function-level authorization)
- Information disclosure through application behavior (error messages, debug endpoints, admin panels)

Do NOT list generic scanner areas (TLS config, HTTP headers, cookie flags, server version disclosure) — those are already covered by automated scanning.

For each area return:
- name: short label
- rationale: why relevant for THIS service, given its tech stack and purpose
- tools: how to check (curl with specific paths, parameter fuzzing, etc.)

Only list areas checkable with benign requests. Prioritize by likelihood of real issues.`,
      { label: `assess:${svc.name.substring(0, 35)}`, phase: 'Assess', schema: AREAS_SCHEMA }
    )
    if (!assessment || !assessment.areas.length) return []
    const enrichedSvc = { ...svc, techStack: assessment.techStack || svc.techStack }
    return assessment.areas.map(a => ({
      service: enrichedSvc,
      area: a,
      existingVulns: assessment.existingVulns || [],
    }))
  },

  // Stage B: for each area, investigate → hypotheses → verify each
  async (serviceAreas) => {
    const findings = []
    for (const { service: svc, area, existingVulns } of serviceAreas) {
      const existingList = (existingVulns || []).map(v => `  - ${v}`).join('\n')
      const investigation = await agent(
        `You are probing the "${area.name}" area on service "${svc.name}".
Domain: ${svc.domain || 'none'}
Hosts: ${(svc.hosts || []).map(h => (h.ip || '?') + ':' + h.port).join(', ') || '?'}
Tech: ${(svc.techStack || []).join(', ') || '?'}

Rationale: ${area.rationale}
Suggested tools: ${area.tools}

## Already known vulnerabilities (found by scanner)
${existingList || '(none)'}

Do NOT re-discover these — the scanner already covers them. Focus on issues that require human/contextual analysis.

## Mandatory checks (apply whichever are relevant to this area)

1. **Default credentials** — if the service has a login form or admin panel, try common default pairs (admin/admin, admin/password, admin/123456, test/test, root/root, etc.). Also check tech-stack-specific defaults (e.g. WordPress admin/admin, phpMyAdmin root/(empty), Tomcat tomcat/tomcat, Grafana admin/admin).

2. **Hardcoded data in responses** — inspect HTML source, JS files, and API responses for hardcoded credentials, API keys, tokens, internal IPs, database connection strings, AWS keys, .env values. Check paths like /js/app.js, /static/js/*.js, /.env, /config.js, /api/config.

3. **IDOR / broken access control** — if the application uses numeric or predictable IDs in URLs (e.g. /user/123, /order/456, /api/v1/documents/789) or in request body, try adjacent IDs (±1, ±2) to see if data from other users/entities is accessible. Compare responses: same structure with different data = confirmed IDOR.

4. **Registration and IP access** — check if the service has an open registration form (/register, /signup, /створити-акаунт). Check if the service is accessible directly by IP (bypassing domain/CDN). Try Host header manipulation to access internal vhosts.

5. **File upload validation** — if the service has any file upload functionality, test whether it validates file types. Try uploading a file with .php extension (or .phtml, .php5, .phar) to see if server-side code execution is possible. Check if uploaded files are accessible and executed.

Actively probe this area with benign requests.
For each real issue found, form a hypothesis:
- title: definitive vulnerability name (no "Possible", no hedging)
- description: what the issue is and its security impact
- evidence: exact command + output that shows the issue
- suggestedSeverity: 1=Info 2=Low 3=Medium 4=High 5=Critical

Only report issues you actually observed. If probing found nothing, return empty hypotheses array.
One benign request per check. Authorized testing on own resources.`,
        { label: `probe:${svc.name.substring(0, 15)}/${area.name.substring(0, 20)}`, phase: 'Investigate', schema: HYPOTHESES_SCHEMA }
      )

      if (!investigation || !investigation.hypotheses.length) continue

      for (const hyp of investigation.hypotheses) {
        const verdict = await agent(
          `Independently verify this vulnerability hypothesis.

Service: "${svc.name}" | Domain: ${svc.domain || 'none'}
Hosts: ${(svc.hosts || []).map(h => (h.ip || '?') + ':' + h.port).join(', ') || '?'}

Hypothesis: "${hyp.title}"
${hyp.description}

Prior evidence:
${hyp.evidence}

Run your OWN check to confirm or deny. Don't trust the prior evidence — verify independently.
If the suggested command is reasonable, run it; if a better check exists, use that.

Return:
- confirmed: true/false
- title: definitive vulnerability name
- severity: 1-5
- evidence: your command + output
- notes: any caveats (WAF blocking, partial confirmation, etc.)

If WAF/captcha blocks the check, that is NOT a false positive — still mark confirmed with a note.
Authorized testing on own resources.`,
          { label: `verify:${hyp.title.substring(0, 40)}`, phase: 'Verify', schema: VERDICT_SCHEMA }
        )

        if (verdict && verdict.confirmed) {
          findings.push({
            serviceId: svc.id,
            serviceName: svc.name,
            domain: svc.domain,
            hosts: svc.hosts,
            area: area.name,
            title: verdict.title,
            severity: verdict.severity,
            evidence: verdict.evidence,
            notes: verdict.notes || '',
          })
        }
      }
    }
    return findings
  }
)

// --- Consolidate ---
phase('Consolidate')
const flat = allFindings.filter(Boolean).flat()

if (!flat.length) {
  log('No confirmed vulnerabilities found')
  await agent(
    `Write this to ./manual-hunt-results-${auditId}.json:
{"auditId":${auditId},"totalFindings":0,"findings":[]}`,
    { label: 'write-empty', phase: 'Consolidate' }
  )
  return { auditId, totalFindings: 0, outputFile: `./manual-hunt-results-${auditId}.json` }
}

log(`${flat.length} confirmed findings — deduplicating`)

await agent(
  `Deduplicate and write findings to ./manual-hunt-results-${auditId}.json

Dedup rules:
- Same title + same serviceId = duplicate → keep the one with better evidence
- Same title on DIFFERENT services = NOT a duplicate → keep both
- Near-duplicate titles (e.g. "Missing X-Frame-Options" vs "X-Frame-Options Not Set") → merge

Output JSON:
{
  "auditId": ${auditId},
  "totalFindings": <count after dedup>,
  "findings": [
    {
      "serviceId": <number>,
      "serviceName": "<string>",
      "domain": "<string or null>",
      "hosts": [{"ip":"...","port":"..."}],
      "area": "<string>",
      "title": "<string>",
      "severity": <1-5>,
      "evidence": "<command + output>",
      "notes": "<string>"
    }
  ]
}

Sort by severity descending, then by serviceName.

Findings:
${JSON.stringify(flat, null, 2)}`,
  { label: 'dedup-and-write', phase: 'Consolidate' }
)

return {
  auditId,
  totalRaw: flat.length,
  outputFile: `./manual-hunt-results-${auditId}.json`,
}
