# Subscription billing schema (Postgres)

This is a greenfield design. No existing schema or data was supplied, so I could not verify anything about a current database. **I have not executed any of this SQL against a Postgres instance.** Treat every statement as unverified until the scratch-database test in the Migration section passes.

## 0. Assumptions and confirm-items

Each row is a reading I chose. The last column says what changes if it's wrong.

| # | Assumption | If wrong |
|---|---|---|
| A1 | Postgres 13 or later. `gen_random_uuid()` is built in from 13, and `btree_gist` is a trusted extension from 13. Your host and version are unverified. | Add `pgcrypto`, or ask a superuser to install `btree_gist`. |
| A2 | Flat recurring pricing. A subscription has one price, with no quantity, usage metering, coupons, trials or multi-item subscriptions. | Adds `subscription_items`, `usage_records`, `discounts` and `trial_end`. The core tables survive. |
| A3 | A subscription's currency never changes. Switching currency means a new subscription. | Drop the currency-immutability guard and decide what happens to open invoices. |
| A4 | A customer holds at most one live subscription per plan. | Drop `subscriptions_one_live_per_plan`. |
| A5 | There is one invoice per billing period per subscription. Proration appears as lines on the next invoice. | Drop the exclusion constraint on `invoices` and add an invoice `kind`. |
| A6 | An invoice is paid by exactly one payment for the full total. No partial or split payments. | Drop the payment-amount FK and the one-live-payment index, and add a sum-of-payments constraint trigger. |
| A7 | Every invoice belongs to a subscription. There are no one-off invoices. | Make `subscription_id` nullable and relax the composite FK. |
| A8 | Customer email is unique. | Drop `customers_email_key`. |
| A9 | Tax is stored as a computed amount only, with no rates or jurisdictions. | Add `tax_rates` and `invoice_line_taxes`. |
| A10 | Invoice numbers are sequential but may have gaps. | If your jurisdiction requires gapless numbers, use a counter-table allocator instead of a sequence. That is a legal question I can't answer. |
| A11 | Supported currencies are USD, EUR and GBP (seed only). | Edit the seed rows. |

## 1. Entities and relationships

```
customers 1──* subscriptions *──1 plan_prices *──1 plans
subscriptions 1──* invoices 1──* invoice_lines
invoices 1──* payments   (at most ONE pending-or-succeeded payment per invoice)
currencies ──< plan_prices, subscriptions, invoices, invoice_lines, payments
audit_log  (append-only, fed by triggers)
```

- **`plans`** is what you sell. **`plan_prices`** is what it costs. Prices are immutable and per currency. A price change is a new row plus deactivating the old one, so history never rewrites.
- **`subscriptions`** links a customer to one price, with the current billing period. Currency is carried on the row so the database can enforce currency consistency downstream.
- **`invoices`** are frozen legal documents once finalized. Totals and bill-to details are derived at finalization by a trigger, not supplied by callers.
- **`payments`** record what the processor did, as facts.

## 2. Schema

Save as `db/migrations/0001-billing-core.up.sql`. I've kept comments to the non-obvious lines.

