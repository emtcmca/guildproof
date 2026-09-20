#!/usr/bin/env node
/**
 * validate.mjs — structure validator for this Claude Code plugin repo.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * The repeat failure mode here is not a broken build. It is a *published number that does
 * not match what is on disk*: a launch draft that said 27 agents when 20 shipped, docs that
 * said 20 while a working tree held 23, a subagent that reported 40 eval cases against 37
 * because it counted the wrong branch, and a README line that said "Copy four things" above
 * a five-row table. None of those break anything at runtime, so nothing catches them. They
 * reach a reader instead.
 *
 * This script turns that class of defect into a failing exit code. It counts what is
 * actually on disk, finds every place prose states a count, and compares them.
 *
 * ZERO DEPENDENCIES. Node built-ins only (node:fs, node:path, node:url, node:os).
 * Run it with:   node scripts/validate.mjs
 * Prove it works: node scripts/validate.mjs --selftest
 *
 * EXIT CODES
 *   0 = no errors (warnings may still print)
 *   1 = at least one error
 *
 * A NOTE ON READING THE OUTPUT
 * Every finding names `file:line` and says what the value is versus what it should be.
 * Warnings are things a human should look at; they never fail the run on their own.
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..');

// ---------------------------------------------------------------------------
// 1. What is countable, and where it lives.
//
// Each entry is a directory whose file count prose keeps making claims about.
// `glob` is the filename test — note known-bad uses the SAME test the Python
// runner uses (`KB*.md`), which is also what excludes that folder's README.md.
// ---------------------------------------------------------------------------
const COUNTABLE = {
  agents:    { dir: 'agents',            test: (f) => f.endsWith('.md'), label: 'agent files' },
  commands:  { dir: 'commands',          test: (f) => f.endsWith('.md'), label: 'command files' },
  lenses:    { dir: 'lenses',            test: (f) => f.endsWith('.md'), label: 'lens files' },
  templates: { dir: 'templates',         test: (f) => f.endsWith('.md'), label: 'template files' },
  evalCases: { dir: 'evals/cases',       test: (f) => f.endsWith('.md'), label: 'eval case files' },
  knownBad:  { dir: 'evals/known-bad',   test: (f) => /^KB.*\.md$/.test(f), label: 'known-bad KB fixtures' },
};

// ---------------------------------------------------------------------------
// 2. Scope: which files the scanning checks are allowed to look at.
//
// HISTORY_DIRS are dated records. A scorecard written in June is *supposed* to
// say what it said in June; "correcting" it would falsify the record. So counts,
// dead command names and phantom paths inside them are not defects.
//
// PRESERVED_FILES are docs that were written under the plugin's old name
// (`promptsmith`, renamed to `guildproof` 2026-09-18) and each carries a notice
// at the top saying it deliberately keeps the old name. Verified 2026-09-20:
// all four carry that notice. The exemption is re-derived from the notice text
// at runtime (see `isPreserved`), and if the notice ever disappears from one of
// these files the exemption is reported as no longer justified — an exemption
// that can rot silently is the same bug class this script exists to catch.
// ---------------------------------------------------------------------------
const HISTORY_DIRS = ['evals/runs', 'docs/test-runs'];
const PRESERVED_FILES = [
  'ROADMAP.md',
  'docs/launch-plan.md',
  'docs/planned-features.md',
  'docs/coverage-gaps.md',
];
const RENAME_NOTICE = /this (?:document|project) (?:is a record )?(?:was|written|keeps)|keeps the old name/i;

// Directories never scanned at all: git internals, binary assets, this script's
// own folder (its selftest fixtures contain deliberately broken text and dead
// command names on purpose, so scanning them would flag the fixtures).
const SKIP_DIRS = new Set(['.git', 'node_modules', 'scripts', 'assets', '.work']);

const SCAN_EXT = new Set(['.md', '.json', '.py', '.yml', '.yaml', '.txt']);

// Files whose count claims are ERRORS. These are the reader-facing surfaces:
// a wrong number here is a wrong number in front of a user.
const COUNT_ERROR_FILES = [
  'README.md',
  'AGENTS.md',
  '.claude-plugin/plugin.json',
  '.claude-plugin/marketplace.json',
  'docs/COMMAND-SHEET.md',
  'docs/agent-gallery.md',
  // Added after this check's first real run, which found CONTRIBUTING.md carrying the same
  // stale "37-case" number as the command sheet. It is the first file a would-be
  // contributor opens, so a wrong count there is as public as one in the README.
  'CONTRIBUTING.md',
  // Added 2026-09-20 after it was caught carrying "over 27 cases" against 38 on disk, wrapped
  // across a line break so the per-line scan never saw it. It is the how-to a new installer is
  // sent to, so a wrong count there is in front of a user.
  'docs/USING-GUILDPROOF.md',
  // Added 2026-09-20. This file told every reader "Thirteen of these prompts ship as
  // host-agnostic skills" when 22 do, at the exact moment they are deciding whether their host
  // is covered. It went unflagged because "prompts" maps to no tracked directory, so the claim
  // was rewritten to "All twenty gallery specialists", which does.
  '.github/ISSUE_TEMPLATE/config.yml',
];

// ---------------------------------------------------------------------------
// 3. Number words. Claims appear as digits ("20 agents") and as English words
//    ("four commands", "Copy five things", "twenty gallery specialists"), so
//    both have to parse to the same integer.
// ---------------------------------------------------------------------------
const UNITS = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20,
};
const TENS = { twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90 };

const UNIT_ALT = Object.keys(UNITS).sort((a, b) => b.length - a.length).join('|');
const TENS_ALT = Object.keys(TENS).join('|');
// Source fragment reused inside every claim pattern below.
// The leading lookbehind matters: without it "standalone" ends in "one" and the
// scanner reads "standalone commands" as a claim that one command ships. That was
// a real false positive on the first run of this script.
const NUM = `(?<![A-Za-z0-9-])(?:\\d{1,4}|(?:${TENS_ALT})(?:[-\\s](?:${UNIT_ALT}))?|${UNIT_ALT})(?![A-Za-z])`;

/** Turn "12", "twelve" or "twenty-two" into a Number. Returns null if unparseable. */
function parseCount(token) {
  const t = String(token).trim().toLowerCase();
  if (/^\d+$/.test(t)) return Number(t);
  const parts = t.split(/[-\s]+/);
  if (parts.length === 1) return UNITS[parts[0]] ?? TENS[parts[0]] ?? null;
  if (parts.length === 2 && TENS[parts[0]] != null && UNITS[parts[1]] != null) {
    return TENS[parts[0]] + UNITS[parts[1]];
  }
  return null;
}

