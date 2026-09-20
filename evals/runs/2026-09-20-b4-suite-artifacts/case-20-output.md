# Share-link API: `POST`, `DELETE`, and public `GET /share/:token`

I did not compile, run, or test this code. It is written against the schema in your message and the assumptions listed below.

## 1. Contract

**Error shape (all endpoints):** `{ "error": { "code": "<machine_code>", "message": "<safe text>" } }`. Nothing internal appears in it.

### `POST /dashboards/:dashboardId/share-links`

The route path is my choice, since you gave only the verb. The owner generates a link.

| | |
|---|---|
| Auth | Required. The caller must own `:dashboardId`. |
| Headers | `Idempotency-Key`: **required**, 16–128 chars of `[A-Za-z0-9_-]`. A UUID v4 is recommended. |
| Body | `{ "expires_in_seconds"?: int }`, range 300 to 7,776,000 (90 days), default 604,800 (7 days). Unknown keys are rejected. |
| 201 | New link: `{ id, dashboard_id, expires_at, token, url }`. The **plaintext token appears only in this response**. |
| 200 | Replay of the same `Idempotency-Key` with identical parameters returns the same body, with header `Idempotent-Replayed: true`. |
| 400 | Malformed id, header, or body. |
| 401 | Not authenticated. |
| 404 | Dashboard doesn't exist **or** isn't the caller's (indistinguishable, so it can't be probed). |
| 409 | `idempotency_key_spent`: the key's link was already revoked or expired, so use a new key. `share_link_limit_reached`: 25 active links per dashboard. |
| Side effects | One INSERT into `dashboard_share_links`, atomic and idempotent. |

### `DELETE /dashboards/:dashboardId/share-links/:linkId`

The owner revokes a link by its row `id`, not by token. The token can't be recovered from its hash.

| | |
|---|---|
| Auth | Required. The caller must own the dashboard. |
| 204 | Revoked now, or already revoked, so a retry is safe. |
| 404 | The link isn't under this dashboard, or the dashboard isn't the caller's. |
| Side effects | Sets `revoked_at = now()` and `revoked_by = caller`, only where `revoked_at IS NULL`. |

### `GET /share/:token`

Public and read-only, with no authentication.

| | |
|---|---|
| 200 | `{ title, updated_at, expires_at, widgets[] }`, an explicit allow-list projection. It includes no owner id, link id, or internal ids. |
| 404 | The **same body** for every failure: malformed, unknown, revoked, expired, or dashboard gone. It reveals nothing about which. |
| Headers | `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex, nofollow`, `X-Content-Type-Options: nosniff` |
| Side effects | None. It is a pure read. |

## 2. Implementation

This is a Node/TypeScript Express module. It uses Express, `pg` and `zod`, which is my assumption because you gave no stack. The plain-English map:

- **Boundary:** validate ids, header, and body before any DB call.
- **Authz:** the SQL itself checks `owner_id = caller`.
- **Token:** the token is derived with HMAC from the caller, dashboard, TTL, and Idempotency-Key. A retried POST produces the same token and hits your existing `UNIQUE(token_hash)`, so retries are idempotent with no schema change.
- **Public read:** the query itself excludes revoked and expired links.

Install (PowerShell): `npm install express pg zod` and `npm install -D @types/express @types/pg`.

`src/share-links/share-links.router.ts`:

```ts
import { createHash, createHmac } from "node:crypto";
import express, { Router, type Request, type RequestHandler, type Response } from "express";
import type { Pool, PoolClient } from "pg";
import { z } from "zod";

// ───────────────────────── policy constants ─────────────────────────
const MIN_TTL_SECONDS = 300; // 5 minutes
const DEFAULT_TTL_SECONDS = 7 * 24 * 3600; // 7 days
const MAX_TTL_SECONDS = 90 * 24 * 3600; // 90 days: no "never expires" links
const MAX_ACTIVE_LINKS_PER_DASHBOARD = 25;

// Own regexes (not library helpers) so behavior doesn't shift with library versions.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/; // 32 random bytes, base64url, no padding
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9_-]{16,128}$/;

// ───────────────────────── types ─────────────────────────
type Queryable = Pick<Pool, "query">;

/** What `requireAuth` is ASSUMED to attach. I did not invent an auth layer. */
interface AuthedRequest extends Request {
  user?: { id: string };
}

/** The loader MUST return only fields safe to show an anonymous viewer. */
export interface PublicWidgetDto {
  id: string;
  type: string;
  title: string;
  data: unknown;
}

interface PublicDashboardDto {
  title: string;
  updated_at: string;
  expires_at: string;
  widgets: PublicWidgetDto[];
}

export interface ShareLinkDeps {
  pool: Pool;
  /** >= 32 bytes, from your secret manager. Never logged. */
  tokenHmacKey: Buffer;
  /** e.g. "https://app.example.com". Config, NEVER derived from the Host header. */
  publicOrigin: string;
  /** Assumed existing: authenticates and sets req.user = { id }. */
  requireAuth: RequestHandler;
  /** Per-user limiter for the two owner endpoints (injected: I didn't pick a library). */
  writeLimiter: RequestHandler;
  /** Per-IP limiter for the public endpoint. */
  publicReadLimiter: RequestHandler;
  /** Loads the public projection of the dashboard's widgets. Needs the real dashboard schema. */
  loadPublicWidgets(db: Queryable, dashboardId: string): Promise<PublicWidgetDto[]>;
  logger: {
    info(o: Record<string, unknown>, msg: string): void;
    error(o: Record<string, unknown>, msg: string): void;
  };
}

// ───────────────────────── helpers ─────────────────────────
class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

function sendError(res: Response, status: number, code: string, message: string): void {
  res.status(status).json({ error: { code, message } });
}

/** Wraps an async handler so a thrown error reaches our catch (safe on Express 4 and 5). */
const wrap =
  (fn: (req: Request, res: Response) => Promise<void>): RequestHandler =>
  (req, res, next) => {
    fn(req, res).catch(next);
  };

/** Runs fn in one transaction, with timeouts so a stuck lock can't pin a connection. */
async function withTx<T>(pool: Pool, fn: (c: PoolClient) => Promise<T>): Promise<T> {
  const c = await pool.connect();
  let destroy = false;
  try {
    await c.query("BEGIN");
    await c.query("SET LOCAL statement_timeout = '5s'");
    await c.query("SET LOCAL lock_timeout = '3s'");
    const out = await fn(c);
    await c.query("COMMIT");
    return out;
  } catch (e) {
    try {
      await c.query("ROLLBACK");
    } catch {
      destroy = true; // rollback failed: don't return a possibly-dirty connection to the pool
    }
    throw e;
  } finally {
    c.release(destroy);
  }
}

const sha256Hex = (s: string): string => createHash("sha256").update(s).digest("hex");

/**
 * Deterministic token. Same (user, dashboard, ttl, idempotency key) -> same token -> same
 * token_hash -> the UNIQUE(token_hash) constraint makes a retried POST collapse to one row.
 * 256 bits of HMAC output, so it is unguessable without the server key.
 */
function deriveToken(
  key: Buffer,
  userId: string,
  dashboardId: string,
  ttlSeconds: number,
  idempotencyKey: string,
): string {
  return createHmac("sha256", key)
    .update(JSON.stringify(["share-link-v1", userId, dashboardId, ttlSeconds, idempotencyKey]))
    .digest("base64url");
}

const createBodySchema = z
  .object({
    expires_in_seconds: z.number().int().min(MIN_TTL_SECONDS).max(MAX_TTL_SECONDS).optional(),
  })
  .strict(); // rejects created_by / token_hash / revoked_at etc. (no mass assignment)

/** Last-resort error mapper: log the class and code only (never the message: pg can echo values). */
function handleUnexpected(
  err: unknown,
  res: Response,
  deps: ShareLinkDeps,
  where: string,
): void {
  if (err instanceof ApiError) {
    sendError(res, err.status, err.code, err.message);
    return;
  }
  const pgCode = (err as { code?: string } | null)?.code;
  deps.logger.error({ where, pgCode, errName: (err as Error)?.name }, "share_link_unexpected_error");
  if (pgCode === "55P03" || pgCode === "57014") {
    res.setHeader("Retry-After", "2");
    sendError(res, 503, "busy", "Temporarily unavailable. Retry shortly.");
    return;
  }
  sendError(res, 500, "internal_error", "Something went wrong.");
}

// ───────────────────────── routers ─────────────────────────
export function createShareLinkRouters(deps: ShareLinkDeps): {
  ownerRouter: Router;
  publicRouter: Router;
} {
  const { pool } = deps;
  const ownerRouter = Router();
  const publicRouter = Router();

  // ── POST: owner generates a link ──────────────────────────────────────────
  ownerRouter.post(
    "/dashboards/:dashboardId/share-links",
    deps.requireAuth,
    deps.writeLimiter,
    express.json({ limit: "1kb" }), // tiny body cap: the only field is one integer
    wrap(async (req, res) => {
      res.setHeader("Cache-Control", "no-store"); // the response carries a bearer secret
      try {
        // 1. Authn (defense in depth: requireAuth should already have rejected).
        const userId = (req as AuthedRequest).user?.id;
        if (!userId) throw new ApiError(401, "unauthenticated", "Authentication required.");

        // 2. Validate every input BEFORE touching the DB.
        const dashboardId = req.params.dashboardId;
        if (!UUID_RE.test(dashboardId)) {
          throw new ApiError(400, "invalid_dashboard_id", "Invalid dashboard id.");
        }
        const idemKey = req.header("Idempotency-Key") ?? "";
        if (!IDEMPOTENCY_KEY_RE.test(idemKey)) {
          throw new ApiError(
            400,
            "invalid_idempotency_key",
            "Idempotency-Key header is required: 16-128 chars of A-Z a-z 0-9 _ -",
          );
        }
        const parsed = createBodySchema.safeParse(req.body ?? {});
        if (!parsed.success) {
          res.status(400).json({
            error: {
              code: "invalid_body",
              message: "Invalid request body.",
              fields: parsed.error.issues.map((i) => ({
                field: i.path.join("."),
                message: i.message,
              })),
            },
          });
          return;
        }
        const ttl = parsed.data.expires_in_seconds ?? DEFAULT_TTL_SECONDS;
        const dashId = dashboardId.toLowerCase();

        // 3. Derive token + hash. Only the hash is ever stored.
        const token = deriveToken(deps.tokenHmacKey, userId, dashId, ttl, idemKey);
        const tokenHash = sha256Hex(token);

        // 4. One transaction: authz on THIS dashboard, replay check, cap check, insert.
        const outcome = await withTx(pool, async (c) => {
          // Ownership check + lock. The lock serializes concurrent creators on this dashboard
          // so the cap can't be raced past. NO KEY UPDATE doesn't block the FK insert below.
          const owned = await c.query(
            `SELECT id FROM dashboards WHERE id = $1 AND owner_id = $2 FOR NO KEY UPDATE`,
            [dashId, userId],
          );
          if (owned.rowCount === 0) return { kind: "not_found" as const };

          // Replay? Same hash means same request. Must precede the cap check, so a retry
          // at the cap still succeeds.
          const existing = await c.query(
            `SELECT id, dashboard_id, created_by, expires_at,
                    (revoked_at IS NULL AND expires_at > now()) AS live
               FROM dashboard_share_links WHERE token_hash = $1`,
            [tokenHash],
          );
          if (existing.rowCount) {
            const row = existing.rows[0];
            const sameOwner = row.dashboard_id === dashId && row.created_by === userId;
            if (!sameOwner || !row.live) return { kind: "key_spent" as const };
            return { kind: "replayed" as const, id: row.id as string, expiresAt: row.expires_at as Date };
          }

          const active = await c.query(
            `SELECT count(*)::int AS n FROM dashboard_share_links
              WHERE dashboard_id = $1 AND revoked_at IS NULL AND expires_at > now()`,
            [dashId],
          );
          if (active.rows[0].n >= MAX_ACTIVE_LINKS_PER_DASHBOARD) return { kind: "limit" as const };

          // Expiry computed with the DB clock (UTC timestamptz), not the app clock.
          const ins = await c.query(
            `INSERT INTO dashboard_share_links (dashboard_id, created_by, token_hash, expires_at)
             VALUES ($1, $2, $3, now() + ($4::int * interval '1 second'))
             RETURNING id, expires_at`,
            [dashId, userId, tokenHash, ttl],
          );
          return { kind: "created" as const, id: ins.rows[0].id as string, expiresAt: ins.rows[0].expires_at as Date };
        });

        switch (outcome.kind) {
          case "not_found":
            throw new ApiError(404, "not_found", "Dashboard not found.");
          case "key_spent":
            throw new ApiError(409, "idempotency_key_spent", "That Idempotency-Key belongs to a link that was revoked or has expired. Use a new key.");
          case "limit":
            throw new ApiError(409, "share_link_limit_reached", `A dashboard can have at most ${MAX_ACTIVE_LINKS_PER_DASHBOARD} active share links.`);
        }

        // 5. Explicit response DTO. The token is shown here and never retrievable again.
        const replayed = outcome.kind === "replayed";
        if (replayed) res.setHeader("Idempotent-Replayed", "true");
        deps.logger.info(
          { event: replayed ? "share_link_replayed" : "share_link_created", linkId: outcome.id, dashboardId: dashId, userId },
          "share_link", // never log the token or the URL
        );
        res.status(replayed ? 200 : 201).json({
          id: outcome.id,
          dashboard_id: dashId,
          expires_at: outcome.expiresAt.toISOString(),
          token,
          url: `${deps.publicOrigin}/share/${token}`,
        });
      } catch (err) {
        handleUnexpected(err, res, deps, "POST share-links");
      }
    }),
  );

  // ── DELETE: owner revokes a link ──────────────────────────────────────────
  ownerRouter.delete(
    "/dashboards/:dashboardId/share-links/:linkId",
    deps.requireAuth,
    deps.writeLimiter,
    wrap(async (req, res) => {
      try {
        const userId = (req as AuthedRequest).user?.id;
        if (!userId) throw new ApiError(401, "unauthenticated", "Authentication required.");

        const { dashboardId, linkId } = req.params;
        if (!UUID_RE.test(dashboardId) || !UUID_RE.test(linkId)) {
          throw new ApiError(400, "invalid_id", "Invalid id.");
        }

        const outcome = await withTx(pool, async (c) => {
          // The join enforces BOTH "link belongs to this dashboard" and "caller owns it".
          // A link id from someone else's dashboard is simply not found (no IDOR).
          const r = await c.query(
            `SELECT l.id, l.revoked_at
               FROM dashboard_share_links l
               JOIN dashboards d ON d.id = l.dashboard_id
              WHERE l.id = $1 AND l.dashboard_id = $2 AND d.owner_id = $3
              FOR UPDATE OF l`,
            [linkId.toLowerCase(), dashboardId.toLowerCase(), userId],
          );
          if (r.rowCount === 0) return "not_found" as const;
          if (r.rows[0].revoked_at !== null) return "already_revoked" as const; // idempotent no-op
          await c.query(
            `UPDATE dashboard_share_links
                SET revoked_at = now(), revoked_by = $1
              WHERE id = $2 AND revoked_at IS NULL`,
            [userId, linkId.toLowerCase()],
          );
          return "revoked" as const;
        });

        if (outcome === "not_found") throw new ApiError(404, "not_found", "Share link not found.");
        deps.logger.info({ event: `share_link_${outcome}`, linkId, dashboardId, userId }, "share_link");
        res.status(204).end();
      } catch (err) {
        handleUnexpected(err, res, deps, "DELETE share-links");
      }
    }),
  );

  // ── GET /share/:token: PUBLIC read ────────────────────────────────────────
  publicRouter.get(
    "/share/:token",
    deps.publicReadLimiter,
    wrap(async (req, res) => {
      // Headers first, so 404s carry them too. A revoked link must never be served from a cache.
      res.setHeader("Cache-Control", "no-store");
      res.setHeader("Referrer-Policy", "no-referrer"); // the token is in the URL
      res.setHeader("X-Robots-Tag", "noindex, nofollow");
      res.setHeader("X-Content-Type-Options", "nosniff");

      const notFound = () => sendError(res, 404, "not_found", "Not found.");

      try {
        const token = req.params.token;
        if (!TOKEN_RE.test(token)) return notFound(); // malformed: same answer as unknown

        // Every read-time invariant lives in the query, so no code path can forget it:
        // not revoked, not expired (DB clock), dashboard still exists. Fail-closed on NULL expiry.
        const found = await pool.query(
          `SELECT l.id AS link_id, l.dashboard_id, l.expires_at, d.title, d.updated_at
             FROM dashboard_share_links l
             JOIN dashboards d ON d.id = l.dashboard_id
            WHERE l.token_hash = $1
              AND l.revoked_at IS NULL
              AND l.expires_at > now()`,
          [sha256Hex(token)],
        );
        if (found.rowCount === 0) return notFound(); // unknown / revoked / expired: indistinguishable

        const row = found.rows[0];
        const widgets = await deps.loadPublicWidgets(pool, row.dashboard_id);

        // Explicit allow-list DTO: no owner id, link id, dashboard id, or token hash.
        const dto: PublicDashboardDto = {
          title: row.title,
          updated_at: new Date(row.updated_at).toISOString(),
          expires_at: new Date(row.expires_at).toISOString(),
          widgets,
        };
        deps.logger.info({ event: "share_link_read", linkId: row.link_id }, "share_link"); // id only
        res.status(200).json(dto);
      } catch (err) {
        handleUnexpected(err, res, deps, "GET share");
      }
    }),
  );

  return { ownerRouter, publicRouter };
}
```