```sql
BEGIN;
SET LOCAL lock_timeout = '5s';              -- fail fast instead of queueing behind a lock
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- needed for the invoice-period exclusion constraint

-- Conventions: uuid keys (non-enumerable when exposed via API; bigint identity would be
-- friendlier to index locality), text+CHECK instead of enum types (easier to change),
-- money = bigint minor units + currency, all timestamps timestamptz.

---------------------------------------------------------------- reference data
CREATE TABLE currencies (
  code       text PRIMARY KEY CHECK (code ~ '^[A-Z]{3}$'),
  minor_unit smallint NOT NULL CHECK (minor_unit BETWEEN 0 AND 4)  -- 2 for USD, 0 for JPY
);
INSERT INTO currencies (code, minor_unit) VALUES ('USD',2),('EUR',2),('GBP',2);  -- A11: confirm

---------------------------------------------------------------- customers (PII)
CREATE TABLE customers (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email      text NOT NULL,
  name       text NOT NULL CHECK (btrim(name) <> ''),
  country    text NOT NULL CHECK (country ~ '^[A-Z]{2}$'),
  erased_at  timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT customers_email_normalized CHECK (email = lower(btrim(email)) AND email LIKE '%_@_%'),
  CONSTRAINT customers_email_key UNIQUE (email)
);

---------------------------------------------------------------- plans and prices
CREATE TABLE plans (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code       text NOT NULL UNIQUE CHECK (code ~ '^[a-z0-9][a-z0-9_-]*$'),
  name       text NOT NULL CHECK (btrim(name) <> ''),
  active     boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE plan_prices (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id           uuid NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
  currency          text NOT NULL REFERENCES currencies(code),
  unit_amount_minor bigint NOT NULL CHECK (unit_amount_minor >= 0),   -- 0 allows free plans
  interval_unit     text NOT NULL CHECK (interval_unit IN ('month','year')),
  interval_count    smallint NOT NULL DEFAULT 1 CHECK (interval_count > 0),
  active            boolean NOT NULL DEFAULT true,
  created_at        timestamptz NOT NULL DEFAULT now(),
  -- FK targets: let child tables pin currency (and plan) to the price row itself
  CONSTRAINT plan_prices_id_currency_key UNIQUE (id, currency),
  CONSTRAINT plan_prices_id_plan_currency_key UNIQUE (id, plan_id, currency)
);
-- at most one ACTIVE price per plan / currency / interval shape
CREATE UNIQUE INDEX plan_prices_one_active_per_shape
  ON plan_prices (plan_id, currency, interval_unit, interval_count) WHERE active;

---------------------------------------------------------------- subscriptions
CREATE TABLE subscriptions (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id          uuid NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
  plan_id              uuid NOT NULL,
  plan_price_id        uuid NOT NULL,
  currency             text NOT NULL,
  status               text NOT NULL CHECK (status IN ('active','past_due','canceled')),
  current_period_start timestamptz NOT NULL,
  current_period_end   timestamptz NOT NULL,
  cancel_at_period_end boolean NOT NULL DEFAULT false,
  canceled_at          timestamptz,
  ended_at             timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  -- price, its plan, and the subscription's currency must all agree
  CONSTRAINT subscriptions_price_fk
    FOREIGN KEY (plan_price_id, plan_id, currency) REFERENCES plan_prices (id, plan_id, currency),
  CONSTRAINT subscriptions_period_ordered CHECK (current_period_end > current_period_start),
  CONSTRAINT subscriptions_ended_iff_canceled CHECK ((status = 'canceled') = (ended_at IS NOT NULL)),
  CONSTRAINT subscriptions_canceled_has_ts CHECK (status <> 'canceled' OR canceled_at IS NOT NULL),
  CONSTRAINT subscriptions_id_customer_currency_key UNIQUE (id, customer_id, currency)
);
CREATE UNIQUE INDEX subscriptions_one_live_per_plan            -- A4
  ON subscriptions (customer_id, plan_id) WHERE status <> 'canceled';
CREATE INDEX subscriptions_customer_idx ON subscriptions (customer_id);
CREATE INDEX subscriptions_price_idx    ON subscriptions (plan_price_id);
CREATE INDEX subscriptions_renewal_idx  ON subscriptions (current_period_end)
  WHERE status IN ('active','past_due');                       -- renewal job's scan

---------------------------------------------------------------- invoices
CREATE SEQUENCE invoice_number_seq;  -- NOT gapless (A10)

CREATE TABLE invoices (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id     uuid NOT NULL,
  subscription_id uuid NOT NULL,
  currency        text NOT NULL,
  status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','open','paid','void','uncollectible')),
  number          text UNIQUE,                       -- assigned by trigger at finalization
  period_start    timestamptz NOT NULL,
  period_end      timestamptz NOT NULL,
  subtotal_minor  bigint NOT NULL DEFAULT 0,         -- derived by trigger at finalization
  tax_minor       bigint NOT NULL DEFAULT 0 CHECK (tax_minor >= 0),
  total_minor     bigint NOT NULL DEFAULT 0,
  due_at          timestamptz,
  finalized_at    timestamptz,
  paid_at         timestamptz,
  voided_at       timestamptz,
  -- frozen snapshot of the customer at finalization (an invoice is a legal document)
  bill_to_name    text,
  bill_to_email   text,
  bill_to_country text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  -- invoice must belong to the subscription's own customer and currency
  CONSTRAINT invoices_subscription_fk
    FOREIGN KEY (subscription_id, customer_id, currency)
    REFERENCES subscriptions (id, customer_id, currency),
  CONSTRAINT invoices_id_currency_key       UNIQUE (id, currency),
  CONSTRAINT invoices_id_currency_total_key UNIQUE (id, currency, total_minor),
  CONSTRAINT invoices_period_ordered  CHECK (period_end > period_start),
  CONSTRAINT invoices_total_is_sum    CHECK (total_minor = subtotal_minor + tax_minor),
  CONSTRAINT invoices_total_nonneg    CHECK (total_minor >= 0),
  CONSTRAINT invoices_number_iff_final CHECK ((status = 'draft') = (number IS NULL)),
  CONSTRAINT invoices_finalized_iff    CHECK ((status = 'draft') = (finalized_at IS NULL)),
  CONSTRAINT invoices_paid_iff         CHECK ((status = 'paid') = (paid_at IS NOT NULL)),
  CONSTRAINT invoices_void_iff         CHECK ((status = 'void') = (voided_at IS NOT NULL)),
  CONSTRAINT invoices_final_complete   CHECK (status = 'draft' OR
     (due_at IS NOT NULL AND bill_to_name IS NOT NULL
      AND bill_to_email IS NOT NULL AND bill_to_country IS NOT NULL)),
  -- A5: a billing period can be invoiced once (voiding frees it); a retried job cannot double-bill
  CONSTRAINT invoices_no_overlapping_periods
    EXCLUDE USING gist (subscription_id WITH =, tstzrange(period_start, period_end) WITH &&)
    WHERE (status <> 'void')
);
CREATE INDEX invoices_customer_idx ON invoices (customer_id, created_at DESC);
CREATE INDEX invoices_dunning_idx  ON invoices (due_at) WHERE status = 'open';

CREATE TABLE invoice_lines (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id        uuid NOT NULL,
  currency          text NOT NULL,
  kind              text NOT NULL CHECK (kind IN ('recurring','proration','adjustment')),
  description       text NOT NULL CHECK (btrim(description) <> ''),
  plan_price_id     uuid,                               -- which price this line billed
  quantity          integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
  unit_amount_minor bigint NOT NULL,                    -- may be negative for credits
  amount_minor      bigint GENERATED ALWAYS AS (unit_amount_minor * quantity) STORED,
  tax_amount_minor  bigint NOT NULL DEFAULT 0 CHECK (tax_amount_minor >= 0),
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT invoice_lines_invoice_fk FOREIGN KEY (invoice_id, currency)
    REFERENCES invoices (id, currency) ON DELETE CASCADE,     -- only drafts can be deleted
  CONSTRAINT invoice_lines_price_fk FOREIGN KEY (plan_price_id, currency)
    REFERENCES plan_prices (id, currency),                    -- skipped when plan_price_id is NULL
  CONSTRAINT invoice_lines_recurring_shape
    CHECK (kind <> 'recurring' OR (plan_price_id IS NOT NULL AND unit_amount_minor >= 0))
);
CREATE INDEX invoice_lines_invoice_idx ON invoice_lines (invoice_id);
CREATE INDEX invoice_lines_price_idx   ON invoice_lines (plan_price_id) WHERE plan_price_id IS NOT NULL;

---------------------------------------------------------------- payments (facts)
CREATE TABLE payments (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id      uuid NOT NULL,
  currency        text NOT NULL,
  amount_minor    bigint NOT NULL CHECK (amount_minor > 0),
  status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','succeeded','failed')),
  provider        text NOT NULL CHECK (btrim(provider) <> ''),
  external_ref    text CHECK (external_ref IS NULL OR btrim(external_ref) <> ''),
  idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key) <> ''),
  created_at      timestamptz NOT NULL DEFAULT now(),
  settled_at      timestamptz,
  -- A6: a payment is for exactly this invoice's currency AND full total
  CONSTRAINT payments_invoice_fk FOREIGN KEY (invoice_id, currency, amount_minor)
    REFERENCES invoices (id, currency, total_minor),
  CONSTRAINT payments_provider_ref_key UNIQUE (provider, external_ref),  -- reconciliation join key
  CONSTRAINT payments_settled_iff CHECK ((status = 'pending') = (settled_at IS NULL)),
  CONSTRAINT payments_success_has_ref CHECK (status <> 'succeeded' OR external_ref IS NOT NULL)
);
-- at most one in-flight-or-successful payment per invoice: a double click or retry can't double-charge
CREATE UNIQUE INDEX payments_one_live_per_invoice
  ON payments (invoice_id) WHERE status IN ('pending','succeeded');
CREATE INDEX payments_invoice_idx ON payments (invoice_id);

---------------------------------------------------------------- audit trail
CREATE TABLE audit_log (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  actor       text,                        -- self-asserted via SET app.actor; see Flags
  table_name  text NOT NULL,
  row_id      uuid NOT NULL,
  action      text NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
  before      jsonb,
  after       jsonb,
  CONSTRAINT audit_log_shape CHECK ((action = 'INSERT') = (before IS NULL)
                                AND (action = 'DELETE') = (after IS NULL))
);
CREATE INDEX audit_log_row_idx ON audit_log (table_name, row_id, id);

---------------------------------------------------------------- guard functions
CREATE FUNCTION forbid_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% rows are never deleted; deactivate or cancel instead', TG_TABLE_NAME
    USING ERRCODE = 'integrity_constraint_violation';
END $$;

CREATE FUNCTION plan_prices_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.id, NEW.plan_id, NEW.currency, NEW.unit_amount_minor, NEW.interval_unit,
      NEW.interval_count, NEW.created_at)
     IS DISTINCT FROM
     (OLD.id, OLD.plan_id, OLD.currency, OLD.unit_amount_minor, OLD.interval_unit,
      OLD.interval_count, OLD.created_at) THEN
    RAISE EXCEPTION 'plan_prices are immutable except deactivation; insert a new price'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF OLD.active = false AND NEW.active = true THEN
    RAISE EXCEPTION 'a deactivated price cannot be reactivated; insert a new price'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION subscriptions_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'canceled' THEN
    RAISE EXCEPTION 'canceled subscriptions are terminal'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.customer_id <> OLD.customer_id OR NEW.currency <> OLD.currency THEN
    RAISE EXCEPTION 'subscription customer and currency are immutable (A3)'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION invoice_lines_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE inv uuid; st text;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.invoice_id <> OLD.invoice_id THEN
    RAISE EXCEPTION 'a line cannot move between invoices'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF TG_OP = 'DELETE' THEN inv := OLD.invoice_id; ELSE inv := NEW.invoice_id; END IF;
  -- FOR SHARE makes a concurrent finalize wait for us (or us for it), so a line
  -- cannot slip into an invoice that is being finalized
  SELECT status INTO st FROM invoices WHERE id = inv FOR SHARE;
  IF FOUND AND st <> 'draft' THEN   -- NOT FOUND = parent draft is mid-delete (cascade): allow
    RAISE EXCEPTION 'invoice % is % ; its lines are immutable', inv, st
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION invoices_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c customers%ROWTYPE; sub bigint; tax bigint; n bigint;
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'draft' THEN
      RAISE EXCEPTION 'invoices are created as draft' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    NEW.subtotal_minor := 0; NEW.tax_minor := 0; NEW.total_minor := 0;
    RETURN NEW;
  END IF;

  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'draft' THEN
      RAISE EXCEPTION 'only draft invoices can be deleted; void instead'
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN OLD;
  END IF;

  -- UPDATE: state machine
  IF NEW.status <> OLD.status AND (OLD.status, NEW.status) NOT IN
     (('draft','open'),('open','paid'),('open','void'),('open','uncollectible'),
      ('uncollectible','paid'),('uncollectible','void')) THEN
    RAISE EXCEPTION 'illegal invoice transition % -> %', OLD.status, NEW.status
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;

  -- once finalized, the document is frozen
  IF OLD.status <> 'draft' AND
     (NEW.customer_id, NEW.subscription_id, NEW.currency, NEW.period_start, NEW.period_end,
      NEW.number, NEW.finalized_at, NEW.due_at, NEW.subtotal_minor, NEW.tax_minor, NEW.total_minor,
      NEW.bill_to_name, NEW.bill_to_email, NEW.bill_to_country, NEW.created_at)
     IS DISTINCT FROM
     (OLD.customer_id, OLD.subscription_id, OLD.currency, OLD.period_start, OLD.period_end,
      OLD.number, OLD.finalized_at, OLD.due_at, OLD.subtotal_minor, OLD.tax_minor, OLD.total_minor,
      OLD.bill_to_name, OLD.bill_to_email, OLD.bill_to_country, OLD.created_at) THEN
    RAISE EXCEPTION 'finalized invoices are immutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF OLD.status = NEW.status AND OLD.status <> 'draft'
     AND (NEW.paid_at, NEW.voided_at) IS DISTINCT FROM (OLD.paid_at, OLD.voided_at) THEN
    RAISE EXCEPTION 'finalized invoices are immutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;

  IF NEW.status = 'draft' THEN
    NEW.subtotal_minor := 0; NEW.tax_minor := 0; NEW.total_minor := 0;   -- callers never supply totals

  ELSIF OLD.status = 'draft' THEN                                        -- draft -> open (finalize)
    SELECT COALESCE(SUM(amount_minor),0), COALESCE(SUM(tax_amount_minor),0), COUNT(*)
      INTO sub, tax, n FROM invoice_lines WHERE invoice_id = NEW.id;
    IF n = 0 THEN
      RAISE EXCEPTION 'cannot finalize an invoice with no lines' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    SELECT * INTO c FROM customers WHERE id = NEW.customer_id;
    IF c.erased_at IS NOT NULL THEN
      RAISE EXCEPTION 'customer % has been erased; cannot finalize', NEW.customer_id
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    NEW.subtotal_minor := sub;  NEW.tax_minor := tax;  NEW.total_minor := sub + tax;
    NEW.number       := 'INV-' || lpad(nextval('invoice_number_seq')::text, 8, '0');
    NEW.finalized_at := now();
    NEW.bill_to_name := c.name; NEW.bill_to_email := c.email; NEW.bill_to_country := c.country;

  ELSIF NEW.status = 'paid' AND OLD.status <> 'paid' THEN
    IF NOT EXISTS (SELECT 1 FROM payments WHERE invoice_id = NEW.id AND status = 'succeeded') THEN
      RAISE EXCEPTION 'invoice % has no succeeded payment', NEW.id USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    NEW.paid_at := now();

  ELSIF NEW.status = 'void' AND OLD.status <> 'void' THEN
    IF EXISTS (SELECT 1 FROM payments WHERE invoice_id = NEW.id AND status = 'succeeded') THEN
      RAISE EXCEPTION 'invoice % has a succeeded payment; refund/credit note required before voiding', NEW.id
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    NEW.voided_at := now();
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION payments_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'payments are never deleted' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF OLD.status <> 'pending' THEN
    RAISE EXCEPTION 'settled payments are immutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF (NEW.invoice_id, NEW.currency, NEW.amount_minor, NEW.provider, NEW.idempotency_key, NEW.created_at)
     IS DISTINCT FROM
     (OLD.invoice_id, OLD.currency, OLD.amount_minor, OLD.provider, OLD.idempotency_key, OLD.created_at)
     OR (OLD.external_ref IS NOT NULL AND NEW.external_ref IS DISTINCT FROM OLD.external_ref) THEN
    RAISE EXCEPTION 'payment identity and amount are immutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;

-- a succeeded payment marks its invoice paid. If the invoice is void, nothing happens here:
-- the payment is a real-world fact and is surfaced by billing_anomalies instead of rejected.
CREATE FUNCTION payments_apply() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'succeeded' THEN
    UPDATE invoices SET status = 'paid'
     WHERE id = NEW.invoice_id AND status IN ('open','uncollectible');
  END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION audit_row_change() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b jsonb; a jsonb; rid uuid;
BEGIN
  IF TG_OP <> 'INSERT' THEN b := to_jsonb(OLD) - TG_ARGV; rid := OLD.id; END IF;  -- TG_ARGV = columns to omit
  IF TG_OP <> 'DELETE' THEN a := to_jsonb(NEW) - TG_ARGV; rid := NEW.id; END IF;
  INSERT INTO audit_log (actor, table_name, row_id, action, before, after)
  VALUES (current_setting('app.actor', true), TG_TABLE_NAME, rid, TG_OP, b, a);
  RETURN NULL;
END $$;

CREATE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only' USING ERRCODE = 'integrity_constraint_violation';
END $$;

---------------------------------------------------------------- triggers (16 by my count)
CREATE TRIGGER plan_prices_immutable BEFORE UPDATE ON plan_prices
  FOR EACH ROW EXECUTE FUNCTION plan_prices_immutable();
CREATE TRIGGER plans_no_delete         BEFORE DELETE ON plans         FOR EACH ROW EXECUTE FUNCTION forbid_delete();
CREATE TRIGGER plan_prices_no_delete   BEFORE DELETE ON plan_prices   FOR EACH ROW EXECUTE FUNCTION forbid_delete();
CREATE TRIGGER subscriptions_no_delete BEFORE DELETE ON subscriptions FOR EACH ROW EXECUTE FUNCTION forbid_delete();
CREATE TRIGGER subscriptions_guard BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION subscriptions_guard();
CREATE TRIGGER invoice_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON invoice_lines
  FOR EACH ROW EXECUTE FUNCTION invoice_lines_guard();
CREATE TRIGGER invoices_guard BEFORE INSERT OR UPDATE OR DELETE ON invoices
  FOR EACH ROW EXECUTE FUNCTION invoices_guard();
CREATE TRIGGER payments_guard BEFORE UPDATE OR DELETE ON payments
  FOR EACH ROW EXECUTE FUNCTION payments_guard();
CREATE TRIGGER payments_apply AFTER INSERT OR UPDATE OF status ON payments
  FOR EACH ROW EXECUTE FUNCTION payments_apply();
CREATE TRIGGER audit_log_no_mutation BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();

-- audit: customers deliberately NOT audited (PII must stay erasable); invoice bill-to columns omitted
CREATE TRIGGER zz_audit AFTER INSERT OR UPDATE OR DELETE ON plans         FOR EACH ROW EXECUTE FUNCTION audit_row_change();
CREATE TRIGGER zz_audit AFTER INSERT OR UPDATE OR DELETE ON plan_prices   FOR EACH ROW EXECUTE FUNCTION audit_row_change();
CREATE TRIGGER zz_audit AFTER INSERT OR UPDATE OR DELETE ON subscriptions FOR EACH ROW EXECUTE FUNCTION audit_row_change();
CREATE TRIGGER zz_audit AFTER INSERT OR UPDATE OR DELETE ON payments      FOR EACH ROW EXECUTE FUNCTION audit_row_change();
CREATE TRIGGER zz_audit AFTER INSERT OR UPDATE OR DELETE ON invoices
  FOR EACH ROW EXECUTE FUNCTION audit_row_change('bill_to_name','bill_to_email');

---------------------------------------------------------------- reconciliation surface
CREATE VIEW billing_anomalies AS
  SELECT 'succeeded_payment_on_non_paid_invoice' AS kind, 'payments'::text AS entity, p.id AS entity_id
    FROM payments p JOIN invoices i ON i.id = p.invoice_id
   WHERE p.status = 'succeeded' AND i.status <> 'paid'
  UNION ALL
  SELECT 'open_invoice_past_due', 'invoices', id FROM invoices
   WHERE status = 'open' AND due_at < now()
  UNION ALL
  SELECT 'subscription_period_lapsed', 'subscriptions', id FROM subscriptions
   WHERE status <> 'canceled' AND current_period_end < now();

COMMIT;
```

