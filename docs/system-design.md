# Dashboard Statistics — System Design

**User story:** US-07 — As a Job Seeker, I want to view a dashboard with application
statistics, so that I can track my overall job hunt performance at a glance.

---

## 1. Sub-features

### 1. Pipeline Status Breakdown & Counters (The Funnel)
- **What it does:** Displays aggregate counts for every stage of the job hunt pipeline.
- **Why it matters:** Gives instant visibility into volume across statuses.
- **Note:** `Rejected` is a terminal *outcome*, not a funnel stage — a rejection can
  arrive from any stage. It is rendered as a separate counter, not as the last bar of
  the funnel, or the funnel implies a progression that did not happen.

### 2. Conversion Success Rate Metrics (Performance Ratios)
- **What it does:** Calculates percentage ratios from the user's own data.
  - Interview Rate: applications that **ever reached** Interviewing ÷ total applications
  - Offer Rate: applications that **ever reached** Offer ÷ total applications
- **Why it matters:** Evaluates whether the resume or targeting strategy is working,
  without manual math.
- **Note:** "ever reached" is the critical word — see §4.

### 3. Recent Activity & Milestone Highlights
- **What it does:** Surfaces recent status changes, upcoming interviews, and newly
  generated AI cover letters.
- **Why it matters:** Keeps focus on immediate action items rather than raw numbers.

### 4. Historical Application Trends (Timeline/Velocity)
- **What it does:** Visualises application volume over time (per week or month).
- **Why it matters:** Tracks consistency and effort velocity.

---

## 2. What the current schema can and cannot answer

Checked against [`models.py`](../backend/app/models.py). Two of the four sub-features
are **not buildable** on today's tables:

| Sub-feature | Buildable now? | Blocker |
| :--- | :--- | :--- |
| 1. Funnel counters | Yes, after §3 | `status` is unconstrained free text |
| 2. Conversion rates | **No** | No status history — cannot know what a job *ever reached* |
| 3. Recent activity | **Partly** | No status-change log; no interview date field; no timestamp for cover-letter generation |
| 4. Trends over time | Yes | `created_at` exists; needs a timezone decision (§6) |

`jobs` currently carries only `created_at` and `updated_at`. `updated_at` fires on
*any* edit — fixing a typo in a company name bumps it — so it cannot stand in for
"recent status update".

---

## 3. Canonical status model (prerequisite)

The single largest correctness risk. `status` is `Column(String, default="Applied")`
with no constraint, and four sources already disagree:

| Source | Says |
| :--- | :--- |
| [`models.py`](../backend/app/models.py) | default `"Applied"`, any string accepted |
| [`schemas.py`](../backend/app/schemas.py) | `status: Optional[str] = "Applied"` |
| [`seed.py`](../backend/app/seed.py) | writes `"Offered"` |
| [`database-schema.md`](database-schema.md) | default `'Wishlist'`; values `Wishlist, Applied, Interviewing, Offer, Rejected` |
| This document (previously) | `Applied, Interviewing, Offer, Rejected` |

`PUT /jobs/{job_id}` accepts any string, so `"applied"`, `"APPLIED"` and `""` are all
storable today. A `GROUP BY status` over realistic data:

```
'Applied' 2   'applied' 1   'APPLIED' 1   'Rejected' 1
'Offered' 1   'Offer'   1   'Interviewing' 1   '' 1

Funnel as designed -> {'Applied': 2, 'Interviewing': 1, 'Offer': 1, 'Rejected': 1}
Rows counted       -> 5 of 9  (4 silently dropped)
Offer Rate         -> 11%     (even though a job IS in 'Offered')
```

The dashboard does not error — it quietly reports wrong numbers, which is worse.

**Decision:** one canonical enum, defined once in code and enforced in the database.

```
Wishlist → Applied → Interviewing → Offer
                  ↘             ↘
                     Rejected  ←
```

- Canonical values: `Wishlist`, `Applied`, `Interviewing`, `Offer`, `Rejected`
- Define as a Python `enum.Enum`, referenced by `models.py` and `schemas.py` so
  Pydantic rejects unknown values with a 422 at the edge