Wiring in your app entry file:

```ts
const { ownerRouter, publicRouter } = createShareLinkRouters({ /* deps */ });
app.use("/api/v1", ownerRouter); // authenticated owner endpoints
app.use(publicRouter);           // GET /share/:token, no auth
```

## 3. Safety notes

- **Validation:** ids must be UUIDs, the header and token are regex-checked, and the body is `.strict()` with bounded integers. Bodies over 1 KB are rejected. All of this runs before any DB call, so `created_by`, `token_hash`, and `revoked_*` can't be set by a client.
- **Authorization:** Authn and authz are separate. Every owner query includes `owner_id = caller`. DELETE joins link to dashboard to owner, so a guessed link id from another user's dashboard returns 404. Nonexistent and not-yours are the same 404.
- **Atomicity:**
  - POST is one transaction: ownership check with lock, replay check, cap check, insert. `SET LOCAL` statement and lock timeouts stop a stuck lock from pinning a connection.
  - The lock serializes concurrent creators, so the 25-link cap can't be raced.
  - The database `UNIQUE(token_hash)` backs the replay logic.
- **Idempotency:**
  - **POST:** The token is an HMAC of user, dashboard, TTL, and key, so a network retry reproduces the identical token and hash. It returns the same body with 200. Replaying a key whose link is revoked or expired returns 409, never a dead token as if it were live.
  - **DELETE:** It is idempotent by construction and returns 204 on repeat.
  - **Limit:** Identical parameters mean identical link. Reusing a key with a different TTL yields a different link, not an error, because the schema has nowhere to store the original parameters.