**Indexes, and the access patterns I assumed** (none were supplied, so these are guesses to confirm):

| Pattern | Index |
|---|---|
| Renewal job finds due subscriptions | `subscriptions_renewal_idx` (partial) |
| Customer's subscriptions and invoice history | `subscriptions_customer_idx`, `invoices_customer_idx` |
| Dunning scan of overdue open invoices | `invoices_dunning_idx` (partial) |
| Load an invoice's lines or payments | `invoice_lines_invoice_idx`, `payments_invoice_idx` |
| Invoices by subscription | the GiST index behind the exclusion constraint (it serves `subscription_id = ?` via `btree_gist`) |
| Processor webhook lookup | `payments_provider_ref_key` |

## 3. Invariants → constraints

| Invariant | Enforced by |
|---|---|
| Money is integer minor units with a currency | `bigint` columns, plus `currency` FK to `currencies` on every money-bearing table |
| No invalid currency code | `currencies` FK |
| Price, plan and subscription currency agree | `subscriptions_price_fk` (composite: price, plan, currency) |
| Invoice belongs to the subscription's customer and currency | `invoices_subscription_fk` (composite) |
| Line and payment currency equal the invoice's | `invoice_lines_invoice_fk`, `payments_invoice_fk` (composite) |
| A line's price is in the line's currency | `invoice_lines_price_fk` |
| Prices never change, only deactivate | `plan_prices_immutable` trigger |
| One active price per plan, currency and interval | `plan_prices_one_active_per_shape` (partial unique) |
| No two live subscriptions to the same plan per customer (A4) | `subscriptions_one_live_per_plan` (partial unique) |
| Canceled is terminal, and `ended_at` is set exactly when canceled | `subscriptions_guard`, `subscriptions_ended_iff_canceled`, `subscriptions_canceled_has_ts` |
| Subscription customer and currency are immutable | `subscriptions_guard` |
| Period ends after it starts | `subscriptions_period_ordered`, `invoices_period_ordered` |
| A billing period is invoiced at most once (A5) | `invoices_no_overlapping_periods` (EXCLUDE) |
| Invoices start as drafts and follow the state machine | `invoices_guard` |
| Number, finalized time and due date exist exactly when non-draft | `invoices_number_iff_final`, `invoices_finalized_iff`, `invoices_final_complete` |
| Totals derive from lines, and callers can't supply them | `invoices_guard` (sets them), `invoices_total_is_sum`, `invoices_total_nonneg` |
| Finalized invoices and their lines are frozen | `invoices_guard`, `invoice_lines_guard` (`FOR SHARE` closes the finalize race) |
| Only drafts can be deleted | `invoices_guard` (DELETE branch) |
| Cannot finalize an empty invoice or one for an erased customer | `invoices_guard` |
| Bill-to snapshot is copied from the customer at finalization | `invoices_guard` |
| Recurring lines carry a price and a non-negative unit amount | `invoice_lines_recurring_shape` |
| Invoice numbers are unique | `invoices.number` UNIQUE |
| A payment matches the invoice's currency and full total (A6) | `payments_invoice_fk` (composite incl. amount) |
| One in-flight or successful payment per invoice | `payments_one_live_per_invoice` (partial unique) |
| A retried attempt can't duplicate | `payments.idempotency_key` UNIQUE |
| No duplicate processor record | `payments_provider_ref_key` |
| Success requires a processor reference and settle time | `payments_success_has_ref`, `payments_settled_iff` |
| Payments are immutable once settled and never deleted | `payments_guard` |
| Paid requires a succeeded payment | `invoices_guard` |
| A succeeded payment marks the invoice paid | `payments_apply` |
| An invoice with a succeeded payment can't be voided | `invoices_guard` |
| Audit rows can't be changed or truncated | `audit_log_no_mutation`, `audit_log_no_truncate` |
| **App-only (no DB enforcement):** advancing `current_period_*` on renewal, dunning moves to `past_due`, proration amounts, month-end anchor rule, processor reconciliation | Listed under Flags |