// ---------------------------------------------------------------------------
// 4. Claim patterns: how this repo actually phrases its counts.
//    Read off the real files, not invented — e.g. plugin.json says "a guild of
//    20 specialist agents" and "six known-bad fixtures"; AGENTS.md says "the 20
//    specialist prompts" and "the 12 review checklists"; README says "a 20-agent
//    specialist gallery" and "All twenty gallery specialists".
//
// `needsMarker` is the whole reason this check is usable.
//
// A bare "N <noun>" is usually NOT an inventory claim. "two agents both assumed
// the other owned it", "one gallery agent", "auto-pick 1-3 lenses", "the core
// three commands" are all ordinary prose. The first version of this script had no
// marker rule and reported 60+ findings of that kind, which buries the one that
// matters. So a bare pattern only counts as a claim when the text immediately
// before the number marks it as THE shipped set: a definite determiner ("the 4
// commands", "All twenty gallery specialists", "all 37 cases"), an opening bold
// ("**Four commands**"), or a collection noun introducing it ("Gallery (20
// specialists"). Patterns whose own wording is already inventory-specific — a
// gallery, a roster, a guild, built-ins, review checklists, known-bad fixtures —
// need no marker.
//
// `allowSingular` exists for attributive compounds: "a 20-agent gallery" counts
// twenty agents even though the word is singular, while a bare singular ("one
// agent", "seven agent outputs") never states an inventory.
// ---------------------------------------------------------------------------
const CLAIM_PATTERNS = [
  // --- inherently inventory-specific wording: no marker required -------------
  { target: 'agents',    needsMarker: false, re: new RegExp(`(${NUM})[-\\s]agents?\\s+(?:\\w+\\s+)?(?:gallery|roster|guild)\\b`, 'gi') },
  { target: 'agents',    needsMarker: false, re: new RegExp(`(?:gallery|roster|guild)\\s+of\\s+(${NUM})\\s+(?:specialist\\s+)?(?:agents?|specialists?|prompts?)\\b`, 'gi') },
  { target: 'agents',    needsMarker: false, re: new RegExp(`(${NUM})\\s+specialist\\s+(?:agents?|prompts?)\\b`, 'gi') },
  { target: 'lenses',    needsMarker: false, re: new RegExp(`(${NUM})\\s+(?:built-in|expert)(?:\\s+expert)?\\s+lenses\\b`, 'gi') },
  { target: 'lenses',    needsMarker: false, re: new RegExp(`(${NUM})\\s+built-ins?\\b`, 'gi') },
  { target: 'lenses',    needsMarker: false, re: new RegExp(`(${NUM})\\s+review\\s+checklists\\b`, 'gi') },
  // "known-bad" must be followed by the thing being counted. Bare `N known-bad` also matched
  // "12 known-bad cells", which is 12 judge scorings of 6 fixtures, and reported it as a claim
  // that 12 fixtures exist. Cells, runs and scorings are all legitimately more numerous than
  // fixtures, so the noun has to be named.
  { target: 'knownBad',  needsMarker: false, re: new RegExp(`(${NUM})\\s+known-bad\\s+(?:regression\\s+)?fixtures?\\b`, 'gi') },
  { target: 'knownBad',  needsMarker: false, re: new RegExp(`(${NUM})\\s+KB\\s+fixtures?\\b`, 'gi') },
  { target: 'knownBad',  needsMarker: false, re: new RegExp(`(${NUM})\\s+(?:deliberately-broken\\s+)?calibration\\s+fixtures?\\b`, 'gi') },
  { target: 'evalCases', needsMarker: false, re: new RegExp(`(${NUM})[-\\s]case\\s+(?:regression\\s+)?suite\\b`, 'gi') },
  // --- bare wording: only a claim when the text before it marks the set -----
  { target: 'agents',    needsMarker: true,  re: new RegExp(`(${NUM})\\s+agents\\b`, 'gi') },
  { target: 'agents',    needsMarker: true,  re: new RegExp(`(${NUM})\\s+(?:gallery\\s+)?specialists\\b`, 'gi') },
  { target: 'commands',  needsMarker: true,  re: new RegExp(`(${NUM})\\s+commands\\b`, 'gi') },
  { target: 'lenses',    needsMarker: true,  re: new RegExp(`(${NUM})\\s+lenses\\b`, 'gi') },
  { target: 'templates', needsMarker: true,  re: new RegExp(`(${NUM})\\s+(?:output\\s+)?templates\\b`, 'gi') },
  { target: 'evalCases', needsMarker: true,  re: new RegExp(`(${NUM})[-\\s](?:eval\\s+)?cases\\b`, 'gi') },
];

/**
 * Does the text immediately before the number mark this as THE shipped set?
 * Only the tail of the preceding text counts — "the core three commands" must NOT
 * qualify, because "the" attaches to "core", not to the number.
 */
