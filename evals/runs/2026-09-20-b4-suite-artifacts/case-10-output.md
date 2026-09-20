## Failure

**Expected:** after a user saves a record, the UI shows the saved values.
**Actual:** in roughly 1 of 5 saves (your estimate, unverified), the UI shows the pre-save data. A manual refresh shows the correct data.
**Trigger condition:** it happens right after a save. The window is short, and the refresh clears it.

Two things follow from what you told me:
- **The write persisted.** If the refresh shows the new value, it wasn't lost, so the bug is in how the data is read or displayed. The lost-update theory (H6 below) is weak.
- **The bug is timing- or routing-dependent.** A 20% rate rules out a deterministic logic error.

I don't have a stack trace, logs, the fetch library, the read-routing mechanism, or the deploy history. Everything below is ranked from priors, not evidence.

## Reproduction

I can't run anything, so this is what to build.

1. Write a script that authenticates and loops 200 times: `PUT`/`PATCH` the record with a unique, incrementing value, then immediately `GET` it by the same path the UI uses.
2. Log per iteration: stale or fresh, the gap between the PUT response and the GET start, the request IDs, and which DB host served the GET.
3. Run two controls: the same loop with a 1s delay before the GET, and the same loop with the GET forced to the primary.
4. Run it against something load-bearing. An idle staging replica may show near-zero lag and hide the bug.
5. **Probe 0, which splits the whole space:** in the browser, capture one stale occurrence with Network → Preserve log. Check whether the stale values are in the raw HTTP response body.
   - Stale in the body means the server side, H1 to H5.
   - Fresh body but stale UI means the client, H2.

## Hypotheses (ranked by likelihood × ease of test)

**H1. Replication lag: a read-your-writes violation. Confidence: medium, lead theory.**
- **Why plausible:** it's the one architectural feature you named that produces exactly this shape. The write commits on the primary, the follow-up read is routed to an asynchronous replica that hasn't replayed it, and a human refresh seconds later hits a caught-up replica.
- **Open question:** a 20% rate needs lag comparable to the save-to-refetch gap. That's plausible under load, or with several replicas where one lags.
- **Probe:**
  - Log the primary's `pg_current_wal_lsn()` right after the write commits.
  - On the stale read, log the serving replica's `pg_last_wal_replay_lsn()` and `pg_last_xact_replay_timestamp()`.
  - Replay LSN behind the write LSN confirms it.
  - Also check `pg_stat_replication.replay_lag` on the primary.
  - Then pin that one GET to the primary. If stale reads drop to about 0, it's confirmed. If they persist, H1 is dead.

**H2. Client-side race or missing invalidation. Confidence: medium, cheapest to test.**
- **Why plausible:** an in-flight refetch (polling, focus refetch, a list query) that started before the save resolved can return after it and overwrite the fresh state. Alternatively the mutation doesn't invalidate the right cache key. Both are timing-dependent, so both are intermittent, and a refresh clears client state.
- **Probe:** log timestamps for the PUT start, the PUT response, and every GET start and response. A stale render preceded by a GET that started before the PUT response, or a response order inverted relative to the request order, confirms it. Also turn off background refetch and see whether the rate drops. Fresh body with stale UI in Probe 0 is direct confirmation.

**H3. HTTP cache: browser, CDN, or proxy. Confidence: low to medium.**
- **Why plausible:** GET responses without `Cache-Control: no-store` or `no-cache` can be reused heuristically. A refresh revalidates, which matches your symptom. The 1-in-5 could come from different edge nodes.
- **Probe:** on a stale response, read `Cache-Control`, `Age`, `Date`, any `X-Cache` header, and the "from disk cache" or "from memory cache" flag in the Network tab. An `Age` above 0 or a cache flag confirms it. No cache markers kills it.

**H4. The save handler's own read-back is stale, or the write is asynchronous. Confidence: low to medium.**
- **Why plausible:** if the PUT response body is built from a replica read, or the endpoint enqueues the write and returns before the worker commits, the user sees old data straight from the save response.
- **Probe:** check whether the stale values appear in the PUT/PATCH response body itself. Then check for a queue in the save path and compare commit time against response-sent time. Stale values in the save response point here or to H1. A fresh save response followed by a stale GET points elsewhere.

**H5. Application-tier cache that isn't invalidated per instance. Confidence: low.**
- **Why plausible:** with several app instances and an in-process or ORM-level cache, only the instance that handled the write invalidates. Reads that land elsewhere serve stale data until the TTL expires. Whether one exists is unknown to me.
- **Probe:** first establish whether any cache exists in the read path (Redis, memoization, ORM second-level cache). Then log the instance ID and cache hit or miss on the stale GET. A hit on a different instance than the writer confirms it.

**H6. The write was overwritten or lost. Confidence: low.**
- **Why plausible:** an autosave or stale-form resubmit could clobber the new value.
- **Against it:** the refresh shows the new data. That is strong evidence the value persisted. I'm keeping it only so it's explicitly killed.
- **Probe:** query the row's update history or audit trail for a second write inside the stale window.

## Most likely, and why

**Lead: H1, with H2 as the close second.** H1 leads because the read replica is the stack detail most tied to "stale right after a write, self-heals on refresh." But the two are hard to separate from the symptom alone. Probe 0 costs a few minutes and splits them, so run it first.

**Does the lead explain all the evidence?**
- **Refresh fixes it:** yes, as time passes for H1. This doesn't discriminate, because H2 and H3 explain it equally.
- **About 1 in 5:** partly. This is the weak spot. It needs lag comparable to the round-trip time, which is possible but not established.
- **What would prove me wrong:**
  - A stale read where the serving replica's replay LSN was already past the write LSN.
  - A fresh response body with a stale render.
  - A stale read that survives a pin to the primary.

**Trigger versus root cause:**
- **Trigger:** the read happening right after the write.
- **Root cause, if H1 holds:** the read path has no read-your-writes guarantee against an async replica.
- Changing the trigger, for example delaying or suppressing the refetch, would hide the bug without fixing it.

I'm not proposing a fix yet. Which fix is right depends on which hypothesis survives.

## Observations that would sharpen the ranking

1. Probe 0's result: is the stale data in the response body?
2. Do users ever need to refresh twice? That suggests lag, multiple replicas, or a cache TTL, and it kills any theory where the first refresh always fixes it.
3. Which fetch library the frontend uses, and whether it refetches after save or uses the PUT response.
4. How reads reach the replica: an app-level split, pgbouncer/pgpool, or the ORM.
5. Whether replication is async, and how many replicas there are.
6. When it started, and whether the replica was added recently. A `git bisect` or deploy correlation would be cheap if the start date is known.