## 4. Migration

**Declare-and-degrade:** with no existing schema supplied, this is an initial migration on empty tables. "Preserves every existing row" is vacuously true and can't be checked against real data.

**Locking and backfill.** Every object is new, so the only locks are on empty tables and last microseconds. `SET LOCAL lock_timeout = '5s'` makes it fail rather than queue behind a stray lock. There is no backfill.

### Rollback: `db/migrations/0001-billing-core.down.sql`

```sql
BEGIN;
DROP VIEW  IF EXISTS billing_anomalies;
-- no CASCADE on purpose: a surprise dependency should fail loudly, not be silently dropped
DROP TABLE IF EXISTS audit_log, payments, invoice_lines, invoices,
                     subscriptions, plan_prices, plans, customers, currencies;
DROP SEQUENCE IF EXISTS invoice_number_seq;
DROP FUNCTION IF EXISTS forbid_delete(), plan_prices_immutable(), subscriptions_guard(),
                        invoice_lines_guard(), invoices_guard(), payments_guard(),
                        payments_apply(), audit_row_change(), audit_log_append_only();
-- btree_gist is left installed: other schemas may use it, and dropping an extension is not
-- this migration's call.
COMMIT;
```

> **Destructive once data exists.** The down script deletes every table, including the append-only audit log and all invoices. It is safe only before go-live. After that, roll forward with a corrective migration instead. Before running it anywhere that matters, take a backup, and confirm you can restore it:
> ```powershell
> pg_dump --format=custom --file=billing-pre-down-2026-09-20.dump $env:DATABASE_URL
> ```
> This assumes `DATABASE_URL` is already set in your shell and `pg_dump` is on your PATH. Both are unverified.

