# API Endpoints Documentation

## 1. Overview

- **Base URL (local):** `http://localhost:8000`.
  The router prefixes (`/jobs`, `/users`, `/resumes`, `/dashboard`) are the whole path.
- **Authentication:** `POST /login` with JWT auth
- **Content type:** JSON, except the form endpoints noted below.

---

## 2. Route Summary

| Endpoint Category | Method & Route | Description / Purpose | Request Payload | Response Type |
| :--- | :--- | :--- | :--- | :--- |
| **Root** | `GET /` | Health / welcome message | *None* | `{"message": ...}` |
| **Authentication** | `POST /login` | Authenticates user, sets auth cookie | Form: `username` (email), `password` | `access_token` + `Set-Cookie` |
| **Authentication** | `POST /logout` | Clears the auth cookie | *None* | `{"message": ...}` |
| **Users** | `POST /users/` | Registers a new user account | `email`, `password` | `201` Created user object |
| **Users** | `GET /users/me` | Current user's profile | *None (auth required)* | User object |
| **Users** | `PUT /users/me` | Updates email and password | `email`, `password` | Updated user object |
| **Users** | `DELETE /users/me` | Deletes the current account | *None (auth required)* | `204 No Content` |
| **Users** | `GET /users/` | Lists all registered users | *None (auth required)* | Array of users — see §6 |
| **Users** | `POST /users/login` | Duplicate login — see §6 | Form: `username`, `password` | `access_token` (**no cookie**) |
| **Users** | `POST /users/logout` | Broken — see §6 | — | — |
| **Job Tracking** | `GET /jobs/` | Lists, searches and filters applications | Query params (§3) | Paginated envelope (§3) |
| **Job Tracking** | `POST /jobs/` | Creates a new job application entry | `company_name`, `job_title`, etc. | `201` Created job object |
| **Job Tracking** | `GET /jobs/{job_id}` | Fetches a single application | *None (auth required)* | Job object |
| **Job Tracking** | `PUT /jobs/{job_id}` | Updates supplied fields only | Fields to change | Updated job object |
| **Job Tracking** | `DELETE /jobs/{job_id}` | Deletes a job application record | *None (auth required)* | `204 No Content` |
| **Resumes & AI** | `POST /jobs/{job_id}/generate-cover-letter` | Generates a tailored AI cover letter | *None (auth required)* | Updated job with `ai_cover_letter` |
| **Resumes & AI** | `POST /resumes/analyze` | Uploads a PDF resume, returns AI feedback | Multipart: `file`, optional `job_description` | Feedback object (§5) |
| **Dashboard** | `GET /dashboard/stats` | Aggregated job-hunt statistics | Query: `range` | Statistics payload (§4) |

Every route except `GET /`, `POST /users/`, `POST /login` and `POST /logout` requires
authentication, and results are scoped to the signed-in user.

---

## 3. `GET /jobs/` — search, filter and pagination (US-08)

| Parameter | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `status` | enum | *none* | `Wishlist` \| `Applied` \| `Interviewing` \| `Offer` \| `Rejected`. An unknown value returns `422`, not an empty list |
| `search` | string (≤ 100) | *none* | Case-insensitive, matched against `company_name` and `job_title`. `%` and `_` match literally |
| `limit` | int 1–100 | `50` | |
| `offset` | int ≥ 0 | `0` | |
| `sort` | enum | `newest` | `newest` \| `oldest` \| `company` \| `updated` |

**The response is an envelope, not a bare array:**

```json
{
  "items": [
    { "id": "…", "user_id": "…", "company_name": "Google",
      "job_title": "Full Stack Engineer", "job_description": "…",
      "status": "Interviewing", "interview_date": "2026-08-14T09:00:00Z",
      "ai_cover_letter": "…", "cover_letter_generated_at": "2026-07-02T10:11:00Z",
      "match_score": 92, "created_at": "…", "updated_at": "…" }
  ],
  "total": 213,
  "limit": 50,
  "offset": 0
}
```

`total` counts every row matching the filters, not the rows on this page.

---

## 4. `GET /dashboard/stats` — statistics (US-07)

`range` accepts `30d` | `90d` | `1y` | `all` (default `90d`) and applies to
`recent_activity` and `trend` only. `funnel` and `rates` are always lifetime, so the
headline numbers do not shift when the date picker changes.

```json
{
  "generated_at": "2026-08-13T02:49:33Z",
  "range": "90d",
  "funnel": { "counts": { "Wishlist": 2, "Applied": 3, "Interviewing": 3,
                          "Offer": 1, "Rejected": 13 },
              "total_tracked": 22, "total_applications": 20 },
  "rates": { "interview_rate": 0.25, "offer_rate": 0.05, "response_rate": 0.85 },
  "recent_activity": [ { "type": "status_change", "job_id": "…",
                         "company_name": "Notion", "job_title": "Product Engineer",
                         "from_status": "Applied", "to_status": "Interviewing",
                         "occurred_at": "2026-08-01T14:02:00Z" } ],
  "upcoming_interviews": [ { "job_id": "…", "company_name": "Notion",
                             "job_title": "Product Engineer",
                             "interview_date": "2026-08-14T09:00:00Z" } ],
  "trend": { "bucket": "week",
             "points": [ { "period_start": "2026-06-01", "applications": 0 } ] }
}
```

- Rates are **fractions**, and are `null` (never `0`) when the user has no
  applications — the UI should render `—` rather than `0%`.
- Rates count applications that **ever reached** a stage, so a job that went
  Applied → Interviewing → Rejected still counts toward the interview rate.
- `trend.bucket` is `week` for `30d`/`90d` and `month` for `1y`/`all`. Periods with no
  applications are returned as `0` rather than omitted.

---

## 5. `POST /resumes/analyze`

Multipart form: `file` (PDF, required) and `job_description` (optional text). Returns
`{"filename", "extracted_text_length", "ai_feedback"}`.

| Status | Cause |
| :--- | :--- |
| `400` | Not a `.pdf`, not a real PDF, empty file, corrupt or password protected, or no extractable text (scanned / image-only) |
| `413` | Larger than 5 MB |
| `429` | Upstream AI rate limit |
| `502` | Upstream AI error or empty completion |
| `504` | Upstream AI timeout |

The same `429` / `502` / `504` mapping applies to
`POST /jobs/{job_id}/generate-cover-letter`.

---

## 6. Known issues

Live in the code today, and each one will surprise a client author:

- **`POST /users/logout` is broken.** Its parameter is annotated `UserResponse`, so
  FastAPI treats it as a required JSON body and then calls `delete_cookie` on a Pydantic
  model. It cannot succeed. Use `POST /logout`.
- **`POST /users/login` duplicates `POST /login`** but does **not** set the auth cookie —
  it only returns the token in the body, so cookie auth silently does not engage.
  Use `POST /login`.
- **`GET /users/` exposes every registered user's email** to any authenticated caller,
  and is unpaginated.

---

## 7. Interactive Documentation

For detailed request schemas, payload validation rules, parameter data types, and live
endpoint testing, refer to the auto-generated Swagger UI at `/docs` (or ReDoc at
`/redoc`) when your FastAPI backend server is running. The raw OpenAPI document is at
`/openapi.json`.
