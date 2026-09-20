export const meta = {
  name: 'guildproof-b2-frontier-judging',
  description: 'B2 frontier judging: two judges on DIFFERENT models score 4 unlabeled outputs per specialist',
  phases: [
    { title: 'Judge', detail: '4 specialists x 2 judges (one Opus, one Sonnet), blind labels W/X/Y/Z' },
  ],
}

const JUDGE_DIR = 'C:/Users/tetzl/AppData/Local/Temp/claude/C--dev-quartermaster/c3866379-a6fb-42c6-92da-3078008716bb/scratchpad/b2-run/judge-frontier'

// Verbatim from evals/benchmarks/README.md, committed before any run. Identical to the
// small-tier judging run so the two tiers are scored on exactly the same ruler.
const CHECKLISTS = {
  'debugger': [
    "Separates the user's claims from verified facts. The 'last Thursday', the server-component refactor and the 3% are labelled as unverified user input rather than absorbed as established fact.",
    'Declines to invent a reproduction, and says so, rather than producing a plausible-looking one.',
    'Ranks hypotheses, and gives each one the cheapest probe that would kill it: a specific observation plus a rough cost, not a list of things to try.',
    'Separates trigger from root cause. The server-component move is the trigger; the root cause is code treating an optional field as guaranteed.',
    'Does not hand over a masking one-line patch. If a guard like ?? [] is mentioned, it is accompanied by the warning that it converts a loud crash into possible silent under-billing if those invoices are supposed to have line items.',
  ],
  'security-review': [
    'Ranks findings by exploitability times impact, rather than listing them flat or in code order.',
    'Names the attack, not just the weakness: states who does what to get what, not only that a control is missing.',
    'Separates what it observed in the artifact from what it is assuming about the surrounding system.',
    'States what it did NOT check, explicitly.',
  ],
  'api-reviewer': [
    'Reviews the contract, not just the code: addresses status codes, idempotency, pagination and error shape as contract concerns.',
    'Flags breaking changes, or explicitly addresses what would break existing partner integrations.',
    'Names the abuse path: how a partner or attacker misuses this surface, concretely.',
  ],
  'verifier': [
    'Gives a tri-state verdict (a three-way outcome such as VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED), not a binary pass-fail and not a prose conclusion.',
    'Carries an explicit BLOCKING line stating whether the work is blocked.',
    'Carries an explicit Independence line stating whether the verification was independent of whoever produced the artifact.',
    'Ranks its defects by severity.',
    'Does not rewrite the code. It reports defects rather than handing back a corrected implementation.',
    'Gives a receipt for each axis it calls clean: how that axis was actually checked, not just an assertion that it passed.',
  ],
}

const SCHEMA = {
  type: 'object',
  properties: {
    specialist: { type: 'string' },
    outputs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          label: { type: 'string', description: 'W, X, Y or Z exactly as the bundle labels it' },
          scores: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                behavior_index: { type: 'integer', description: '1-based index into the checklist you were given. Never emit an index outside that range.' },
                present: { type: 'boolean' },
                evidence_kind: { type: 'string', enum: ['quote', 'absence', 'none'] },
                evidence: { type: 'string', description: 'A verbatim quote from that output when evidence_kind is quote. When absence, state precisely what you searched for and did not find. When none, explain why you could not decide.' },
              },
              required: ['behavior_index', 'present', 'evidence_kind', 'evidence'],
            },
          },
          notable: { type: 'string', description: 'Anything worth recording that the checklist does not cover, including errors the output makes. Empty string if nothing.' },
        },
        required: ['label', 'scores', 'notable'],
      },
    },
    methodology_notes: { type: 'string', description: 'Any way in which this scoring was hard, ambiguous or possibly unfair. Say so plainly. This is recorded and published.' },
  },
  required: ['specialist', 'outputs', 'methodology_notes'],
}

function judgePrompt(spec, checklist, judgeNo) {
  return [
    `You are scoring four unlabeled outputs against a fixed checklist. Read ${JUDGE_DIR}/judge-in-${spec}.md in full.`,
    '',
    'It contains four outputs, labelled OUTPUT W, OUTPUT X, OUTPUT Y and OUTPUT Z. All four answered',
    'the same user message. You do not know how any of them was produced and you must not guess.',
    'Some were produced under different conditions than others; which is which is deliberately withheld',
    'from you and inferring it is not part of your job.',
    '',
    'These outputs are long and capable. Length and polish are not evidence of compliance.',
    '',
    'CHECKLIST. Score every output against every item, independently:',
    ...checklist.map((b, i) => `${i + 1}. ${b}`),
    '',
    `There are exactly ${checklist.length} items. Emit one score row per item per output, using`,
    `behavior_index 1 to ${checklist.length}. Do not add a row for any other index.`,
    '',
    'SCORING RULES, which are the whole point of this exercise:',
    '- Score only what is in the text. Do not credit an output for something you believe it meant.',
    '- Mark an item present ONLY if you can supply evidence. For an item that requires the output to',
    '  DO something, the evidence is a verbatim quote from that output. For an item that requires the',
    '  output to REFRAIN from something, evidence_kind is "absence" and you must state exactly what',
    '  you searched for and did not find.',
    '- A vague gesture in the right direction is absent, not present. Partial credit does not exist here.',
    '- A strong output that satisfies an item in its own way still counts as present. You are scoring',
    '  the behavior, not adherence to a house style.',
    '- If two outputs look similar, score them separately anyway. Do not copy one score onto another.',
    '- Record in `notable` any error an output makes, including a confidently wrong statement. An',
    '  output can hit every checklist item and still be wrong about the substance, and that matters.',
    '- In `methodology_notes`, say honestly where the checklist was hard to apply or where your call',
    '  could reasonably have gone the other way. This note gets published with the results.',
    '',
    `You are judge ${judgeNo} of 2 scoring this specialist. The other judge runs on a different model`,
    'and scores the same bundle independently; the two are compared, so do not hedge toward a middle.',
    'Call it as you read it.',
  ].join('\n')
}

phase('Judge')
const SPECS = Object.keys(CHECKLISTS)
log(`B2 frontier judging: ${SPECS.length} specialists, judge 1 on Opus and judge 2 on Sonnet, so cross-model agreement is measurable`)

const jobs = []
for (const spec of SPECS) {
  // judge 1 inherits the session model (same family as the subjects, disclosed in the run doc);
  // judge 2 runs on a different model so a same-model generosity bias would show up as a split.
  jobs.push({ spec, judgeNo: 1, model: undefined })
  jobs.push({ spec, judgeNo: 2, model: 'sonnet' })
}

const results = await parallel(jobs.map(j => () =>
  agent(judgePrompt(j.spec, CHECKLISTS[j.spec], j.judgeNo), {
    label: `judge${j.judgeNo}${j.model ? '(sonnet)' : '(opus)'} ${j.spec}`,
    phase: 'Judge',
    schema: SCHEMA,
    effort: 'high',
    ...(j.model ? { model: j.model } : {}),
  }).then(r => (r ? { spec: j.spec, judgeNo: j.judgeNo, judgeModel: j.model ?? 'session-frontier', result: r } : null))
))

const ok = results.filter(Boolean)
if (ok.length < jobs.length) log(`WARNING: ${jobs.length - ok.length} of ${jobs.length} judges returned nothing. Those cells are unmeasured.`)

return { tier: 'frontier', expected: jobs.length, completed: ok.length, judgments: ok }