// `over` earns its place here: "an adversarial skeptic rubric over 27 cases" is an inventory
// claim about the suite, and it sat stale in docs/USING-GUILDPROOF.md against 38 on disk because
// nothing marked it as one. The risk of a false positive from `over` is low, because a claim only
// counts at all when its noun maps to a real tracked directory.
const MARKER_TAIL = /(?:\b(?:the|all|its|these|those|over)\s+(?:\*\*)?|\*\*|\b(?:gallery|roster|guild|suite|library)\s*[(:\-–—]\s*)$/i;
function hasInventoryMarker(line, index) {
  return MARKER_TAIL.test(line.slice(Math.max(0, index - 30), index));
}

// A table row of the form `| Expert lenses | 12 | lenses/ |` is also a count claim.
// First cell names the component, second cell is a bare number (AGENTS.md does this).
const TABLE_COUNT_ROW = /^\|\s*([^|]+?)\s*\|\s*(\d{1,4})\s*\|/;
const TABLE_LABEL_TO_TARGET = [
  [/known[-\s]?bad|calibration/i, 'knownBad'],
  [/eval\s+case/i, 'evalCases'],
  [/command/i, 'commands'],
  [/lens|lenses/i, 'lenses'],
  [/template/i, 'templates'],
  [/agent|specialist/i, 'agents'],
];

/**
 * Lines that LOOK like an inventory claim but are not one.
 *
 * These are not cosmetic. Without them the check drowns in false positives and
 * a drowning check gets ignored, which is worse than no check:
 *   - "a live run of 7 specialists plus 1 independent verifier"  → a record of
 *     one run, not a claim about how many agents ship.
 *   - "auto-run <=3 agents/low-risk"                             → a threshold.
 *   - "(7 agents > the smart threshold)"                         → a comparison.
 *   - "installs 22 skills ... npx skills add emtcmca/..."        → a DIFFERENT
 *     repo's inventory (the skills mirror), not this one's.
 * Every suppressed match is still printed under "suppressed candidates" so the
 * suppression itself is auditable rather than invisible.
 */
const CLAIM_DISQUALIFIERS = [
  { re: /live run|logged in `evals\/runs/i, why: 'describes one logged run, not the shipped inventory' },
  { re: /[≤≥<>]=?\s*\d|\bthreshold\b/i, why: 'a threshold or comparison, not an inventory count' },
  { re: /guildproof-skills|npx skills|skills mirror|distribution mirror/i, why: "the skills mirror repo's inventory, not this repo's" },
];

/**
 * Files whose counts are historical statements, not claims about right now.
 *
 * CHANGELOG.md says what a past release added ("Four eval cases and one live
 * seven-agent run"); a dated plan says what the roster looked like when the plan
 * was written. Re-pointing those at today's numbers would falsify the record,
 * which is the same defect in the other direction. PRESERVED_FILES are excluded
 * for the same reason and are listed above.
 */
const COUNT_EXEMPT_FILES = new Set(['CHANGELOG.md']);

// ---------------------------------------------------------------------------
// Findings plumbing
// ---------------------------------------------------------------------------
/** @typedef {{level:'error'|'warn', check:string, file:string, line:number|null, msg:string}} Finding */

function makeCtx(root) {
  return { root, findings: /** @type {Finding[]} */ ([]), suppressed: [], seen: new Set() };
}
function add(ctx, level, check, file, line, msg) {
  // Deduped: several patterns can legitimately land on the same defect, and the
  // same file can be scanned by more than one check. Reporting one defect twice
  // makes the output look worse than the repo is.
  const key = `${level}|${check}|${file}|${line}|${msg}`;
  if (ctx.seen.has(key)) return;
  ctx.seen.add(key);
  ctx.findings.push({ level, check, file, line, msg });
}

// ---------------------------------------------------------------------------
// Filesystem helpers
// ---------------------------------------------------------------------------
function exists(p) { try { fs.statSync(p); return true; } catch { return false; } }

function readLines(abs) {
  // Split on \n after stripping \r so CRLF files report the same line numbers as LF ones.
  return fs.readFileSync(abs, 'utf8').replace(/\r\n?/g, '\n').split('\n');
}

/** All files under root, as repo-relative POSIX paths, minus SKIP_DIRS. */
function walk(root, rel = '', out = []) {
  const abs = path.join(root, rel);
  let entries;
  try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const childRel = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) {
      if (SKIP_DIRS.has(e.name)) continue;
      walk(root, childRel, out);
    } else if (e.isFile()) {
      out.push(childRel);
    }
  }
  return out;
}

function isHistory(rel) { return HISTORY_DIRS.some((d) => rel === d || rel.startsWith(`${d}/`)); }

/** True when this file self-declares that it preserves the plugin's old name. */
function isPreserved(ctx, rel) {
  if (!PRESERVED_FILES.includes(rel)) return false;
  const abs = path.join(ctx.root, rel);
  if (!exists(abs)) return false;
  const head = readLines(abs).slice(0, 12).join('\n');
  if (RENAME_NOTICE.test(head) || /renamed/i.test(head)) return true;
  // The exemption's own justification is gone. Say so instead of exempting silently.
  add(ctx, 'warn', 'namespace', rel, 1,
    'this file is on the old-name exemption list but no longer carries the "Renamed." notice ' +
    'that justified the exemption — either restore the notice or drop it from PRESERVED_FILES ' +
    'in scripts/validate.mjs');
  return true;
}

function countInventory(ctx) {
  const inv = {};
  for (const [key, spec] of Object.entries(COUNTABLE)) {
    const abs = path.join(ctx.root, spec.dir);
    if (!exists(abs)) { inv[key] = null; continue; }
    inv[key] = fs.readdirSync(abs).filter((f) => {
      return fs.statSync(path.join(abs, f)).isFile() && spec.test(f);
    }).length;
  }
  return inv;
}

// ===========================================================================
// CHECK 1 — counts on disk vs counts claimed in prose
// ===========================================================================
function checkCounts(ctx, inv) {
  const scanned = walk(ctx.root).filter((rel) => {
    if (!SCAN_EXT.has(path.extname(rel))) return false;
    if (isHistory(rel)) return false;
    if (COUNT_EXEMPT_FILES.has(rel)) return false;
    if (isPreserved(ctx, rel)) return false;
    return true;
  });

  for (const rel of scanned) {
    const isErrorFile = COUNT_ERROR_FILES.includes(rel);
    const lines = readLines(path.join(ctx.root, rel));
    const seen = new Set(); // dedupe: two patterns can match the same claim on one line

    lines.forEach((rawLine, i) => {
      const lineNo = i + 1;
      // Scan the line joined to the next one, because these docs are hard-wrapped and a claim
      // splits across the break. `docs/USING-GUILDPROOF.md` said "over 27" at the end of one
      // line and "cases." at the start of the next, against 38 cases on disk. A per-line regex
      // cannot see that, so the stale count sat in a reader-facing doc while this checker
      // reported the file clean. A wrapped claim is still a claim.
      //
      // Reporting stays on the FIRST line, where the number is. Findings that were already
      // visible on one line dedupe against the single-line pass via `seen`, so joining cannot
      // double-report.
      // Join ONLY when this line ends with a number, which is the only way a claim can be split
      // by the wrap. Joining unconditionally was tried first and was a net loss: it produced two
      // false positives by manufacturing adjacencies that do not exist in the prose, and caught
      // nothing. Narrowing it to a trailing number targets the real case and nothing else.
      const wraps = new RegExp(`(?:${NUM})\\s*$`, 'i').test(rawLine);
      const line = wraps && i + 1 < lines.length ? `${rawLine} ${lines[i + 1].trim()}` : rawLine;
      const disq = CLAIM_DISQUALIFIERS.find((d) => d.re.test(line));

      const hits = [];

      for (const { target, re, needsMarker } of CLAIM_PATTERNS) {
        re.lastIndex = 0;
        let m;
        while ((m = re.exec(line)) !== null) {
          const claimed = parseCount(m[1]);
          if (claimed == null) continue;
          // A bare "N <noun>" needs the text before it to mark the shipped set.
          if (needsMarker && !hasInventoryMarker(line, m.index)) continue;
          // "Three of the four specialists" counts a subset, not the inventory.
          if (isSubsetDenominator(line, m.index)) continue;
          hits.push({ target, claimed, text: m[0].trim() });
        }
      }

      const tm = TABLE_COUNT_ROW.exec(line);
      if (tm) {
        const label = tm[1];
        const entry = TABLE_LABEL_TO_TARGET.find(([re]) => re.test(label));
        if (entry) hits.push({ target: entry[1], claimed: Number(tm[2]), text: `| ${label.trim()} | ${tm[2]} |` });
      }

      for (const hit of hits) {
        const actual = inv[hit.target];
        if (actual == null) continue; // that directory does not exist here
        const key = `${rel}:${lineNo}:${hit.target}:${hit.claimed}`;
        if (seen.has(key)) continue;
        seen.add(key);
        if (hit.claimed === actual) continue;

        if (disq) {
          ctx.suppressed.push(
            `${rel}:${lineNo} — "${hit.text}" reads as ${hit.claimed} ${hit.target}, on disk ${actual} ` +
            `— SUPPRESSED: ${disq.why}`);
          continue;
        }
        const spec = COUNTABLE[hit.target];
        add(ctx, isErrorFile ? 'error' : 'warn', 'counts', rel, lineNo,
          `claimed ${hit.claimed} — actual ${actual}. The text "${hit.text}" states ${hit.claimed} ` +
          `but ${spec.dir}/ holds ${actual} ${spec.label}. Change the text to ${actual}, or add the ` +
          `missing file(s).`);
      }
    });
  }
}

// ===========================================================================
// CHECK 2 — a markdown table whose row count contradicts the sentence above it
//
// This is the "Copy four things / five rows" bug, generalised.
//
// Precision rule, stated plainly because it is where this check could go wrong:
// a count near a table is only treated as a claim ABOUT that table when either
//   (a) the count sits on the last non-blank line before the table AND that line
//       ends with a colon — i.e. it is literally introducing the table, or
//   (b) the counted noun is a generic row noun (things, rows, items, ...).
// Without that rule, "Twelve models. Three vendors." two lines above an unrelated
// six-row table reads as a contradiction, and it is not one.
// The known weakness: an introducing sentence that omits its colon and counts a
// domain noun is missed. That is a deliberate trade for near-zero false alarms.
// ===========================================================================
const ROW_NOUNS = /\b(things?|rows?|items?|entries|steps?|options?|ways?|columns?|files?|directories|dirs?|checks?)\b/i;
const TABLE_ROW = /^\s*\|/;
const TABLE_SEP = /^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$/;

/**
 * Is this number the denominator of a subset statement rather than an inventory claim?
 *
 * "Four of the six items", "Three of the four specialists", "two of 12 lenses" — in every one of
 * those the second number describes a SUBSET being drawn from, not a claim about how many exist
 * in the repo. Reading it as an inventory count produces a confident, wrong finding: the first
 * real run of this checker reported "four specialists" as contradicting the 20 files in agents/,
 * when the sentence was about the four that carry a benchmark.
 *
 * A checker that cries wolf gets ignored, and an ignored checker is worse than no checker,
 * because it also carries the false assurance that something is being watched.
 */
function isSubsetDenominator(line, numberIndex) {
  const before = line.slice(0, numberIndex);
  return /\b(?:of|out of)\s+(?:the\s+)?$/i.test(before);
}

function checkTableRows(ctx) {
  const files = walk(ctx.root).filter((rel) => rel.endsWith('.md') && !isHistory(rel));

  for (const rel of files) {
    const lines = readLines(path.join(ctx.root, rel));

    for (let i = 0; i < lines.length; i++) {
      if (!TABLE_ROW.test(lines[i])) continue;
      if (!(i + 1 < lines.length && TABLE_SEP.test(lines[i + 1]))) continue; // header+separator = a real table

      // Count data rows: everything after the separator that still starts with |
      let dataRows = 0;
      let j = i + 2;
      while (j < lines.length && TABLE_ROW.test(lines[j])) { dataRows++; j++; }

      // Walk back over up to 3 non-blank lines looking for the introducing count.
      const intro = [];
      for (let k = i - 1; k >= 0 && intro.length < 3; k--) {
        if (lines[k].trim() === '') { if (intro.length) break; else continue; }
        intro.push({ line: lines[k], no: k + 1, isImmediate: intro.length === 0 });
      }

      for (const cand of intro) {
        const introducesTable = cand.isImmediate && /:\s*$/.test(cand.line.trim());
        const re = new RegExp(`(${NUM})\\s+([A-Za-z-]+)`, 'gi');
        let m;
        while ((m = re.exec(cand.line)) !== null) {
          const claimed = parseCount(m[1]);
          if (claimed == null) continue;
          const noun = m[2];
          // A row-noun anywhere in the look-back window is not enough. The count has to be on
          // the line IMMEDIATELY before the table to be introducing it. Without this, "Four of
          // the six items are satisfiable by..." two lines above a 2-row table that GROUPS those
          // six into two categories reported a contradiction that was not there.
          const qualifies = cand.isImmediate && (introducesTable || ROW_NOUNS.test(noun));
          if (!qualifies) continue;
          if (isSubsetDenominator(cand.line, m.index)) continue;
          if (claimed === dataRows) continue;
          add(ctx, 'error', 'table-rows', rel, cand.no,
            `claimed ${claimed} — actual ${dataRows}. The line says "${m[0].trim()}" and the table ` +
            `immediately below it (starting line ${i + 1}) has ${dataRows} data rows, not counting the ` +
            `header or the |---| separator. Fix whichever is wrong: the sentence or the table.`);
        }
      }
      i = j - 1; // do not re-scan this table's own rows
    }
  }
}

// ===========================================================================
// CHECK 3 — required frontmatter on agents/ and lenses/
//
// WHICH FIELDS, AND WHY THESE:
//
// agents/  -> name, description, role, voice, lenses
//   Read from all 20 agent files plus the format contract in docs/agent-gallery.md.
//   That doc states the block explicitly (`name`, `description`, `role`, `voice`,
//   `lenses`) and says of one of them: "`description` is not optional and not
//   decorative. It is the only frontmatter field the host uses to auto-select an
//   agent by task context" — an agent shipped without it still loads but can never
//   be matched to a task. `role`, `voice` and `lenses` are the plugin's own schema
//   and are what `/forge-agent` seeds from; all 20 files carry all five, so the
//   observed set and the documented set agree. Requiring the intersection would be
//   weaker than what the repo actually holds, so the full five are required.
//
// lenses/  -> name, applies-to
//   The format block in README.md ("Add your own lens") shows exactly these two,
//   and `applies-to` is load-bearing: it is what auto-selects a lens by topic, so a
//   lens without it is reachable only when named explicitly. All 12 carry both.
// ===========================================================================
const FRONTMATTER_REQUIRED = {
  agents: ['name', 'description', 'role', 'voice', 'lenses'],
  lenses: ['name', 'applies-to'],
};

function parseFrontmatter(lines) {
  if (lines[0]?.trim() !== '---') return null;
  const end = lines.findIndex((l, idx) => idx > 0 && l.trim() === '---');
  if (end === -1) return null;
  const keys = new Map();
  for (let i = 1; i < end; i++) {
    const m = /^([A-Za-z_][A-Za-z0-9_-]*)\s*:/.exec(lines[i]);
    if (m) keys.set(m[1], i + 1);
  }
  return { keys, endLine: end + 1 };
}

function checkFrontmatter(ctx) {
  for (const [dirKey, required] of Object.entries(FRONTMATTER_REQUIRED)) {
    const dir = COUNTABLE[dirKey].dir;
    const abs = path.join(ctx.root, dir);
    if (!exists(abs)) continue;
    for (const f of fs.readdirSync(abs).filter((f) => f.endsWith('.md'))) {
      const rel = `${dir}/${f}`;
      const lines = readLines(path.join(abs, f));
      const fm = parseFrontmatter(lines);
      if (!fm) {
        add(ctx, 'error', 'frontmatter', rel, 1,
          `no YAML frontmatter block. Every file in ${dir}/ must open with a --- fenced block ` +
          `containing: ${required.join(', ')}. Line 1 is "${(lines[0] ?? '').slice(0, 40)}".`);
        continue;
      }
      const missing = required.filter((k) => !fm.keys.has(k));
      if (missing.length) {
        add(ctx, 'error', 'frontmatter', rel, 1,
          `frontmatter is missing: ${missing.join(', ')}. Required in ${dir}/: ${required.join(', ')}. ` +
          `Present: ${[...fm.keys.keys()].join(', ') || '(none)'}.`);
      }
      const nameLine = fm.keys.get('name');
      if (nameLine) {
        const declared = lines[nameLine - 1].split(':').slice(1).join(':').trim().replace(/^["']|["']$/g, '');
        const expected = f.replace(/\.md$/, '');
        if (declared && declared !== expected) {
          add(ctx, 'error', 'frontmatter', rel, nameLine,
            `frontmatter name is "${declared}" but the filename says "${expected}". The two must match ` +
            `— docs and routing refer to agents and lenses by one name, and a mismatch makes one of ` +
            `them a phantom reference.`);
        }
      }
    }
  }
}

// ===========================================================================
// CHECK 4 — no phantom references
//
// Every agent named in the reader-facing docs and in /orchestrate's routing must
// exist as a file in agents/; every lens named must exist in lenses/.
//
// Candidate extraction is deliberately structural rather than "any word that
// looks like a name". Four unambiguous shapes are used:
//   (a) an explicit path, `agents/<name>.md` or `lenses/<name>.md`
//   (b) the first column of the gallery table in docs/agent-gallery.md
//   (c) a roster bullet: `- **Build:** feature-spec · planner · ...`
//   (d) a `--lens a,b` argument anywhere in the live docs
// Plus (e) backticked bare names in the two orchestration files, restricted to
// lines that mention an agent, since that is where routing names live.
// ===========================================================================
const ORCH_FILES = ['skills/orchestration/SKILL.md', 'commands/orchestrate.md'];
// Hyphenated English compounds and vocabulary that appear backticked in the
// orchestration files but are not agent names. Kept short on purpose: if this
// list has to grow much, the candidate rule is wrong and should be narrowed.
const NOT_AGENT_NAMES = new Set([
  'read-only', 'low-risk', 'non-overlapping', 'zero-call', 'paste-anywhere',
  'sharpen', 'lens', 'orchestrate', 'forge-agent', 'compact', 'stat',
  'prompt-engineering', 'orchestration', 'agent-gallery', 'coverage-gaps',
]);
// Metasyntactic stand-ins that appear where a lens name would go, e.g. the
// `usage:` line "[--lens name,name]" or the README's "--lens my-lens" example.
const LENS_PLACEHOLDERS = new Set(['name', 'names', 'a', 'b', 'x', 'y', 'lens', 'lenses', 'my-lens', 'lens-a', 'lens-b', 'v1', 'v2']);

function listNames(ctx, dirKey) {
  const dir = COUNTABLE[dirKey].dir;
  const abs = path.join(ctx.root, dir);
  if (!exists(abs)) return new Set();
  return new Set(fs.readdirSync(abs).filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, '')));
}

function checkPhantoms(ctx) {
  const agentNames = listNames(ctx, 'agents');
  const lensNames = listNames(ctx, 'lenses');

  const liveFiles = walk(ctx.root).filter((rel) => {
    if (!SCAN_EXT.has(path.extname(rel))) return false;
    if (isHistory(rel)) return false;
    if (isPreserved(ctx, rel)) return false;
    return true;
  });

  const report = (rel, lineNo, kind, name, dir, known) => {
    add(ctx, 'error', 'phantom', rel, lineNo,
      `phantom ${kind} reference "${name}" — no such file ${dir}/${name}.md. Either the name is ` +
      `misspelled here or the file was renamed or removed. What ${dir}/ actually holds: ` +
      `${[...known].sort().join(', ')}.`);
  };

  for (const rel of liveFiles) {
    const lines = readLines(path.join(ctx.root, rel));
    const inGallery = rel === 'docs/agent-gallery.md';
    const inOrch = ORCH_FILES.includes(rel);

    lines.forEach((line, i) => {
      const lineNo = i + 1;

      // (a) explicit paths
      for (const m of line.matchAll(/\bagents\/([a-z0-9][a-z0-9-]*)\.md\b/g)) {
        if (!agentNames.has(m[1])) report(rel, lineNo, 'agent', m[1], 'agents', agentNames);
      }
      for (const m of line.matchAll(/\blenses\/([a-z0-9][a-z0-9-]*)\.md\b/g)) {
        if (!lensNames.has(m[1])) report(rel, lineNo, 'lens', m[1], 'lenses', lensNames);
      }

      // (b) the gallery table's first column, e.g. "| `feature-spec` | turns ... |"
      if (inGallery) {
        const m = /^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|/.exec(line);
        if (m && !agentNames.has(m[1])) report(rel, lineNo, 'agent', m[1], 'agents', agentNames);
      }

      // (c) roster bullets: "- **Build:** `a`, `b`" or "- **Build:** a · b · c"
      const roster = /^[-*]\s*\*\*(Build|Review|Write|Meta|Gallery)[:\s]*\*\*:?\s*(.+)$/i.exec(line);
      if (roster) {
        for (const raw of roster[2].split(/[,·|]/)) {
          const name = raw.trim().replace(/`/g, '').trim();
          if (/^[a-z0-9][a-z0-9-]*$/.test(name) && !agentNames.has(name)) {
            report(rel, lineNo, 'agent', name, 'agents', agentNames);
          }
        }
      }

      // (d) --lens arguments. The commands' own `usage:` strings show the FORM of
      // the flag ("--lens name,name"), so metasyntactic placeholders are skipped —
      // they are not claims that a lens called "name" exists.
      for (const m of line.matchAll(/--lens\s+([a-z0-9][a-z0-9,-]*)/g)) {
        for (const name of m[1].split(',')) {
          const n = name.trim();
          if (!n || LENS_PLACEHOLDERS.has(n)) continue;
          if (!lensNames.has(n)) report(rel, lineNo, 'lens', n, 'lenses', lensNames);
        }
      }

      // (e) backticked bare names on agent-ish lines in the orchestration files
      if (inOrch && /\bagent|gallery|specialist|dispatch|route/i.test(line)) {
        for (const m of line.matchAll(/`([a-z][a-z0-9-]*)`/g)) {
          const name = m[1];
          if (NOT_AGENT_NAMES.has(name) || lensNames.has(name)) continue;
          if (!name.includes('-') && !agentNames.has(name)) {
            // A single bare word is only claimed as an agent when it really is one
            // OR the line frames it as an agent ("the `foo` agent").
            const framed = new RegExp(`\`${name}\`\\s+agent|agent\\s+\`${name}\``, 'i').test(line);
            if (!framed) continue;
          }
          if (!agentNames.has(name)) report(rel, lineNo, 'agent', name, 'agents', agentNames);
        }
      }
    });
  }

  // Reverse coherence: an agent on disk that the gallery index never lists is
  // invisible to a reader. A warning, not an error — the spec asks for phantoms,
  // and this is the mirror image of one.
  const galleryAbs = path.join(ctx.root, 'docs/agent-gallery.md');
  if (exists(galleryAbs)) {
    const text = fs.readFileSync(galleryAbs, 'utf8');
    for (const name of [...agentNames].sort()) {
      if (!text.includes(name)) {
        add(ctx, 'warn', 'phantom', 'docs/agent-gallery.md', null,
          `agents/${name}.md exists on disk but is not listed in the gallery index. Add a row for it, ` +
          `or the roster a reader sees is smaller than the roster that ships.`);
      }
    }
  }
}

