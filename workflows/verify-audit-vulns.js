export const meta = {
  name: 'verify-audit-vulns',
  description: 'Verify all vulnerabilities with new instances in an audit — one agent per vuln',
  whenToUse: 'When the user asks to verify/triage all vulnerabilities in an audit',
  phases: [
    { title: 'Scout', detail: 'Fetch vulns that have new instances' },
    { title: 'Verify', detail: 'One agent per vulnerability, sequential checks' },
  ],
}

const auditId = args.auditId
if (!auditId) throw new Error('args.auditId is required')

const VULNS_SCHEMA = {
  type: 'object',
  properties: {
    vulnerabilities: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'number' },
          name: { type: 'string' },
          severity: { type: 'number' },
          newCount: { type: 'number' },
        },
        required: ['id', 'name', 'severity', 'newCount'],
      },
    },
  },
  required: ['vulnerabilities'],
}

phase('Scout')
const scout = await agent(
  `Run: reportgen vulnerabilities list ${auditId}

The output is a JSON array of top-level vulnerabilities. Each may have an "instances" array and optionally a "children" array (merged vulns whose instances also belong to this parent).

Return ONLY vulns that have at least one instance with "status": "new" — count new instances across own + children's instances. Skip vulns where every instance is already approved/false_positive/fixed.`,
  { label: 'scout', schema: VULNS_SCHEMA, model: 'claude-opus-4-6' }
)

if (!scout || !scout.vulnerabilities.length) {
  log('No vulnerabilities with new instances found')
  return { verified: 0, message: 'Nothing to verify' }
}

let vulns = scout.vulnerabilities
if (args.limit) {
  vulns = vulns.slice(0, args.limit)
  log(`Found ${scout.vulnerabilities.length} vulns with new instances, processing first ${vulns.length}`)
} else {
  log(`Found ${vulns.length} vulns with new instances`)
}

phase('Verify')
const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    vulnId: { type: 'number' },
    vulnName: { type: 'string' },
    approved: { type: 'number' },
    falsePositive: { type: 'number' },
    leftNew: { type: 'number' },
    proofsWritten: { type: 'boolean' },
    notes: { type: 'string' },
  },
  required: ['vulnId', 'vulnName', 'approved', 'falsePositive', 'leftNew', 'proofsWritten'],
}

const results = await pipeline(
  vulns,
  (v) => agent(
    `Before doing anything, load two skills using the Skill tool (when they come from the plugin they are listed with a "reportgen:" prefix):
1. reportgen-cli — CLI reference for querying and modifying data
2. verify-vuln — step-by-step algorithm for verifying a vulnerability

Then follow the verify-vuln skill to verify vulnerability #${v.id} "${v.name}" (severity ${v.severity}) in audit ${auditId}. It has ${v.newCount} new instance(s).

Return: vulnId, vulnName, counts of approved/falsePositive/leftNew, proofsWritten, short notes.`,
    { label: `${v.name.substring(0, 45)}`, phase: 'Verify', schema: RESULT_SCHEMA, model: 'claude-opus-4-6' }
  )
)

const summary = results.filter(Boolean)
const totals = summary.reduce((acc, r) => {
  acc.approved += r.approved
  acc.falsePositive += r.falsePositive
  acc.leftNew += r.leftNew
  return acc
}, { approved: 0, falsePositive: 0, leftNew: 0 })

return {
  auditId,
  vulnsProcessed: summary.length,
  ...totals,
  details: summary,
}