### Running it safely on a scratch database

1. **Create a throwaway database.** This creates an empty one and touches nothing else.
   ```powershell
   createdb billing_scratch
   ```
   *Verify:* `psql -d billing_scratch -c "\dt"` prints "Did not find any relations."
2. **Apply the migration.** `ON_ERROR_STOP=1` halts at the first error. The file has its own `BEGIN`/`COMMIT`, so a failure rolls everything back.
   ```powershell
   psql -d billing_scratch -v ON_ERROR_STOP=1 -f db/migrations/0001-billing-core.up.sql
   ```
   *Success:* the last line is `COMMIT` and no line contains `ERROR`. If `CREATE EXTENSION` is refused, your role lacks the privilege (see A1).
3. **Check the shape.**
   ```powershell
   psql -d billing_scratch -c "\dt"
   psql -d billing_scratch -c "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal;"
   ```
   *Success:* 9 tables and 16 triggers, by my count. Recount if you edit the script.
4. **Prove the constraints can fail.** A schema that only passes happy paths proves nothing. Each of these statements should error:

   | Attempt | Expected error |
   |---|---|
   | Insert a `plan_prices` row with a negative amount | 23514 check violation |
   | `UPDATE plan_prices SET unit_amount_minor = …` | 23000, raised by the trigger |
   | Subscribe to a price whose currency differs from the subscription's | 23503 FK violation |
   | Create two live subscriptions for the same customer and plan | 23505 unique violation |
   | Create two non-void invoices with overlapping periods for one subscription | 23P01 exclusion violation |
   | Insert a line into an open invoice | 23000 |
   | Finalize an invoice with no lines | 23000 |
   | Insert two pending payments for one invoice | 23505 |
   | Insert a payment whose amount ≠ the invoice total | 23503 |
   | `UPDATE invoices SET status='paid'` with no succeeded payment | 23000 |
   | `UPDATE audit_log …` or `TRUNCATE audit_log` | 23000 |

   Also run one happy path: draft, add lines, finalize (number and totals appear), insert a succeeded payment, and confirm the invoice becomes `paid`. Then run two concurrent sessions, one finalizing and one inserting a line. I reasoned about that race but have not observed it.