- **Storage:** Only `sha256(token)` is stored, so a DB leak yields no usable links. SHA-256 is enough because the token has 256 bits of entropy and doesn't need a slow hash.
- **Read-time invariants:** Revocation, expiry (DB clock), and dashboard existence are in the WHERE clause. A NULL `expires_at` fails closed as "not valid".
- **Immediate revocation:** No cache is read on GET, and `Cache-Control: no-store` prevents browser or CDN copies. A revoke takes effect on the next request.
- **Error leakage:** GET returns one uniform 404 for every failure. Unexpected errors log only the pg code and error class, because pg unique-violation messages can echo values. The client sees generic messages.
- **Logging:** The token is never logged, only link ids. The handler can't fix access logs, though. See the confirm-these list.
- **Money and time:** No money is involved. Timestamps are `timestamptz` computed with DB `now()`, and the API returns ISO-8601 UTC.

**Self-challenge:**
- *What input did I trust?* None unvalidated. Host isn't trusted, because the URL comes from config.
- *Which write isn't idempotent?* POST is only as idempotent as the client's key discipline.
- *Can caller A reach caller B's row?* Not through these queries.
- *What does an error leak?* Nothing that distinguishes the failure reasons.

## 4. Assumptions / confirm these

1. **Stack:** Node + Express (4 or 5) + `pg` + `zod`, and UUID primary keys with a `gen_random_uuid()` default on `id`. Confirm, or I'll port it (Next.js route handlers, Supabase RLS, etc.).
2. **Auth:** `requireAuth` exists and sets `req.user.id`. I built no auth layer. "Owner" means `dashboards.owner_id = caller`. If dashboards have teams, roles, or org admins, that predicate must change. It's the most important thing to confirm.
3. **Dashboards table:** I assumed `dashboards(id, owner_id, title, updated_at)`. You didn't give this schema, so `loadPublicWidgets` is an injected dependency I can't write without it.
4. **Widget data scope:** widgets must load with the dashboard's own data scope, not the creator's full permissions, or a share link could expose more than the dashboard shows. This is a design question for you.
5. **Column types:** I assumed `token_hash` is `text` (hex), and `expires_at`, `revoked_at` are `timestamptz`. If `token_hash` is `bytea`, switch to `createHash(...).digest()` (a Buffer).
6. **Policy choices:**
   - Expiry is always required (default 7 days, max 90).
   - The cap is 25 active links.
   - The Idempotency-Key header is required.
   - Change any of these freely, but "no expiry" is a real risk on a public link.