- Add a DB `CHECK` constraint (or native `ENUM` type) so nothing can bypass the API
- Align `seed.py` (`"Offered"` → `"Offer"`) and reconcile the default with
  `database-schema.md` — code says `Applied`, the doc says `Wishlist`; pick one
- Backfill existing rows before adding the constraint

**Ordering matters for the funnel.** The enum needs an explicit rank
(`Wishlist=0 … Offer=3`), because alphabetical ordering renders the funnel as
Applied → Interviewing → Offer → Rejected → Wishlist, which is nonsense.

---

## 4. Metric definitions

Ambiguity here produces numbers that look plausible and are wrong.

**"Interviews" means jobs that ever reached Interviewing, not jobs currently in it.**
A job that went Applied → Interviewing → Rejected sits in `Rejected` today. Counting
current status would report an Interview Rate of 0% for a user who interviewed four
times and was turned down — the exact opposite of the truth, and precisely the signal
this feature exists to surface.

That history does not exist in the schema. It requires §5.

| Metric | Definition | Denominator |
| :--- | :--- | :--- |
| Total applications | Jobs that ever reached `Applied` or beyond | — |
| Interview Rate | Jobs that ever reached `Interviewing` ÷ total applications | Total applications |
| Offer Rate | Jobs that ever reached `Offer` ÷ total applications | Total applications |
| Response Rate | Jobs that left `Applied` in any direction ÷ total applications | Total applications |

- `Wishlist` jobs are **excluded from the denominator** — they were never submitted, and
  including them deflates every rate.
- **Division by zero:** a new user has zero applications. Rates are `null`, not `0` —
  the UI shows "—", not "0%", which reads as failure rather than absence of data.
- Round for display only; keep full precision in the payload.

---

## 5. Required schema additions

### `job_status_events` (new table)