5. **Prove the rollback.** Run the down script on the scratch database, then `\dt` should show no relations. Re-run the up script to confirm it re-applies cleanly.

### If this is later applied to a populated database (untested pattern, not verified against your data)

- Postgres supports `NOT VALID` only for CHECK and FOREIGN KEY constraints, not EXCLUDE (verify on your version). Adding `invoices_no_overlapping_periods` to a large populated table therefore builds its index under a write-blocking lock. Check for overlapping historical periods first and run it in a quiet window.
- Build indexes with `CREATE INDEX CONCURRENTLY`. That cannot run inside `BEGIN`, so split it into its own migration step.
- Backfill in primary-key batches. Add each CHECK or FK as `NOT VALID`, then `VALIDATE CONSTRAINT`.
- Backfill `bill_to_*`, `number` and totals for historical invoices under an explicit break-glass procedure, because the guard triggers deliberately block that.

## 5. Flags

### Self-challenge: wrong states that can still be stored

1. **Line amounts are unconstrained.** Nothing ties `unit_amount_minor` to the plan price, so a $1 line for a $99 plan is representable. Proration and discounts make an equality check impossible without modeling them.
2. **Tax is unauditable.** `tax_amount_minor` has no rate or jurisdiction behind it, and negative tax on credit lines isn't representable (A9).
3. **Subscription and invoice periods are not linked.** Nothing forces `current_period_end` to advance only after an invoice exists, or an invoice's period to match its subscription's. Renewal logic lives in the app.
4. **`past_due` is unlinked from invoice state.** The DB doesn't couple a subscription's status to its invoices.
5. **A negative-total invoice is rejected**, so credits exceeding charges fail at finalization. A customer credit balance isn't modeled.
6. **A succeeded payment can land on a void invoice.** I chose to record real-world money movement rather than reject it. `billing_anomalies` surfaces it, but someone has to act on that view.
7. **Refunds and credit notes are not modeled.** Finalized invoices are frozen, so corrections need additive tables (`refunds`, `credit_notes`). The current tables don't change.
8. **A stuck `pending` payment blocks retries** through `payments_one_live_per_invoice`. Something must time it out and mark it failed.
9. **Invoice numbers can gap** (sequence rollbacks). See A10.
10. **Country and email formats are checked, but membership isn't.** Any two uppercase letters pass as a country.
11. **The triggers depend on privileges.** A table owner or superuser can disable them. I don't know your roles, so I've assumed none. The real barrier is an app role with no `ALTER`/`TRIGGER` rights, and I haven't defined one.
12. **`audit_log.actor` is self-asserted.** It comes from `SET app.actor` in the session, so anything with DB access can spoof it. It is a debugging aid, not proof of identity.
13. **Provider reconciliation is not in the DB.** `payments.external_ref` makes matching processor reports possible, but a mismatch job is app or ops work. The DB can't detect a mismatch by itself.