// ===========================================================================
// CHECK 5 — no dead command namespace
//
// The plugin was renamed promptsmith -> guildproof on 2026-09-18. A live
// `/promptsmith:` string tells a user to type a command that does not resolve.
//
// Exempt, all verified against the files on 2026-09-20:
//   * evals/runs/ and docs/test-runs/ — dated records of runs made under the old
//     name; editing them would falsify the record.
//   * ROADMAP.md, docs/launch-plan.md, docs/planned-features.md,
//     docs/coverage-gaps.md — each opens with a notice saying it is a record
//     written under the old name and keeps it deliberately. Re-derived at runtime.
//   * `promptsmith-lenses` / `promptsmith-agents` / `promptsmith-templates` —
//     NOT dead. commands/lens.md:56-57 and skills/prompt-engineering/SKILL.md:163
//     read these legacy folders on purpose so lenses a user already created are
//     not orphaned by the rename. Removing them would break existing installs.
// ===========================================================================
const DEAD_NAMESPACE = /\/promptsmith:/g;
const LEGACY_FALLBACK = /promptsmith-(?:lenses|agents|templates)/;
const RENAME_EXPLANATION = /was named|renamed|old name|until 2026-09/i;

function checkDeadNamespace(ctx) {
  const files = walk(ctx.root).filter((rel) => {
    if (!SCAN_EXT.has(path.extname(rel))) return false;
    if (isHistory(rel)) return false;
    if (isPreserved(ctx, rel)) return false;
    if (rel === 'CLAUDE.md') return false; // repo-local session state; names the worktree dir
    return true;
  });

  for (const rel of files) {
    const lines = readLines(path.join(ctx.root, rel));
    lines.forEach((line, i) => {
      DEAD_NAMESPACE.lastIndex = 0;
      if (DEAD_NAMESPACE.test(line)) {
        add(ctx, 'error', 'namespace', rel, i + 1,
          `dead command namespace "/promptsmith:" — the plugin is now "guildproof", so this tells a ` +
          `user to type a command that does not exist. Should be "/guildproof:". If this file is a ` +
          `dated record that must keep the old name, it needs the "Renamed." notice and an entry in ` +
          `PRESERVED_FILES in scripts/validate.mjs.`);
      }
      // Softer sweep: any other surviving mention of the old project name.
      // CHANGELOG.md is exempt from this half only — recording the rename and the
      // old paths it replaced is literally the file's job. The hard
      // "/promptsmith:" check above still applies to it.
      if (rel !== 'CHANGELOG.md' &&
          /promptsmith/i.test(line) &&
          !LEGACY_FALLBACK.test(line) &&
          !RENAME_EXPLANATION.test(line) &&
          !/\/promptsmith:/.test(line) &&
          !/blind|redact|neutralis|neutraliz|regex|r"/i.test(line)) {
        add(ctx, 'warn', 'namespace', rel, i + 1,
          `mentions the old project name "promptsmith" outside a rename explanation or a legacy ` +
          `read-fallback path. Confirm this is intentional; the current name is "guildproof".`);
      }
    });
  }
}