Append-only log; the source of truth for sub-features 2 and 3.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | |
| `job_id` | UUID | FK → `jobs.id`, ON DELETE CASCADE, NOT NULL | |
| `user_id` | UUID | FK → `users.id`, NOT NULL | Denormalised so dashboard queries never join `jobs` |
| `from_status` | VARCHAR(50) | NULL | Null on the row's first event |
| `to_status` | VARCHAR(50) | NOT NULL | |
| `changed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

Written on create and on every status change in
[`update_job`](../backend/app/routers/jobs.py). Emit **only when the status actually
differs** — `PUT` with an unchanged status must not create an event, or "recent
activity" fills with noise.

This also unlocks time-in-stage metrics ("median days from Applied to Interviewing")
later, at no extra write cost.

### Additions to `jobs`

| Column | Type | Why |
| :--- | :--- | :--- |
| `interview_date` | TIMESTAMPTZ NULL | Sub-feature 3 promises "upcoming interviews"; nothing in the schema can answer that today |
| `cover_letter_generated_at` | TIMESTAMPTZ NULL | `ai_cover_letter IS NOT NULL` proves one exists, not that it is *new* |

Both are additive and nullable — no backfill needed.

> There is no migration tooling in the project yet (`Base.metadata.create_all` only).
> These changes alter existing tables, so this is the point to add Alembic.

---

## 6. API contract

**One endpoint, one round trip.** Four separate calls would mean four auth checks and
four connection checkouts to render a single screen, and the widgets could disagree if
data changed mid-render.

`GET /dashboard/stats?range=90d` → `200`

```json
{
  "generated_at": "2026-08-13T02:49:33Z",
  "funnel": {
    "counts": { "Wishlist": 3, "Applied": 24, "Interviewing": 5, "Offer": 1, "Rejected": 12 },
    "total_tracked": 45,
    "total_applications": 42
  },
  "rates": {
    "interview_rate": 0.238,
    "offer_rate": 0.047,
    "response_rate": 0.428
  },
  "recent_activity": [
    { "type": "status_change", "job_id": "…", "company_name": "Acme",
      "from_status": "Applied", "to_status": "Interviewing",
      "occurred_at": "2026-08-12T14:02:00Z" }
  ],
  "upcoming_interviews": [
    { "job_id": "…", "company_name": "Acme", "job_title": "Backend Engineer",
      "interview_date": "2026-08-15T09:00:00Z" }
  ],
  "trend": {
    "bucket": "week",
    "points": [ { "period_start": "2026-06-01", "applications": 7 } ]
  }
}
```

- **Auth:** required. Every query filters `user_id == current_user.id`, matching the
  existing pattern in [`jobs.py`](../backend/app/routers/jobs.py). This is the one
  invariant with real security consequences — a missing filter leaks another user's
  entire job hunt.
- **Rates are `null`, never `0`,** when the denominator is zero.
- **`range`:** `30d` | `90d` | `1y` | `all`, default `90d`. Applies to `trend` and
  `recent_activity` only — funnel counts and rates are always lifetime, or the numbers
  shift under the user for no visible reason.
- Rates are returned as fractions (`0.238`); the client formats as percentages.
- Define a Pydantic `DashboardStats` response model so the shape is enforced and shows
  up in `/docs`.

---

## 7. Query strategy

**Aggregate in the database, never in Python.** The existing pattern in the jobs router
is `db.query(Job).filter(...).all()`, which for the dashboard would load every row and
every `job_description` and `ai_cover_letter` blob just to count them.

- Funnel: `SELECT status, COUNT(*) … WHERE user_id = :uid GROUP BY status`
- Rates: `SELECT to_status, COUNT(DISTINCT job_id) FROM job_status_events WHERE user_id = :uid GROUP BY to_status`
- Trend: `date_trunc('week', created_at)` with `GROUP BY 1`
- **Zero-fill in Python.** SQL returns no row for a status with no jobs and no row for
  a week with no applications. Both must be filled — a missing bucket becomes a gap in
  the chart and a missing key in the funnel.

**Indexes:** `(user_id, status)` on `jobs`, `(user_id, created_at)` on `jobs`,
`(user_id, changed_at)` on `job_status_events`.

**Caching: none.** This is per-user data in the low hundreds of rows; the indexed
aggregates run in single-digit milliseconds. Caching would add staleness — a user who
updates a status expects the dashboard to reflect it immediately — for no measurable
gain. Revisit only if a user crosses ~10k jobs.

---

## 8. Edge cases

| Case | Expected behaviour |
| :--- | :--- |
| New user, zero jobs | `200` with zeroed counts, `null` rates, empty arrays. Never `404` |
| Only Wishlist jobs | Funnel shows them; rates are `null` (denominator is 0) |
| All jobs rejected | Interview/Offer rates reflect history, not the current all-`Rejected` state |
| Job deleted | Its events cascade-delete; historical rates change. Documented, accepted |
| Interview date in the past | Excluded from "upcoming"; still present in recent activity |
| Legacy rows with no events | Seed one synthetic event at `created_at` during migration, or they vanish from every rate |

---

## 9. Out of scope

Cross-user benchmarking ("you interview more than average"), salary analytics,
per-company breakdowns, CSV export, and email digests. Each is a separate story.

---

## 10. Acceptance criteria

1. `GET /dashboard/stats` returns `401` without a valid token.
2. A user's numbers never include another user's jobs.
3. A new user with zero jobs gets `200` with `null` rates and empty arrays.
4. A job moved Applied → Interviewing → Rejected counts toward Interview Rate.
5. Funnel counts sum to `total_tracked` — no status is silently dropped.
6. Trend buckets with zero applications appear as `0`, not as gaps.
7. `PUT /jobs/{id}` with an unchanged status creates no activity entry.
8. The whole payload is one request and one DB round trip per widget.

---

## 11. Build order

1. Canonical status enum + DB constraint + backfill + fix `seed.py` (§3)
2. Alembic, then `job_status_events` and the two `jobs` columns (§5)
3. Emit events from `create_job` / `update_job`
4. `GET /dashboard/stats`: funnel and trend first (§6, §7)
5. Rates and recent activity, once events have accumulated
6. Frontend widgets

Step 1 is a prerequisite for everything else and is worth doing even if the dashboard
slips — it is currently possible to corrupt the pipeline with a typo.


# Search & Filtering — System Design

**User story:** US-08 — As a Job Seeker, I want to search and filter my applications by
keyword or status, so that I can quickly find specific entries without scrolling
endlessly.

**Purpose:** Let users narrow the application list using status categories and keyword
text search.

---

## 1. Corrections against the implemented code

The original draft was written before US-07 landed and no longer matches the codebase:

| Draft said | Reality in code | Consequence |
| :--- | :--- | :--- |
| Route `GET /api/jobs` | `GET /jobs/` — the router sets `prefix="/jobs"` and `main.py` adds no `/api` prefix | Frontend calling `/api/jobs` gets a 404 |
| `Job.company`, `Job.title` | Columns are `company_name` and `job_title` | `AttributeError` at import |
| `status` is a string | `status` is the `JobStatus` enum, with a DB `CHECK` constraint | See §2 |
| "Add index on `jobs(user_id, status)`" | Already exists as `ix_jobs_user_status` | Nothing to do |
| "and text columns" | A B-tree index does **not** serve `ILIKE '%term%'` | See §4 |

---

## 2. API contract

**Route:** `GET /jobs/` — extend the existing endpoint rather than adding a new one.
Search and filter are *views of the same collection*; a separate `/jobs/search` would
duplicate the auth, scoping and serialisation logic and drift from it over time.

| Parameter | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `status` | `JobStatus` | `None` | Typed as the enum, **not** a bare string |
| `search` | `str` | `None` | Case-insensitive, matched against `company_name` and `job_title` |
| `limit` | `int` (1–100) | `50` | |
| `offset` | `int` (≥ 0) | `0` | |
| `sort` | `newest` \| `oldest` \| `company` \| `updated` | `newest` | |

**Type `status` as the enum.** With a bare string, `?status=Offered` returns an empty
list and the user concludes they have no offers — a wrong answer delivered with a 200.
Typed as `JobStatus`, FastAPI rejects it with a 422 naming the valid values. This is
the same class of bug the canonical enum in §3 was introduced to kill, and the query
layer is the last place it can still leak in.

**Security:** every query keeps `Job.user_id == current_user.id`, matching the
existing pattern. Filters are *added to* that clause, never replace it.

---

## 3. Pagination and ordering

Neither was in the draft. Both are required for this story, not nice-to-haves.

**`GET /jobs/` is currently unbounded** — it returns every job with every
`job_description` and `ai_cover_letter` blob attached. "Without scrolling endlessly"
is not solved by filtering alone: a user with 400 applications who filters to
`Rejected` still gets 200 rows in one payload.

**`get_jobs` has no `ORDER BY` at all.** Postgres is free to return rows in any order,
and that order can change between identical requests. Today that is a cosmetic
annoyance; the moment `limit`/`offset` are added it becomes a correctness bug — with an
unstable sort, paging from offset 0 to 50 can show the same job twice and never show
another. **Add the `ORDER BY` before the pagination**, not after.

Every sort needs a deterministic tiebreaker, since `created_at` values can collide:

```
newest  -> created_at DESC, id DESC
oldest  -> created_at ASC,  id ASC
company -> company_name ASC, id ASC
updated -> updated_at DESC, id DESC
```

**Response shape.** Paging needs a total count, so the client can render "showing 1–50
of 213". That is a breaking change to an endpoint that currently returns a bare array:

- **Option A (chosen):** envelope — `{ "items": [...], "total": 213, "limit": 50, "offset": 0 }`.
- Option B: keep the array, return the count in an `X-Total-Count` header. Avoids the
  break but hides the count from `/docs` and from anything reading only the body.

Option A is chosen because [`frontend/`](../frontend) is still empty — there is no
consumer to break. Doing it later means versioning the endpoint.

`total` is a separate `COUNT(*)` with the **same filters and no limit**. It counts
matches, not the page.

---

## 4. Keyword search

```python
term = search.strip()
if term:
    pattern = f"%{term}%"
    query = query.filter(or_(
        Job.company_name.ilike(pattern),
        Job.job_title.ilike(pattern),
    ))