7. **Recommendations for `data-modeler` (I did not touch the schema):**
   - `expires_at NOT NULL`.
   - `CHECK ((revoked_at IS NULL) = (revoked_by IS NULL))`.
   - A `created_at` column.
   - A partial index on `(dashboard_id) WHERE revoked_at IS NULL` for the cap count.
   - The FK to `dashboards` should have a defined delete behavior.
8. **Secret key:** `tokenHmacKey` is at least 32 bytes from a secret manager. Rotating it only breaks in-flight POST retries. Existing links keep working, because GET hashes whatever token is presented.
9. **Access logs:** your proxy, load balancer, and CDN will log the path `/share/<token>`, which puts live bearer tokens in logs. Redact `/share/*` there. The handler can't fix this.
10. **Frontend page:** if the SPA page lives at the same `/share/:token` path, its page also needs `Referrer-Policy: no-referrer`, because outbound links would leak the token. Routing an API call to the same path is your call.
11. **Rate limiters and proxy:** limiters are injected, because I won't guess a library. Configure `trust proxy` correctly, or per-IP limiting sees only your proxy.
12. **Stale link on removal:** a link outlives its creator's access, for example if the creator is removed from the org. Whether to auto-revoke is a policy decision.
13. **UX option:** if you want "this link has expired" messages, return 410 for expired and revoked links. That leaks nothing to someone holding a real token, but I defaulted to the uniform 404.
14. **Unverified library behavior (standard APIs, not run here):** `digest("base64url")` on Node 24, `client.release(true)` destroying the connection in `pg`, `.strict()` in `zod`, and `express.json({ limit })`.
15. **Fallback if the HMAC-derived token is unacceptable:** use a random token plus an idempotency table. That needs a schema change, which is `data-modeler`'s call.

