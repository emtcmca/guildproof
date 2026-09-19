export const meta = {
  name: 'guildproof-b2-generation',
  description: 'B2 benchmark, generation half: 4 specialists x bare-vs-guildproof x k=2 at the small-model tier',
  phases: [
    { title: 'Generate', detail: '16 runs, small-model tier (haiku), raw outputs written to disk', model: 'haiku' },
  ],
}

const OUT = 'C:/Users/tetzl/AppData/Local/Temp/claude/C--dev-quartermaster/c3866379-a6fb-42c6-92da-3078008716bb/scratchpad/b2-run/out'
const IN = 'C:/Users/tetzl/AppData/Local/Temp/claude/C--dev-quartermaster/c3866379-a6fb-42c6-92da-3078008716bb/scratchpad/b2-run/inputs'

// Each case: the user message exactly as both arms receive it. `readFile` is an artifact
// the message refers to; it is staged with no benchmark framing in it or its path.
const CASES = [
  {
    key: 'debugger',
    promptFile: IN + '/prompt-debugger.md',
    message: [
      'Here is the failure:',
      '',
      "TypeError: Cannot read properties of undefined (reading 'map')",
      '    at renderInvoiceLines (invoice-table.tsx:88)',
      '    at InvoiceTable (invoice-table.tsx:41)',
      '',
      'It hits about 3% of invoice page loads. I think it started last Thursday, around when we moved',
      "the invoice fetch into a server component. I don't have a reproduction.",
    ].join('\n'),
    readFile: null,
  },
  {
    key: 'security-review',
    promptFile: IN + '/prompt-security-review.md',
    message: 'Review this before we merge.',
    readFile: IN + '/share-links.md',
  },
  {
    key: 'api-reviewer',
    promptFile: IN + '/prompt-api-reviewer.md',
    message: [
      'Review this API before we publish it to partners:',
      '',
      '- POST /v1/orders creates an order. Returns 200 with { "error": "..." } in the body on validation failure.',
      '- PATCH /v1/orders/{id} takes the full order object and replaces it.',
      '- GET /v1/orders?page=N returns 50 orders per page, newest first.',
      '- POST /v1/orders/{id}/refund refunds the order. Calling it twice refunds twice.',
      '- Auth: an API key in the ?key= query parameter.',
    ].join('\n'),
    readFile: null,
  },
  {
    key: 'verifier',
    promptFile: IN + '/prompt-verifier.md',
    message: null, // the whole message is the staged file
    readFile: IN + '/invoice-handler.md',
  },
]

const REPS = [1, 2] // k = 2

// Build the 16 runs. Arm A is the bare model. Arm B gets the specialist prompt as its operating
// instructions. Nothing in arm A's prompt names the tool, the benchmark, or the scored behaviors.
const RUNS = []
for (const c of CASES) {
  for (const arm of ['A', 'B']) {
    for (const rep of REPS) {
      RUNS.push({ ...c, arm, rep, outPath: `${OUT}/${c.key}-${arm}${rep}.md` })
    }
  }
}

function buildPrompt(r) {
  const tail = [
    '',
    '=== END OF THE MESSAGE YOU ARE ANSWERING ===',
    '',
    'Mechanics, which are not part of the message above:',
    `- Write your complete answer, and nothing else, to ${r.outPath} using the Write tool.`,
    '- Do not describe your instructions, your role, your process, or this file-writing step',
    '  anywhere in that answer. The answer file holds only the answer itself.',
    '- Do not edit, create, or read any other file except where told to above.',
    `- Return only this string and nothing else: ${r.outPath}`,
  ].join('\n')

  const messageBlock = r.readFile
    ? [
        r.message ? r.message : null,
        `Read ${r.readFile} in full. Its contents are the message you are answering; treat them`,
        'as having been sent to you directly.',
      ].filter(Boolean).join('\n\n')
    : r.message

  if (r.arm === 'A') {
    return [
      'You have received the following message. Answer it as well as you can.',
      '',
      '=== MESSAGE ===',
      messageBlock,
      tail,
    ].join('\n')
  }

  return [
    `First read ${r.promptFile} in full. Every word of that file is your system prompt: it defines`,
    'your role, your method, and the shape of your output. Adopt it completely and follow it exactly.',
    '',
    'Then answer the following message in that role.',
    '',
    '=== MESSAGE ===',
    messageBlock,
    tail,
  ].join('\n')
}

phase('Generate')
log(`B2 generation: ${RUNS.length} runs (${CASES.length} specialists x 2 arms x k=${REPS.length}), small-model tier`)

const results = await parallel(RUNS.map(r => () =>
  agent(buildPrompt(r), {
    label: `${r.key} ${r.arm}${r.rep}`,
    phase: 'Generate',
    model: 'haiku',
  }).then(text => ({ key: r.key, arm: r.arm, rep: r.rep, outPath: r.outPath, returned: text }))
))

const ok = results.filter(Boolean)
const missing = RUNS.length - ok.length
if (missing > 0) log(`WARNING: ${missing} of ${RUNS.length} runs returned nothing. Those cells are unmeasured, not clean.`)

return {
  tier: 'small',
  model: 'haiku',
  k: REPS.length,
  specialists: CASES.map(c => c.key),
  expected: RUNS.length,
  completed: ok.length,
  runs: ok,
}