```

Three things the draft omitted:

- **Escape LIKE wildcards.** A user searching for `100%` or `senior_dev` gets `%` and
  `_` interpreted as wildcards and sees nonsense matches. Escape them
  (`\` + `%`/`_`/`\`) and pass `escape="\\"` to `ilike`.
- **Treat blank as absent.** `?search=` and `?search=%20` must mean "no filter", not
  "match rows containing an empty string" — the latter is harmless but the strip is
  needed anyway to avoid a stray-space search returning nothing.
- **Scope is `company_name` + `job_title` only.** Deliberately *not* `job_description`:
  descriptions are thousands of words of boilerplate, and including them makes almost
  every query match almost every row. Revisit only with real full-text search.

**Indexing.** A B-tree index cannot serve `ILIKE '%term%'` — the leading wildcard makes
it unusable, and Postgres will sequential-scan regardless of what index exists. The
draft's "index on text columns" would consume disk and speed nothing up. The correct
tool is a trigram index:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_jobs_company_trgm ON jobs USING gin (company_name gin_trgm_ops);
CREATE INDEX ix_jobs_title_trgm   ON jobs USING gin (job_title gin_trgm_ops);
```

`pg_trgm` is available on the project's Postgres 15.18 image but **not currently
installed**. That said: at a few hundred rows per user, a sequential scan behind the
`user_id` filter is already sub-millisecond. **Defer the trigram indexes** and add them
only if row counts justify it — record the decision here so it is a choice rather than
an oversight.