## 5. Tests needed (`test-author` pass)

**Happy path**
- POST returns 201, a 43-char token, and a URL on `publicOrigin`.
- The row stores `sha256(token)`, never the token.
- GET with that token returns 200 with exactly the DTO fields and no ids.
- The default TTL is 7 days and a custom TTL is honored.

**Authz**
- Caller B POSTs against A's dashboard and gets 404 with no row created.
- Caller B DELETEs A's link and gets 404, and the link stays live.
- A `linkId` from dashboard X sent under dashboard Y returns 404.
- An unauthenticated POST or DELETE returns 401, while an unauthenticated GET succeeds.
- The 404 body for "not yours" equals the 404 body for "doesn't exist".

**Validation**
- A bad UUID gets 400.
- A missing, short, or illegal-character `Idempotency-Key` gets 400.
- A body with `created_by`, `token_hash`, or `revoked_at` gets 400.
- `expires_in_seconds` of 299, 7,776,001, `1.5`, or `"60"` gets 400.
- A body over 1 KB gets 413.
- A malformed token on GET gets 404 with no DB query.

**Idempotency and retry**
- The same key and same params twice returns 201 then 200 with an identical body and `Idempotent-Replayed: true`, and the DB has one row.
- Two concurrent identical POSTs leave one row, and both callers get the same token.
- The same key with a different TTL creates a distinct link.
- A replay after revoke returns 409 `idempotency_key_spent`, and the same after expiry.
- A replay at the 25-link cap still returns 200.
- DELETE twice returns 204 both times, and `revoked_at` and `revoked_by` keep the first values.

**Read-time invariants**
- A revoked link gets 404 on the very next GET, with no cache delay.
- An expired link gets 404 (use a controlled clock or a row with a past `expires_at`).
- A NULL `expires_at` row gets 404.
- A link whose dashboard was deleted gets 404.
- Unknown, revoked, expired, and malformed tokens all give byte-identical 404 bodies.
- Every GET response carries `no-store`, `no-referrer`, `noindex`, and `nosniff`.

**Cap and race**
- The 26th active link returns 409, and 25 concurrent POSTs with distinct keys never exceed 25 rows.
- Revoked and expired links don't count toward the cap.

**Failure**
- A DB error mid-transaction rolls back with no partial row and returns a generic 500 with no pg text.
- A `lock_timeout` returns 503 with `Retry-After`.
- If `loadPublicWidgets` throws, GET returns a generic 500 and never a partial DTO.
- A failed ROLLBACK destroys the connection (spy on `release(true)`).

**Logging**
- No captured log line, on any path, contains the token, the URL, or `token_hash`.

**Security**
- The `Host` header can't change the returned `url`.
- A rate-limited GET returns 429.

Log this to Q as a commitment if you defer any of it, especially confirm-these items 2 and 3, since the whole authorization model depends on the owner definition.