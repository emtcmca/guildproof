# Scoring: data-modeler on the subscription billing case

I did not run the SQL, since no Postgres instance was available. I read it statement by statement instead and checked the trigger, constraint and FK counts by hand.

## 1. Structural invariants (gallery agent)

- ✅ **Output matches the agent's contract, section for section.** Sections 1–5 are Entities & relationships, Schema (DDL), Invariants → constraints, Migration and Flags. The extra "0. Assumptions" section adds to the contract and does not replace any part of it.
- ✅ **A voice is detectable.** Examples: "I have not executed any of this SQL against a Postgres instance", "I reasoned about that race but have not observed it", and "Recount if you edit the script."

## 2. Quality dimensions (gallery agent)

- ✅ **Contract honored.** Migration covers locking, backfill, rollback and a scratch-database test, and it declares that "'Preserves every existing row' is vacuously true". Flags covers PII, irreversible steps and a self-challenge.
- ✅ **Guardrails honored (hard gate).** The output invents no domain facts. Every assumption A1–A11 has an "If wrong" consequence. It marks the unexecuted SQL, the untested race and the Postgres version as unverified. The checkable claims hold:
  - `gen_random_uuid()` is built in from 13.
  - `btree_gist` is trusted from 13.
  - `NOT VALID` does not apply to EXCLUDE constraints.
  - `CREATE INDEX CONCURRENTLY` cannot run in a transaction.
  - The counts of 9 tables and 16 triggers are correct. I counted 11 plain and 5 audit `CREATE TRIGGER` statements.
- ✅ **In voice.**
- ✅ **Self-challenge done.** It lists 13 specific wrong-state cases, for example "A $1 line for a $99 plan is representable", "A succeeded payment can land on a void invoice" and "`audit_log.actor` is self-asserted". This is substantive and specific, not a token line.
- ⚠️ **Index claim is inaccurate.** The access-pattern table says invoices by subscription are served by "the GiST index behind the exclusion constraint". That constraint carries `WHERE (status <> 'void')`, so the index is partial. A query for all invoices of a subscription, including voided ones, cannot use it. There is no plain `invoices(subscription_id)` index, and the composite FK to `subscriptions` has no supporting index either. This is a confident statement that is wrong on a checkable point.
- ⚠️ **Overstated impossibility.** The output says: "Nothing ties `unit_amount_minor` to the plan price… Proration and discounts make an equality check impossible." For `kind='recurring'` lines that is not true. A `UNIQUE (id, currency, unit_amount_minor)` on `plan_prices`, plus a composite FK on recurring lines, would pin the price in the DB. The output uses the same composite-FK technique elsewhere (`payments_invoice_fk`), so it could have used it here. It left this to app code when the DB could enforce it.
- ⚠️ **Scope and volume.** The output has 16 triggers, an audit log, an anomalies view and an erasure flow. The ask was "plans, customers, subscriptions, invoices". Most of it is justified in the Flags section, but the audit and anomalies pieces are unrequested surface area.

## 3. This case's must list

- ✅ **Full contract.** All five sections are present, as covered above.
- ✅ **Integer minor units with a currency column.** Every money column is `bigint` (`unit_amount_minor`, `subtotal_minor`, `total_minor`, `amount_minor`). Currency is enforced by FK to `currencies`, and composite FKs carry it through to lines and payments.
- ✅ **Invariants enforced in the DB.** This uses PK, FK, UNIQUE and CHECK, with status values as `text CHECK (... IN (...))`. It also uses partial unique indexes, an EXCLUDE constraint and guard triggers.
- ✅ **Idempotency via a unique key, with UTC timestamps.**
  - Charges use `payments.idempotency_key text NOT NULL UNIQUE` plus `UNIQUE (provider, external_ref)`.
  - Invoices use a natural-key EXCLUDE on subscription and period. It is not literally a unique key, and a retry raises 23P01 rather than returning the existing row. It is still DB-enforced and stricter than a unique key.
  - Timestamps are all `timestamptz`, which Postgres stores as UTC. The output says "all timestamps timestamptz" and never states "UTC" explicitly.

## 4. This case's must-not list

- ✅ **No floating-point money.** No `float`, `real`, `double precision` or `numeric` appears anywhere.
- ✅ **Core invariant not left to app code when the DB could enforce it.** The named example, one live subscription per customer per plan, is enforced by `subscriptions_one_live_per_plan`. The gaps left to the app are flagged, but one is arguably enforceable (the recurring-line price pin above). I treat it as a quality ⚠️ and not a violation, because the named core invariant is enforced.

## Verdict rule

There is no ❌ anywhere and no hard-gate failure. There are three ⚠️ marks, so the rule gives WEAK.

VERDICT: WEAK