### PII and retention

- **Personal data:** `customers.email`, `.name`, `.country`, plus the frozen `invoices.bill_to_*` snapshot.
- **Erasure:** `customers` is not audited, so it stays erasable. Anonymize instead of deleting:
  ```sql
  UPDATE customers
     SET email = 'erased-' || id || '@erased.invalid', name = '[erased]', erased_at = now()
   WHERE id = $1;
  ```
- **Tension:** the invoice snapshot keeps PII by design, since an invoice is a legal record. Whether tax or financial retention law overrides an erasure request, and for how long, is a legal question I cannot verify. Get counsel's answer before shipping an erasure flow.
- **Audit log:** it deliberately omits `bill_to_name` and `bill_to_email`, but `payments` and `subscriptions` rows are logged in full and hold no PII.
- **Encryption at rest and column-level encryption** are host-level concerns I haven't designed.

### Irreversible or loud steps

- The down migration drops the audit log and all invoices (see the warning in section 4).
- Append-only and frozen-record triggers block manual fixes. A wrong finalized invoice is corrected by void-and-reissue or a credit note, never by `UPDATE`. Agree on a break-glass procedure (owner disables the trigger inside a transaction, with a ticket) before you need one.
- `CREATE EXTENSION btree_gist` needs a privileged role on some hosts, and the down script leaves it installed.

### Suggested ledger entries

Per your habit of logging non-obvious decisions, these four are worth `ledger log` before the first commit:

- Composite FKs pin currency and customer consistency in the DB.
- Payments are recorded as facts, with an anomaly view rather than rejection.
- Invoice totals and the bill-to snapshot are derived by trigger at finalization.
- `text` plus `CHECK` was chosen over enum types.