---

## 5. Edge cases

| Case | Expected |
| :--- | :--- |
| No filters | Current behaviour, plus pagination — first 50, newest first |
| Filters match nothing | `200` with `{"items": [], "total": 0}` — never `404` |
| `?status=Offered` | `422` listing the valid statuses |
| `?search=` or whitespace | Treated as no filter |
| `?limit=5000` | `422` — bounded at 100 |
| `offset` past the end | `200`, empty `items`, `total` still the real match count |
| Search term with `%`, `_`, `\` | Matched literally |
| Both filters | `AND`-ed: status **and** keyword |

---

## 6. Frontend (React + TypeScript)

- Local state for `searchQuery`, `selectedStatus`, `sort`, `offset`.
- Text input, plus a dropdown or button group built from the `JobStatus` values —
  fetch them from the API rather than re-typing the list in the client, or you
  reintroduce the string-drift problem in a third place.
- **Debounce the search input by ~300 ms.** Fetching per keystroke sends a request per
  character and the responses can arrive out of order, leaving the list showing results
  for a prefix of what is in the box.
- Reset `offset` to 0 whenever a filter changes, or the user lands on page 5 of a
  3-page result set and sees an empty list.
- Mirror the filters into the URL query string so a filtered view is shareable and
  survives a refresh.

---

## 7. Acceptance criteria

1. `GET /jobs/` without parameters behaves as before, plus pagination and a stable order.
2. `?status=Interviewing` returns only that status, for the current user only.
3. `?search=goog` matches "Google" case-insensitively in company or title.
4. `?status=X&search=y` applies both filters together.
5. An invalid status returns `422`, not an empty list.
6. `total` reflects all matches, not the page size.
7. Paging through the whole set with a fixed sort yields every job exactly once.
8. A search containing `%` or `_` matches those characters literally.

---

## 8. Build order

1. Add `ORDER BY` to `get_jobs` — independently correct, and a prerequisite for paging
2. Envelope response + `limit`/`offset` + `total`
3. `status` filter (typed as `JobStatus`)
4. `search` filter with wildcard escaping
5. Frontend controls with debounce and URL sync
6. Trigram indexes — only if measurement shows they are needed (§4)