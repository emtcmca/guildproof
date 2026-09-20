export const meta = {
  name: 'guildproof-b2-frontier',
  description: 'B2 frontier tier: same 4 specialists, bare vs guildproof, k=2, on the session frontier model',
  phases: [
    { title: 'Generate', detail: '16 runs on the frontier model, raw outputs written to disk' },
  ],
}

const OUT = 'C:/Users/tetzl/AppData/Local/Temp/claude/C--dev-quartermaster/c3866379-a6fb-42c6-92da-3078008716bb/scratchpad/b2-run/out-frontier'
const IN = 'C:/Users/tetzl/AppData/Local/Temp/claude/C--dev-quartermaster/c3866379-a6fb-42c6-92da-3078008716bb/scratchpad/b2-run/inputs'

// Identical to the small-tier run. Same staged inputs, same wording, same k.
// The ONLY variable changed is the model, so the two runs are comparable.
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
    message: null,
    readFile: IN + '/invoice-handler.md',
  },
]

const REPS = [1, 2]

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
log(`B2 frontier tier: ${RUNS.length} runs, same inputs and wording as the small-tier run`)

const results = await parallel(RUNS.map(r => () =>
  agent(buildPrompt(r), {
    label: `${r.key} ${r.arm}${r.rep}`,
    phase: 'Generate',
  }).then(text => ({ key: r.key, arm: r.arm, rep: r.rep, outPath: r.outPath, returned: text }))
))

const ok = results.filter(Boolean)
if (ok.length < RUNS.length) log(`WARNING: ${RUNS.length - ok.length} of ${RUNS.length} runs returned nothing. Those cells are unmeasured, not clean.`)

return { tier: 'frontier', k: REPS.length, expected: RUNS.length, completed: ok.length, runs: ok }