// ===========================================================================
// CHECK 6 — version coherence
// ===========================================================================
function readJson(ctx, rel) {
  const abs = path.join(ctx.root, rel);
  if (!exists(abs)) return null;
  try { return JSON.parse(fs.readFileSync(abs, 'utf8')); } catch (e) {
    add(ctx, 'error', 'version', rel, 1, `is not valid JSON: ${e.message}`);
    return null;
  }
}

/** Find the 1-based line a `"key":` appears on, for a citable file:line. */
function jsonKeyLine(ctx, rel, key) {
  const abs = path.join(ctx.root, rel);
  if (!exists(abs)) return null;
  const lines = readLines(abs);
  const idx = lines.findIndex((l) => new RegExp(`"${key}"\\s*:`).test(l));
  return idx === -1 ? null : idx + 1;
}

function checkVersions(ctx) {
  const plugin = readJson(ctx, '.claude-plugin/plugin.json');
  if (!plugin) {
    add(ctx, 'error', 'version', '.claude-plugin/plugin.json', null,
      'missing — this is the plugin manifest and it owns the version number.');
    return;
  }
  const pv = plugin.version;
  const pvLine = jsonKeyLine(ctx, '.claude-plugin/plugin.json', 'version');
  if (!pv) {
    add(ctx, 'error', 'version', '.claude-plugin/plugin.json', pvLine,
      'no "version" field. The manifest must state the version every other file is checked against.');
    return;
  }

  // marketplace.json may legitimately carry no version; only a DISAGREEING one is an error.
  const market = readJson(ctx, '.claude-plugin/marketplace.json');
  if (market) {
    const candidates = [market.version, market.plugins?.[0]?.version].filter(Boolean);
    if (candidates.length === 0) {
      add(ctx, 'warn', 'version', '.claude-plugin/marketplace.json', null,
        `states no version, so nothing here contradicts plugin.json (${pv}). Nothing to fix; noted ` +
        `so the absence is a known fact rather than an assumption.`);
    }
    for (const v of candidates) {
      if (v !== pv) {
        add(ctx, 'error', 'version', '.claude-plugin/marketplace.json',
          jsonKeyLine(ctx, '.claude-plugin/marketplace.json', 'version'),
          `version "${v}" does not match plugin.json version "${pv}". One install path would ship a ` +
          `different number than the other. Make them equal.`);
      }
    }
  }

  const changelogRel = 'CHANGELOG.md';
  if (!exists(path.join(ctx.root, changelogRel))) {
    add(ctx, 'warn', 'version', changelogRel, null,
      `does not exist, so plugin.json's version (${pv}) cannot be cross-checked against release ` +
      `notes. Not an error — a repo may ship without one — but a reader has no way to see what ` +
      `changed in ${pv}.`);
    return;
  }
  const lines = readLines(path.join(ctx.root, changelogRel));
  // Accept the usual heading shapes: "## 0.3.0", "## [0.3.0]", "## v0.3.0 - 2026-09-20"
  const found = [];
  lines.forEach((l, i) => {
    const m = /^#{1,3}\s*\[?v?(\d+\.\d+\.\d+)\]?/.exec(l.trim());
    if (m) found.push({ v: m[1], line: i + 1 });
  });
  if (found.length === 0) {
    add(ctx, 'warn', 'version', changelogRel, 1,
      `has no version heading matching "## <x.y.z>", so plugin.json's ${pv} cannot be cross-checked.`);
  } else if (found[0].v !== pv) {
    add(ctx, 'error', 'version', changelogRel, found[0].line,
      `the newest version heading is "${found[0].v}" but plugin.json says "${pv}". The changelog's ` +
      `top entry should be the version being shipped.`);
  }
}

// ===========================================================================
// CHECK 7 — KB fixtures exist and keep the shape the Python runner strips
//
// evals/harness/run-knownbad.py's neutralize() blinds a fixture by splitting it
// on three headings and dropping the answer. Read from that function directly:
//   re.match(r"(?s)^---\n(.*?)\n---\n(.*)$")   -> a frontmatter block
//   re.search(r"(?m)^## Input\s*$")             -> exact heading, nothing after it
//   re.search(r"(?m)^## Bad output[^\n]*$")     -> trailing text allowed
//                                                  (KB6 is "## Bad output (must FAIL - excerpt)")
//   re.search(r"(?m)^## Why it must FAIL\s*$")  -> exact heading, nothing after it
// It also requires Input < Bad output < Why, since it slices between them, and it
// raises if "must FAIL", "expect:" or "plants:" survive into what the judge sees.
//
// If a heading drifts, that runner raises on every fixture and the calibration
// set silently stops running. Catching it here is the whole point.
// ===========================================================================
const KB_EXPECTED_IDS = ['KB1', 'KB2', 'KB3', 'KB4', 'KB5', 'KB6'];

function checkKbFixtures(ctx) {
  const dir = 'evals/known-bad';
  const abs = path.join(ctx.root, dir);
  if (!exists(abs)) {
    add(ctx, 'error', 'kb-shape', dir, null,
      'directory is missing. It holds the deliberately-broken calibration fixtures the eval suite ' +
      'must always FAIL; without them a green run proves nothing.');
    return;
  }
  const files = fs.readdirSync(abs).filter((f) => /^KB.*\.md$/.test(f)).sort();

  for (const id of KB_EXPECTED_IDS) {
    if (!files.some((f) => f.startsWith(id))) {
      add(ctx, 'error', 'kb-shape', dir, null,
        `no fixture file starting with "${id}". Expected all of ${KB_EXPECTED_IDS.join(', ')}; found ` +
        `${files.join(', ') || '(none)'}. evals/harness/run-knownbad.py gates on the whole set, so a ` +
        `missing fixture lowers the bar without anything reporting it.`);
    }
  }

  for (const f of files) {
    const rel = `${dir}/${f}`;
    const lines = readLines(path.join(abs, f));

    if (lines[0]?.trim() !== '---' || !lines.slice(1).some((l) => l.trim() === '---')) {
      add(ctx, 'error', 'kb-shape', rel, 1,
        'no --- frontmatter block. run-knownbad.py neutralize() starts with ' +
        're.match(r"(?s)^---\\n(.*?)\\n---\\n(.*)$") and raises "fixture has no frontmatter block" ' +
        'without one, which takes down the whole known-bad gate.');
      continue;
    }

    const want = [
      { label: '## Input', re: /^## Input[ \t]*$/, exact: true },
      { label: '## Bad output', re: /^## Bad output.*$/, exact: false },
      { label: '## Why it must FAIL', re: /^## Why it must FAIL[ \t]*$/, exact: true },
    ];
    const at = {};
    for (const w of want) {
      const idx = lines.findIndex((l) => w.re.test(l));
      if (idx === -1) {
        add(ctx, 'error', 'kb-shape', rel, null,
          `missing the heading "${w.label}"${w.exact ? ' (exact text, nothing after it on the line)' : ' (trailing text after it is allowed)'}. ` +
          `run-knownbad.py neutralize() searches for /${w.re.source}/ and raises "fixture is missing one ` +
          `of: '## Input', '## Bad output', '## Why it must FAIL'" — every fixture then fails to load ` +
          `and the gate stops measuring anything.`);
      } else {
        at[w.label] = idx + 1;
      }
    }

    if (at['## Input'] && at['## Bad output'] && at['## Why it must FAIL']) {
      const order = [at['## Input'], at['## Bad output'], at['## Why it must FAIL']];
      if (!(order[0] < order[1] && order[1] < order[2])) {
        add(ctx, 'error', 'kb-shape', rel, order[0],
          `headings are out of order (## Input line ${order[0]}, ## Bad output line ${order[1]}, ` +
          `## Why it must FAIL line ${order[2]}). neutralize() slices the input and output text ` +
          `BETWEEN those offsets, so out-of-order headings produce an empty or inverted judge prompt.`);
      }
    }
  }
}

// ===========================================================================
// Orchestration + reporting
// ===========================================================================
function runAllChecks(root) {
  const ctx = makeCtx(root);
  const inv = countInventory(ctx);
  checkCounts(ctx, inv);
  checkTableRows(ctx);
  checkFrontmatter(ctx);
  checkPhantoms(ctx);
  checkDeadNamespace(ctx);
  checkVersions(ctx);
  checkKbFixtures(ctx);
  return { ctx, inv };
}

function fmt(f) {
  const where = f.line == null ? f.file : `${f.file}:${f.line}`;
  return `  [${f.check}] ${where} — ${f.msg}`;
}

function report(root, { ctx, inv }) {
  const errors = ctx.findings.filter((f) => f.level === 'error');
  const warns = ctx.findings.filter((f) => f.level === 'warn');

  console.log(`validate.mjs — ${root}`);
  console.log('');
  console.log('Counted on disk:');
  for (const [key, spec] of Object.entries(COUNTABLE)) {
    const n = inv[key];
    console.log(`  ${spec.dir.padEnd(20)} ${n == null ? '(directory not found)' : `${n} ${spec.label}`}`);
  }
  console.log('');

  if (errors.length) {
    console.log(`ERRORS (${errors.length}) — these must be fixed or explicitly exempted:`);
    errors.forEach((f) => console.log(fmt(f)));
    console.log('');
  }
  if (warns.length) {
    console.log(`WARNINGS (${warns.length}) — worth a look; they do not fail the run:`);
    warns.forEach((f) => console.log(fmt(f)));
    console.log('');
  }
  if (ctx.suppressed.length) {
    console.log(`Suppressed count candidates (${ctx.suppressed.length}) — matched a claim pattern but`);
    console.log('were judged not to be inventory claims. Listed so the suppression is auditable:');
    ctx.suppressed.forEach((s) => console.log(`  ${s}`));
    console.log('');
  }
  if (!errors.length && !warns.length) console.log('All checks passed. Nothing to fix.');
  else console.log(`Result: ${errors.length} error(s), ${warns.length} warning(s).`);

  return errors.length ? 1 : 0;
}

// ===========================================================================
// --selftest
//
// The point of this mode is not tidiness. A check that has never been observed
// to fail is not known to be measuring anything — this repo learned that from
// its own known-bad eval fixtures, which exist because nine consecutive all-PASS
// runs were indistinguishable from a broken judge.
//
// So: every check above is pointed at a mini-repo that is deliberately broken in
// exactly one way, and the selftest FAILS if the check does not catch it. One
// extra fixture ("clean") is correct and must produce zero errors, which proves
// the checks do not simply fire on everything.
//
// Fixtures live in scripts/validate-selftest/. `base/` is the correct mini-repo;
// each other folder is an OVERLAY of only the file(s) it breaks. The selftest
// copies base into a temp dir, copies the overlay over it, and runs the real
// checks against the result — same code path as the real repo, no mocks.
// ===========================================================================
const FIXTURES = [
  { dir: 'clean',               expect: null,          note: 'a correct mini-repo — must produce ZERO errors' },
  { dir: 'wrong-count',         expect: 'counts',      note: 'README claims 9 agents; 3 exist' },
  { dir: 'table-rows',          expect: 'table-rows',  note: 'sentence says 4 things, the table has 2 rows' },
  { dir: 'missing-frontmatter', expect: 'frontmatter', note: 'an agent with no role/voice, a lens with no applies-to' },
  { dir: 'phantom-agent',       expect: 'phantom',     note: 'gallery lists an agent with no file' },
  { dir: 'dead-namespace',      expect: 'namespace',   note: 'a live doc still says /promptsmith:' },
  { dir: 'version-mismatch',    expect: 'version',     note: 'marketplace.json version disagrees with plugin.json' },
  { dir: 'kb-heading',          expect: 'kb-shape',    note: 'KB fixture heading renamed; neutralize() would raise' },
];

function selftest() {
  const fixRoot = path.join(HERE, 'validate-selftest');
  const base = path.join(fixRoot, 'base');
  if (!exists(base)) {
    console.log(`SELFTEST CANNOT RUN — fixture base not found at ${base}`);
    return 1;
  }

  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'validate-selftest-'));
  let failures = 0;
  console.log('validate.mjs --selftest');
  console.log(`fixtures: ${fixRoot}`);
  console.log(`workdir : ${work}`);
  console.log('');

  for (const fx of FIXTURES) {
    const target = path.join(work, fx.dir);
    fs.cpSync(base, target, { recursive: true });
    if (fx.dir !== 'clean') {
      const overlay = path.join(fixRoot, fx.dir);
      if (!exists(overlay)) {
        console.log(`  ${fx.dir.padEnd(20)} MISSING FIXTURE at ${overlay}`);
        failures++;
        continue;
      }
      fs.cpSync(overlay, target, { recursive: true, force: true });
    }

    const { ctx } = runAllChecks(target);
    const errors = ctx.findings.filter((f) => f.level === 'error');

    if (fx.expect === null) {
      if (errors.length === 0) {
        console.log(`  ${fx.dir.padEnd(20)} OK   — clean fixture produced 0 errors (${fx.note})`);
      } else {
        failures++;
        console.log(`  ${fx.dir.padEnd(20)} FAIL — clean fixture was flagged; the checks fire on correct input:`);
        errors.forEach((f) => console.log(`      ${fmt(f).trim()}`));
      }
      continue;
    }

    const caught = errors.filter((f) => f.check === fx.expect);
    if (caught.length > 0) {
      const at = caught[0].line == null ? `${caught[0].file} (file-level)` : `${caught[0].file}:${caught[0].line}`;
      console.log(`  ${fx.dir.padEnd(20)} OK   — [${fx.expect}] caught it: ${at}`);
    } else {
      failures++;
      console.log(`  ${fx.dir.padEnd(20)} FAIL — [${fx.expect}] did NOT fire. ${fx.note}`);
      if (errors.length) {
        console.log('      other errors it did report:');
        errors.forEach((f) => console.log(`        ${fmt(f).trim()}`));
      } else {
        console.log('      it reported no errors at all.');
      }
    }
  }

  fs.rmSync(work, { recursive: true, force: true });
  console.log('');
  if (failures === 0) {
    console.log(`SELFTEST PASS — all ${FIXTURES.length} fixtures behaved as expected ` +
      `(${FIXTURES.length - 1} deliberate defects caught, 1 clean fixture not flagged).`);
    return 0;
  }
  console.log(`SELFTEST FAIL — ${failures} of ${FIXTURES.length} fixtures behaved wrongly. ` +
    `A check that cannot catch its own fixture is not measuring anything.`);
  return 1;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------
const argv = process.argv.slice(2);
if (argv.includes('--help') || argv.includes('-h')) {
  console.log(`Usage:
  node scripts/validate.mjs             validate this repo (exit 1 on any error)
  node scripts/validate.mjs --selftest  run the checks against deliberately broken fixtures
`);
  process.exit(0);
}
process.exit(argv.includes('--selftest') ? selftest() : report(REPO_ROOT, runAllChecks(REPO_ROOT)));
