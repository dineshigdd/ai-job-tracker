# ATS Matching Score — System Design

**User story:** As a Job Seeker, I want to see how well my resume matches each job description, so that I can prioritize applications where I have the strongest fit.

---

## 0. Review findings (v1.0 → v1.1)

The v1.0 algorithm in §7.1 was transcribed verbatim and executed against the document's
own tests and worked example. It does not behave as the document claims.

**Three of the document's own six unit tests fail:**

```
PASS  test_perfect_match       score= 95  (hard=100 soft=100 exp=100 kw=58)  expected >= 90
FAIL  test_no_match            score= 40  (hard=  0 soft=100 exp=100 kw= 0)  expected <= 10
FAIL  test_partial_match       score= 75  (hard= 60 soft=100 exp=100 kw=58)  expected 40-60
FAIL  test_experience_match    score= 91  (hard=100 soft=100 exp= 85 kw=41)  expected exp >= 90
PASS  test_special_characters  score= 92  (hard=100 soft=100 exp=100 kw=26)  expected >= 80
PASS  test_empty_inputs        score= 90  (hard=100 soft=100 exp=100 kw= 0)  expected 0-100
```

Five defects, each verified by execution:

**D1 — Jaccard similarity penalises the better candidate.** Jaccard divides by the
*union*, so every skill a candidate has that the job did not ask for lowers their score:

```
job needs: python, django, postgresql
candidate A (exactly those 3)   -> hard=100.0  FINAL=97
candidate B (those 3 + 9 more)  -> hard= 33.3  FINAL=59
```

B knows everything A knows and more, and scores **38 points lower**. This is the single
most important fix: the metric must be *coverage of the job's requirements*, not
set overlap. See §3.2.

**D2 — Substring matching invents skills that were never mentioned.**
`skill in text_lower` matches inside other words:

```
'I work with Django every day'            -> detects ['django', 'go']
'Experienced JavaScript developer'        -> detects ['java', 'javascript']
'Knowledge of employment laws'            -> detects ['aws']
'Our culture is expressive and reactive'  -> detects ['express', 'react']
```

A JavaScript developer is credited with Java; an HR policy document is credited with
AWS. Needs word-boundary matching (§3.2).

**D3 — Empty and nonsense inputs score as "Excellent match".** `_jaccard_similarity`
returns `1.0` when the union is empty, and `_calculate_experience_score` returns `100.0`
when either side is unparseable. Both defaults award full marks for *absence of data*:

```
empty JD, empty resume   -> FINAL= 90  'Excellent match'
totally unrelated pair   -> FINAL= 40  'Moderate'
```

**D4 — The "0-19 Poor match" band is unreachable.** Because soft skills and experience
default to 100, they contribute a fixed **40-point floor**. A deliberately terrible
pairing scores 40. Four of the six bands in §3.3 can never occur.

**D5 — Years-of-experience extraction takes the first regex match, not the largest:**

```
'3 years at Acme, then 8 years at Globex'                 -> extracts 3.0
'Minimum 2 years required, 10 years preferred'            -> extracts 2.0
'401k vests after 2 years. Seeking 10+ years experience.' -> extracts 2.0
```

**Blocker — the system has nowhere to store a resume.** §2.2 lists "Resume Management -
Uses parsed resume text", §8.3 shows `PUT /resume/{resume_id}`, and the test fixture in
§10.3 imports `Resume` from `app.models`. **None of these exist.**
[`POST /resumes/analyze`](../backend/app/routers/resumes.py) parses an uploaded PDF and
throws the text away. Until a `resumes` table exists, every scoring call must carry the
full resume text in the request body, `resume_version` cannot be computed, and §8.3's
recalculation-on-resume-update cannot be built. See §6.3.

Sections 3, 4.2, 5, 9, 10, 13 and Appendix A have been revised accordingly.

---

## 1. Objective & Purpose

The ATS (Applicant Tracking System) Matching Score feature calculates a numerical score (0-100) representing how well a user's resume aligns with a specific job description. This helps users:

- **Prioritize applications** - Focus on jobs where they have the highest match scores
- **Identify gaps** - Understand which skills or keywords are missing from their resume
- **Improve applications** - Tailor resumes to specific job descriptions before applying
- **Track improvements** - See how resume updates affect match scores over time

The score is calculated using a weighted algorithm:
- **Hard skills match** (50% weight) - Technical skills, tools, technologies
- **Soft skills match** (20% weight) - Communication, leadership, teamwork
- **Experience level match** (20% weight) - Years of experience, seniority
- **Keyword density** (10% weight) - Frequency of relevant terms

---

## 2. Feature Overview

### 2.1 Core Functionality

| Feature | Description | API Endpoint |
| :--- | :--- | :--- |
| Calculate Match Score | Compute match score for a job application | `POST /jobs/{job_id}/match-score` |
| Get Match Score | Retrieve stored match score for a job | `GET /jobs/{job_id}/match-score` |
| Bulk Calculate | Calculate scores for multiple jobs | `POST /jobs/match-scores` |
| Score Breakdown | Get detailed breakdown of components | `GET /jobs/{job_id}/match-score/breakdown` |
| Score History | Track score changes over time | `GET /jobs/{job_id}/match-score/history` |

### 2.2 Integration Points

- **Resume Management** - Uses parsed resume text
- **Job Application Pipeline** - Stores score with each job record
- **Dashboard Statistics** - Aggregates average match scores
- **AI Cover Letter Generator** - Uses score for personalized suggestions
- **Search & Filter** - Allows filtering jobs by score range

---

## 3. Scoring Algorithm

### 3.1 Weighted Scoring Model

```
MATCH_SCORE = (hard_skills_score * 0.50) + (soft_skills_score * 0.20) + 
              (experience_score * 0.20) + (keyword_density_score * 0.10)
```

Each component produces a score from 0-100.

**Weights must be renormalised when a component is unavailable** — see §3.4.

### 3.2 Component Details

**Hard Skills Match (50%) — use coverage, not Jaccard**

```
hard_skills_score = |resume_skills ∩ job_skills| / |job_skills| * 100
```

The denominator is the **job's** requirements, not the union. This answers the question
the user is actually asking — "how much of what they want do I have?" — and does not
punish breadth (D1). A candidate with every required skill scores 100 whether they list
three technologies or thirty.

- If `job_skills` is empty, the component is **unavailable**, not 100 (§3.4).
- Extraction must use **word-boundary matching**, not substring containment (D2):

  ```python
  pattern = r'(?<![a-z0-9+#.])' + re.escape(skill) + r'(?![a-z0-9+#.])'
  ```

  A plain `\b` is not enough: `\b` after `c++` or `c#` sits between two non-word
  characters and never matches. The lookarounds above handle `c++`, `c#`,
  `scikit-learn` and `node.js` correctly.
- The taxonomy must include the multi-word terms the scorer claims to detect. Appendix A
  reports `REST APIs` and `GraphQL` as missing skills, but neither is in `HARD_SKILLS`,
  so neither can ever be detected. Match longest-first so `spring boot` is not consumed
  by `spring`, and `machine learning` not by a bare `learning`.

**Soft Skills Match (20%)**

Same coverage formula. Note that soft skills are the weakest signal here: job
descriptions list them as boilerplate ("excellent communication skills") and resumes
rarely state them explicitly. **Consider dropping this component to 10% and moving the
weight to hard skills**, or removing it in v1 — a 20% weight on a near-random signal
adds noise to the headline number.

**Experience Level Match (20%) — asymmetric**

```
if user_years >= required_years:  score = 100
else:                             score = max(0, 100 - (required - user) * 15)
```

Exceeding the requirement is a *match*, not a mismatch. The v1.0 symmetric-difference
formula scores a 20-year veteran applying to a 5-year role at 25/100.

Extraction must take the **maximum** plausible figure, not the first (D5), and must
ignore matches that are not about work experience (`401k vests after 2 years`). If
either side yields nothing, the component is **unavailable** (§3.4).

**Keyword Density Match (10%)**

TF-IDF over a two-document corpus produces almost no useful IDF signal — a term in both
documents and a term in one differ by a factor of ~1.7, so this is effectively weighted
term overlap. Keep it at 10%, and describe it honestly as *term overlap* rather than
implying corpus-level term weighting. If a genuine IDF signal is wanted later, fit the
vectorizer over **all** of the user's job descriptions, not the pair.

### 3.3 Score Interpretation

| Score Range | Interpretation | Action |
| :--- | :--- | :--- |
| 85-100 | Excellent match | Apply immediately |
| 70-84 | Strong match | Apply with minor tweaks |
| 55-69 | Good match | Review and tailor resume |
| 40-54 | Moderate match | Consider other factors |
| 20-39 | Weak match | Significant revision needed |
| 0-19 | Poor match | Likely not a good fit |

These bands are only meaningful once §3.4 removes the 40-point floor (D4). **Re-verify
the band boundaries against real resumes after implementation** — six bands imply a
precision this algorithm does not have, and the boundaries are currently guesses.

### 3.4 Unavailable components (new)

The v1.0 defaults award full marks for missing data, which is what makes an empty
resume score 90 (D3). Replace them with an explicit unavailable state:

- A component is **unavailable** when its inputs cannot be evaluated: no recognised
  skills on the job side, or no parseable experience on either side.
- An unavailable component is **excluded from both the numerator and the weight sum**,
  and the remaining weights are renormalised:

  ```
  score = Σ(available_score × weight) / Σ(available_weight)
  ```

- If **no** component is available, return `null`, not `0` — the same
  no-data-is-not-a-zero rule used for the dashboard conversion rates.
- Surface it: the breakdown should report `"experience": {"available": false, "reason":
  "no experience statement found in job description"}` so the user understands why a
  section is missing rather than seeing an unexplained number.

**Guard rail:** an empty resume, an empty job description, or a pairing with no
overlapping skills must never produce a score above the "Weak match" band. Assert this
in the test suite (§10.1).

---

## 4. Data Flow

```
User Resume (Parsed Text) -> Job Description (Text) -> 
Match Score Calculation -> Score Store -> Job Record (Updated) -> Dashboard
```

### 4.1 Process Steps
1. User creates/updates job application OR manually requests score
2. Validate job description and resume text exist
3. Extract clean text from both documents
4. Use NLP to extract skills from both texts
5. Parse experience requirements and user experience
6. Run all four scoring components
7. Combine scores with weights
8. Save score and breakdown to database
9. Return score to user

### 4.2 Asynchronous Processing — not needed in v1

The algorithm is pure-Python set operations plus one TF-IDF fit over two short
documents. Measured, it completes in **single-digit milliseconds** — roughly three
orders of magnitude faster than the Groq call already made synchronously by
[`generate_cover_letter`](../backend/app/services/ai_service.py).

Returning `202 Accepted` and adding Celery, a broker and WebSocket notifications to
hide a 5 ms computation adds an entire operational tier — a second process to run, a
Redis instance to keep alive, task states to reconcile, and a UI that must poll or
subscribe — for no user-visible gain. **Compute synchronously and return `200` with the
score.**

Revisit only if the algorithm grows an expensive step (a transformer model, or an LLM
call as suggested in §12), or if bulk recalculation across hundreds of jobs becomes a
real workflow. FastAPI's built-in `BackgroundTasks` covers the middle ground without a
broker.

---

## 5. API Contract

### 5.1 Calculate Match Score

**`POST /jobs/{job_id}/match-score`**

Request:
```json
{
  "resume_text": "Full text of user's resume...",
  "force_recalculate": false
}
```

> **`resume_text` in the body is a workaround, not the design.** It exists only because
> nothing persists resumes (§0, §6.3). Once a `resumes` table lands, this becomes
> `{"resume_id": "uuid"}` and the server reads the text itself — which also lets the
> server compute `resume_version` and cache on it. Treat the body field as temporary and
> document it as such, so the migration is expected rather than a breaking surprise.

Response (**200 OK**, not 201 — this updates the existing job rather than creating a
resource at a new URL):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "match_score": 85,
  "breakdown": {
    "hard_skills": {
      "score": 90,
      "matched_skills": ["Python", "Django", "PostgreSQL"],
      "missing_skills": ["React", "AWS"]
    },
    "soft_skills": {
      "score": 80,
      "matched_skills": ["communication", "teamwork"],
      "missing_skills": ["leadership"]
    },
    "experience": {
      "score": 95,
      "user_experience": "8 years",
      "required_experience": "5+ years"
    },
    "keyword_density": 75
  },
  "calculated_at": "2026-08-14T10:30:00Z",
  "status": "completed",
  "suggestions": [
    "Add React experience to your resume",
    "Mention AWS cloud services"
  ]
}
```

### 5.2 Get Match Score

**`GET /jobs/{job_id}/match-score`**

Response (200 OK):
```json
{
  "job_id": "uuid",
  "match_score": 85,
  "breakdown": { ... },
  "calculated_at": "2026-08-14T10:30:00Z"
}
```

### 5.3 Bulk Calculate

**`POST /jobs/match-scores`**

Request:
```json
{
  "job_ids": ["uuid1", "uuid2", "uuid3"],
  "resume_text": "Full resume text...",
  "force_recalculate": false
}
```

Response (202 Accepted):
```json
{"task_id": "celery-task-uuid", "job_ids": [...], "status": "pending"}
```

### 5.4 Filter by Score Range

Extend existing **`GET /jobs/`** endpoint with:
- `min_score` (optional, 0-100) - Minimum match score
- `max_score` (optional, 0-100) - Maximum match score

### 5.5 Error Responses

| Error | Status | Response |
| :--- | :--- | :--- |
| Job not found | 404 | `{"detail": "Job not found"}` |
| No resume text | 400 | `{"detail": "Resume text is required"}` |
| Invalid job_id | 422 | Pydantic validation error |
| Calculation failed | 500 | `{"detail": "Score calculation failed"}` |

---

## 6. Database Schema Changes

### 6.1 Existing Column

The `jobs` table already has `match_score` column:
```python
# In models.py
match_score = Column(Integer, nullable=True)
```

### 6.2 New Tables Required

#### `match_score_history` (Audit Trail)

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | |
| `job_id` | UUID | FK jobs.id, NOT NULL | |
| `user_id` | UUID | FK users.id, NOT NULL | Denormalized for queries |
| `match_score` | Integer | NOT NULL, 0-100 | Final score |
| `hard_skills_score` | Integer | NOT NULL, 0-100 | Component score |
| `soft_skills_score` | Integer | NOT NULL, 0-100 | Component score |
| `experience_score` | Integer | NOT NULL, 0-100 | Component score |
| `keyword_density_score` | Integer | NOT NULL, 0-100 | Component score |
| `calculated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Timestamp |
| `resume_version` | String | NOT NULL | Resume hash/version |
| `algorithm_version` | String | NOT NULL, DEFAULT 'v1.0' | Algorithm version |

**Indexes:**
- `(job_id, calculated_at DESC)` - History for a job, newest first
- `(user_id, match_score)` - Query jobs by score range

#### `match_score_breakdown` (Detailed Results)

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | |
| `job_id` | UUID | FK jobs.id, NOT NULL, UNIQUE | One per job |
| `hard_skills_matched` | JSONB | NOT NULL | Array of matched skills |
| `hard_skills_missing` | JSONB | NOT NULL | Array of missing skills |
| `soft_skills_matched` | JSONB | NOT NULL | Array of matched skills |
| `soft_skills_missing` | JSONB | NOT NULL | Array of missing skills |
| `experience_details` | JSONB | NOT NULL | `{user: "8 years", required: "5+ years"}` |
| `keyword_similarity` | Float | NOT NULL, 0.0-1.0 | Cosine similarity |
| `suggestions` | JSONB | NOT NULL | Array of suggestions |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Timestamp |

**Index:** `(job_id)`

> `match_score_breakdown.job_id` is `UNIQUE`, so the breakdown is **replaced** on each
> recalculation while `match_score_history` accumulates. State that explicitly as an
> upsert, and add `user_id` here too — without it, every breakdown query needs a join to
> `jobs` purely to check ownership.

### 6.3 `resumes` — the missing prerequisite (new)

Neither new table above is the real blocker. **There is no resume storage at all.**
`POST /resumes/analyze` extracts text from an uploaded PDF, sends it to Groq and
discards it; there is no `Resume` model, table, or endpoint. That breaks four things
this document assumes:

| Assumption | Where | Status |
| :--- | :--- | :--- |
| "Uses parsed resume text" | §2.2 | No stored text to use |
| `resume_version` NOT NULL | §6.2 | Nothing to version |
| `PUT /resume/{resume_id}` triggers recalculation | §8.3 | Endpoint does not exist |
| `from app.models import Resume` | §10.3 fixture | Import fails |

Minimum viable table:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | |
| `user_id` | UUID | FK users.id ON DELETE CASCADE, NOT NULL | |
| `filename` | VARCHAR(255) | NOT NULL | Original upload name |
| `extracted_text` | TEXT | NOT NULL | Output of the existing PDF parser |
| `content_hash` | VARCHAR(64) | NOT NULL | SHA-256 of `extracted_text`; this **is** `resume_version` |
| `is_active` | Boolean | NOT NULL DEFAULT true | The resume used for scoring by default |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

Index `(user_id, created_at DESC)`. Deriving `resume_version` from a content hash means
re-uploading an unchanged resume produces the same version, so cached scores stay valid
— which is what makes the caching in §9.1 actually correct.

This is a prerequisite for steps 8 and 9 of the build order, and it also delivers
"Resume Versioning", listed as a Priority 1 future enhancement in §12.

---

## 7. Implementation Details

### 7.1 Backend Implementation

#### New Router: `routers/match_score.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from app.models import Job, User
from app.services.match_score import calculate_match_score
from app.database import get_db
from app.auth import get_current_user
from app.schemas import MatchScoreRequest, MatchScoreResponse

router = APIRouter(prefix="/jobs", tags=["match-score"])

@router.post("/{job_id}/match-score", response_model=MatchScoreResponse)
def calculate_job_match_score(
    job_id: UUID,
    request: MatchScoreRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify job exists and belongs to user
    job = db.query(Job).filter(
        Job.id == job_id, Job.user_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or does not belong to you")
    
    if not request.resume_text:
        raise HTTPException(status_code=400, detail="Resume text is required")
    
    # Calculate score
    score_result = calculate_match_score(
        job_description=job.job_description or "",
        resume_text=request.resume_text,
        job_title=job.job_title
    )
    
    # Store results
    job.match_score = score_result.final_score
    db.commit()
    
    return MatchScoreResponse(**score_result.dict())

@router.get("/{job_id}/match-score", response_model=MatchScoreResponse)
def get_job_match_score(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(
        Job.id == job_id, Job.user_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or does not belong to you")
    if job.match_score is None:
        raise HTTPException(status_code=404, detail="Match score not calculated yet")
    return MatchScoreResponse(...)
```

#### Match Score Service: `services/match_score.py`

```python
from dataclasses import dataclass
from typing import List, Set
import re

# Pre-defined skill taxonomies (expandable)
HARD_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "django", "flask", "fastapi", "spring", "spring boot", "express",
    "react", "angular", "vue", "node", "postgresql", "mysql", "mongodb",
    "redis", "aws", "gcp", "azure", "docker", "kubernetes", "git", "linux",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn"
}

SOFT_SKILLS = {
    "communication", "leadership", "teamwork", "collaboration",
    "problem solving", "critical thinking", "adaptability", "creativity",
    "time management", "project management", "stakeholder management",
    "mentoring", "coaching", "negotiation", "conflict resolution",
    "presentation", "writing"
}

@dataclass
class MatchScoreResult:
    final_score: int
    hard_skills_score: float
    soft_skills_score: float
    experience_score: float
    keyword_density: float
    matched_hard_skills: List[str]
    missing_hard_skills: List[str]
    matched_soft_skills: List[str]
    missing_soft_skills: List[str]
    user_experience: str
    required_experience: str
    suggestions: List[str]

class MatchScoreCalculator:
    def calculate(self, job_description: str, resume_text: str, job_title: str = "") -> MatchScoreResult:
        # Extract skills
        job_hard, job_soft = self._extract_skills(job_description + " " + job_title)
        resume_hard, resume_soft = self._extract_skills(resume_text)
        
        # Calculate component scores
        hard_score = self._jaccard_similarity(resume_hard, job_hard) * 100
        soft_score = self._jaccard_similarity(resume_soft, job_soft) * 100
        exp_score, user_exp, req_exp = self._calculate_experience_score(job_description, resume_text)
        keyword_score = self._calculate_keyword_similarity(job_description, resume_text) * 100
        
        # Weighted sum
        final_score = int(
            hard_score * 0.50 + soft_score * 0.20 + 
            exp_score * 0.20 + keyword_score * 0.10
        )
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            job_hard - resume_hard, job_soft - resume_soft, user_exp, req_exp
        )
        
        return MatchScoreResult(
            final_score=final_score,
            hard_skills_score=hard_score,
            soft_skills_score=soft_score,
            experience_score=exp_score,
            keyword_density=keyword_score,
            matched_hard_skills=list(resume_hard & job_hard),
            missing_hard_skills=list(job_hard - resume_hard),
            matched_soft_skills=list(resume_soft & job_soft),
            missing_soft_skills=list(job_soft - resume_soft),
            user_experience=user_exp,
            required_experience=req_exp,
            suggestions=suggestions
        )
    
    def _extract_skills(self, text: str) -> tuple[Set[str], Set[str]]:
        """Extract hard and soft skills from text."""
        text_lower = text.lower()
        hard = {skill for skill in HARD_SKILLS if skill in text_lower}
        soft = {skill for skill in SOFT_SKILLS if skill in text_lower}
        return hard, soft
    
    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 1.0
    
    def _calculate_experience_score(
        self, job_desc: str, resume: str
    ) -> tuple[float, str, str]:
        """Extract and compare experience levels."""
        req_years = self._extract_years(job_desc)
        user_years = self._extract_years(resume)
        
        req_exp = f"{req_years} years" if req_years else "Not specified"
        user_exp = f"{user_years} years" if user_years else "Not specified"
        
        if req_years is None or user_years is None:
            return 100.0, user_exp, req_exp
        
        # Normalize to 0-20 scale
        user_norm = min(user_years / 20, 1.0)
        required_norm = min(req_years / 20, 1.0)
        
        # Score based on difference
        diff = abs(user_norm - required_norm)
        score = max(0, 100 - (diff * 100))
        
        return score, user_exp, req_exp
    
    def _extract_years(self, text: str) -> float | None:
        """Extract years of experience from text."""
        text_lower = text.lower()
        
        # Try to find numeric years
        year_matches = re.findall(r'(\d+)\+?\s*years?', text_lower)
        if year_matches:
            return float(year_matches[0])
        
        # Check for seniority keywords
        if any(kw in text_lower for kw in ['senior', 'principal', 'lead', 'architect']):
            return 6.0
        if any(kw in text_lower for kw in ['mid-level', 'mid level']):
            return 3.5
        if any(kw in text_lower for kw in ['junior', 'entry', 'graduate', 'intern']):
            return 1.0
        
        return None
    
    def _calculate_keyword_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between TF-IDF vectors."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Clean and tokenize
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        vectorizer = TfidfVectorizer(tokenizer=lambda x: x, lowercase=False)
        tfidf_matrix = vectorizer.fit_transform([tokens1, tokens2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        
        return float(similarity[0][0])
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text, removing stopwords and punctuation."""
        import re
        from nltk.corpus import stopwords
        
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        stop_words = set(stopwords.words('english'))
        return [t for t in tokens if t and t not in stop_words and len(t) > 2]
    
    def _generate_suggestions(
        self,
        missing_hard: Set[str],
        missing_soft: Set[str],
        user_exp: str,
        req_exp: str
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if missing_hard:
            suggestions.append(f"Add experience with: {', '.join(list(missing_hard)[:3])}")
        if missing_soft:
            suggestions.append(f"Highlight soft skills: {', '.join(list(missing_soft)[:3])}")
        
        # Experience suggestions
        if req_exp and user_exp:
            try:
                req_years = float(req_exp.split()[0])
                user_years = float(user_exp.split()[0])
                if user_years < req_years:
                    suggestions.append(
                        f"Gain {req_years - user_years:.0f} more years of experience"
                    )
            except (ValueError, IndexError):
                pass
        
        return suggestions[:5]

# Singleton instance
match_score_calculator = MatchScoreCalculator()

def calculate_match_score(job_description: str, resume_text: str, job_title: str = "") -> MatchScoreResult:
    return match_score_calculator.calculate(job_description, resume_text, job_title)
```

### 7.2 Frontend Implementation

#### Score Display Component

```tsx
// components/MatchScoreBadge.tsx
import React from 'react';
import { Badge } from './ui/badge';

interface MatchScoreBadgeProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
}

export function MatchScoreBadge({ score, size = 'md' }: MatchScoreBadgeProps) {
  if (score === null) {
    return <Badge variant="secondary">Not calculated</Badge>;
  }

  const getVariant = (score: number) => {
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'strong';
    if (score >= 55) return 'good';
    if (score >= 40) return 'moderate';
    if (score >= 20) return 'weak';
    return 'poor';
  };

  const styles = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-2.5 py-1.5 text-sm',
    lg: 'px-3 py-2 text-base',
  };

  return (
    <Badge variant={getVariant(score)} className={`${styles[size]} font-medium`}>
      {score}
    </Badge>
  );
}
```

#### Score Breakdown Modal

```tsx
// components/MatchScoreBreakdown.tsx
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Progress } from './ui/progress';

// NOTE: field names must match the API contract in §5.1, which returns
// `matched_skills` / `missing_skills`. The v1.0 draft declared `matched` / `missing`
// here, so every skill list would have rendered as `undefined`.
interface MatchScoreBreakdownProps {
  isOpen: boolean;
  onClose: () => void;
  data: {
    match_score: number;
    breakdown: {
      hard_skills: { score: number; matched_skills: string[]; missing_skills: string[] };
      soft_skills: { score: number; matched_skills: string[]; missing_skills: string[] };
      experience: { score: number; user_experience: string; required_experience: string };
      keyword_density: number;   // already 0-100, do NOT multiply again
    };
    suggestions: string[];
  };
}

export function MatchScoreBreakdown({ isOpen, onClose, data }: MatchScoreBreakdownProps) {
  const components = [
    { name: 'Hard Skills', score: data.breakdown.hard_skills.score, weight: 50, color: 'bg-blue-500' },
    { name: 'Soft Skills', score: data.breakdown.soft_skills.score, weight: 20, color: 'bg-green-500' },
    { name: 'Experience', score: data.breakdown.experience.score, weight: 20, color: 'bg-purple-500' },
    { name: 'Keyword Density', score: data.breakdown.keyword_density, weight: 10, color: 'bg-orange-500' },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Match Score Breakdown</DialogTitle>
        </DialogHeader>

        <div className="text-center mb-6">
          <div className="text-6xl font-bold text-primary mb-2">{data.match_score}</div>
          <div className="text-muted-foreground">/ 100</div>
        </div>

        <div className="space-y-4 mb-6">
          {components.map((component) => (
            <div key={component.name}>
              <div className="flex justify-between mb-1">
                <span className="font-medium">{component.name} ({component.weight}%)</span>
                <span className="font-bold">{component.score.toFixed(0)}</span>
              </div>
              <Progress value={component.score} className={`h-2 ${component.color}`} />
            </div>
          ))}
        </div>

        {(data.breakdown.hard_skills.missing_skills.length > 0 ||
          data.breakdown.soft_skills.missing_skills.length > 0) && (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Missing Skills</h3>
            <div className="grid grid-cols-2 gap-2">
              {data.breakdown.hard_skills.missing_skills.map(skill => (
                <div key={skill} className="bg-red-50 text-red-700 px-2 py-1 rounded text-sm">
                  {skill}
                </div>
              ))}
              {data.breakdown.soft_skills.missing_skills.map(skill => (
                <div key={skill} className="bg-amber-50 text-amber-700 px-2 py-1 rounded text-sm">
                  {skill}
                </div>
              ))}
            </div>
          </div>
        )}

        {data.suggestions.length > 0 && (
          <div>
            <h3 className="font-semibold mb-2">Suggestions for Improvement</h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {data.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

#### Score Range Filter

```tsx
// components/ScoreFilter.tsx
import React from 'react';
import { Slider } from './ui/slider';

interface ScoreFilterProps {
  minScore: number | undefined;
  maxScore: number | undefined;
  onChange: (min: number | undefined, max: number | undefined) => void;
}

export function ScoreFilter({ minScore, maxScore, onChange }: ScoreFilterProps) {
  const [range, setRange] = React.useState<[number, number]>([
    minScore ?? 0, 
    maxScore ?? 100
  ]);

  const handleChange = (value: number[]) => {
    setRange([value[0], value[1]]);
    onChange(
      value[0] === 0 ? undefined : value[0],
      value[1] === 100 ? undefined : value[1]
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>0</span>
        <span>25</span>
        <span>50</span>
        <span>75</span>
        <span>100</span>
      </div>
      <Slider
        value={range}
        onValueChange={handleChange}
        max={100}
        min={0}
        step={1}
        className="mb-2"
      />
      <div className="flex justify-between text-sm">
        <span>Min: {range[0] === 0 ? 'Any' : range[0]}</span>
        <span>Max: {range[1] === 100 ? 'Any' : range[1]}</span>
      </div>
    </div>
  );
}
```

---

## 8. Integration with Existing Features

### 8.1 Search & Filter Integration

Extend `GET /jobs/` endpoint in `routers/jobs.py`:

```python
@router.get("/", response_model=JobListResponse)
def get_jobs(
    # ... existing parameters ...
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    # ...
):
    query = db.query(Job).filter(Job.user_id == current_user.id)
    
    # ... existing filters ...
    
    if min_score is not None:
        query = query.filter(Job.match_score >= min_score)
    if max_score is not None:
        query = query.filter(Job.match_score <= max_score)
    
    # ... rest of function
```

### 8.2 Dashboard Integration

Add to dashboard stats endpoint:

```json
{
  "average_match_score": 78.5,
  "score_distribution": {
    "excellent": 5,
    "strong": 7,
    "good": 3,
    "moderate": 1,
    "weak": 0,
    "poor": 0
  },
  "highest_scoring_jobs": [
    {"job_id": "...", "company": "Google", "title": "Senior Engineer", "score": 95}
  ]
}
```

### 8.3 Resume Update Workflow

In resume update endpoint:

```python
@router.put("/resume/{resume_id}")
def update_resume(
    resume_id: UUID,
    resume_data: ResumeUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ... update resume ...
    
    # Queue recalculation for all user's jobs
    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
    for job in jobs:
        background_tasks.add_task(
            recalculate_match_score_task,
            job_id=str(job.id),
            user_id=str(current_user.id),
            resume_text=new_resume_text
        )
    
    return {"message": "Resume updated, recalculating match scores..."}
```

---

## 9. Performance & Error Handling

### 9.1 Caching Strategy — not needed in v1

**Rationale check:** the premise "NLP processing is expensive" does not hold. The
algorithm is set intersection plus one TF-IDF fit over two documents — milliseconds.
Standing up Redis to cache a 5 ms computation costs more than it saves.

The database *is* the cache: `jobs.match_score` and `match_score_breakdown` already
persist the result, and `force_recalculate=false` should simply return the stored row.
Store `resume_version` and `algorithm_version` alongside it and recompute only when
either changes.

If Redis is added later, key on content rather than time:

```
match_score:{algorithm_version}:{sha256(resume_text)}:{sha256(job_description)}
```

A content-addressed key needs no TTL and no invalidation logic — changing the resume or
the job description changes the key. The v1.0 design's "7 days, invalidate on update"
requires the invalidation to be wired to every write path, and a single missed path
serves a stale score for a week.

### 9.2 Background Processing

Use Celery for async score calculation:

```python
# tasks.py
from celery import Celery
from app.database import SessionLocal
from app.models import Job
from app.services.match_score import calculate_match_score

celery = Celery(__name__, broker='redis://localhost:6379/0')

@celery.task(bind=True, max_retries=3)
def calculate_match_score_task(self, job_id: str, user_id: str, resume_text: str):
    try:
        db = SessionLocal()
        job = db.query(Job).filter(
            Job.id == job_id, 
            Job.user_id == user_id
        ).first()
        
        if job and job.job_description:
            score_result = calculate_match_score(
                job.job_description, 
                resume_text,
                job.job_title
            )
            job.match_score = score_result.final_score
            db.commit()
        
        db.close()
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

### 9.3 Error Handling

| Scenario | Status Code | Response |
| :--- | :--- | :--- |
| Job not found | 404 | `{"detail": "Job not found or does not belong to you"}` |
| Empty resume text | 400 | `{"detail": "Resume text is required"}` |
| Invalid job_id format | 422 | Pydantic validation error |
| Calculation failed | 500 | `{"detail": "Score calculation failed"}` |
| Unauthorized | 401 | `{"detail": "Not authenticated"}` |

> **Do not return `"error": str(exc)` to the client.** That leaks file paths, library
> internals and sometimes input fragments. Log the real exception with
> `logger.exception` and return the generic message — the same pattern already applied
> in [`resumes.py`](../backend/app/routers/resumes.py).

Also cap `resume_text` length (`max_length` on the Pydantic field) so a multi-megabyte
body cannot be posted; the PDF path already caps uploads at 5 MB, and this endpoint
would otherwise be the unguarded way in.

### 9.4 Rate Limiting — deferred

The v1.0 snippet has two problems if adopted as written:

- `key_func=get_remote_address` limits **by IP**. Every user behind one corporate NAT
  or mobile carrier shares a bucket, so one heavy user locks out the rest. Key on
  `current_user.id` instead.
- `slowapi`'s `@limiter.limit` decorator requires a `request: Request` parameter in the
  endpoint signature and raises at runtime without one. The examples omit it.

More fundamentally, rate limiting protects a scarce resource. Scoring is local CPU with
no per-call cost, and every route is already authenticated and user-scoped. **Defer
this**, and apply it first to the endpoints that spend money — the Groq-backed
[cover letter](../backend/app/routers/jobs.py) and
[resume analysis](../backend/app/routers/resumes.py) routes, where the free-tier quota
is the actual scarce resource.

---

## 10. Testing Strategy

### 10.1 Unit Tests

Test the scoring algorithm in isolation. The v1.0 suite below was **verified to fail 3
of 6 cases** against its own algorithm (§0), and its one always-true assertion
(`0 <= score <= 100`) hid the worst defect. Replacement suite:

```python
# tests/test_match_score.py
import pytest
from app.services.match_score import MatchScoreCalculator

@pytest.fixture
def calc():
    return MatchScoreCalculator()


class TestScoring:
    def test_perfect_match(self, calc):
        r = calc.calculate("Looking for Python Django developer with PostgreSQL",
                           "Python Django PostgreSQL, 5 years of experience")
        assert r.final_score >= 90

    def test_no_overlap_scores_low(self, calc):
        # v1.0 scored this 40 because soft skills and experience defaulted to 100
        r = calc.calculate("Python Django PostgreSQL", "Java Spring Boot")
        assert r.final_score <= 20, "no shared skills must not land in a 'Moderate' band"

    def test_partial_match(self, calc):
        # resume covers 2 of the job's 4 required skills -> hard component ~50
        r = calc.calculate("Python Django PostgreSQL AWS", "Python Django")
        assert 40 <= r.final_score <= 70
        assert 45 <= r.hard_skills_score <= 55


class TestCoverageNotJaccard:
    """D1: extra skills must never reduce the score."""

    def test_breadth_is_not_penalised(self, calc):
        jd = "We need Python, Django and PostgreSQL"
        narrow = calc.calculate(jd, "Python Django PostgreSQL")
        broad = calc.calculate(jd, "Python Django PostgreSQL AWS Docker React Redis Go")
        assert broad.hard_skills_score == narrow.hard_skills_score == 100
        assert broad.final_score >= narrow.final_score


class TestSkillExtraction:
    """D2: word-boundary matching, no substring false positives."""

    @pytest.mark.parametrize("text,forbidden", [
        ("I work with Django every day", "go"),
        ("Experienced JavaScript developer", "java"),
        ("Knowledge of employment laws", "aws"),
        ("Our culture is expressive and reactive", "react"),
    ])
    def test_no_substring_false_positives(self, calc, text, forbidden):
        hard, _ = calc._extract_skills(text)
        assert forbidden not in hard

    def test_still_finds_real_skills(self, calc):
        hard, _ = calc._extract_skills("Python, C++, C#, scikit-learn and Spring Boot")
        assert {"python", "c++", "c#", "scikit-learn", "spring boot"} <= hard

    def test_longest_match_wins(self, calc):
        hard, _ = calc._extract_skills("Spring Boot microservices")
        assert "spring boot" in hard


class TestUnavailableComponents:
    """D3/D4: absence of data must never score as a match."""

    def test_empty_inputs_return_null(self, calc):
        assert calc.calculate("", "").final_score is None

    def test_empty_job_description(self, calc):
        r = calc.calculate("", "Senior Python developer, 10 years")
        assert r.final_score is None or r.final_score < 40

    def test_unrelated_pair_is_weak(self, calc):
        r = calc.calculate("Looking for a barista with latte art skills",
                           "Senior Python developer, 10 years, AWS and Kubernetes")
        assert r.final_score < 40, "v1.0 scored this 40 via the soft/experience floor"

    def test_unavailable_component_is_flagged(self, calc):
        r = calc.calculate("Python developer", "Python developer")
        assert r.experience.available is False
        assert r.experience.reason


class TestExperience:
    """D5: take the maximum, and never penalise exceeding the requirement."""

    def test_meeting_requirement(self, calc):
        r = calc.calculate("Requires 5+ years of Python", "8 years of Python")
        assert r.experience_score >= 90

    def test_exceeding_is_not_penalised(self, calc):
        r = calc.calculate("Requires 5+ years of Python", "20 years of Python")
        assert r.experience_score == 100, "over-qualification is a match, not a gap"

    def test_takes_maximum_not_first(self, calc):
        assert calc._extract_years("3 years at Acme, then 8 years at Globex") == 8.0

    def test_ignores_non_experience_years(self, calc):
        assert calc._extract_years("401k vests after 2 years. Seeking 10+ years.") == 10.0


class TestDeterminism:
    def test_repeated_calls_are_identical(self, calc):
        jd, cv = "Python Django AWS Docker", "Python Django Redis"
        first = calc.calculate(jd, cv)
        assert all(calc.calculate(jd, cv) == first for _ in range(5)), \
            "suggestions built from unordered sets vary between runs; sort them"
```

Two of these encode fixes the implementation must make to pass: `_extract_skills` needs
word-boundary matching, and `_generate_suggestions` must sort its sets — `list(missing_hard)[:3]`
over a `set` returns an arbitrary three skills that change between interpreter runs, so
the same inputs produce different advice.

### 10.2 Integration Tests

Test API endpoints with database:

```python
# tests/test_match_score_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestMatchScoreEndpoints:
    def test_calculate_match_score(self, client: TestClient, test_job, test_resume):
        response = client.post(
            f"/jobs/{test_job.id}/match-score",
            json={"resume_text": test_resume.text}
        )
        assert response.status_code == 201
        assert "match_score" in response.json()
        assert 0 <= response.json()["match_score"] <= 100
    
    def test_get_match_score(self, client: TestClient, test_job_with_score):
        response = client.get(f"/jobs/{test_job_with_score.id}/match-score")
        assert response.status_code == 200
        assert response.json()["match_score"] == test_job_with_score.match_score
    
    def test_get_match_score_not_found(self, client: TestClient):
        response = client.get("/jobs/00000000-0000-0000-0000-000000000000/match-score")
        assert response.status_code == 404
    
    def test_calculate_score_empty_resume(self, client: TestClient, test_job):
        response = client.post(
            f"/jobs/{test_job.id}/match-score",
            json={"resume_text": ""}
        )
        assert response.status_code == 400
    
    def test_filter_by_score_range(self, client: TestClient, create_test_jobs):
        # Create jobs with various scores
        response = client.get("/jobs/?min_score=70")
        assert response.status_code == 200
        for job in response.json()["items"]:
            assert job["match_score"] >= 70 or job["match_score"] is None
    
    def test_user_can_only_see_own_scores(self, client: TestClient, db_session):
        # Create job for another user
        # Verify current user cannot access it
        response = client.get("/jobs/other-user-job-id/match-score")
        assert response.status_code == 404
```

### 10.3 Test Fixtures

```python
# conftest.py
import pytest
from app.models import Job, User, Resume
from uuid import uuid4

@pytest.fixture
def test_user(db_session):
    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_job(db_session, test_user):
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Test Company",
        job_title="Senior Python Developer",
        job_description="Looking for Senior Python developer with Django experience",
        status="Applied"
    )
    db_session.add(job)
    db_session.commit()
    return job

@pytest.fixture
def test_resume():
    class Resume:
        text = "8 years of Python Django development. Experience with PostgreSQL and AWS."
    return Resume()

@pytest.fixture
def test_job_with_score(db_session, test_job):
    test_job.match_score = 85
    db_session.commit()
    return test_job

@pytest.fixture
def create_test_jobs(db_session, test_user):
    """Create multiple test jobs with different scores."""
    jobs_data = [
        {"company": "Google", "title": "Senior Backend", "desc": "Python Django", "score": 90},
        {"company": "Microsoft", "title": "Frontend Engineer", "desc": "React TypeScript", "score": 75},
        {"company": "Amazon", "title": "DevOps", "desc": "AWS Kubernetes", "score": 60},
        {"company": "Netflix", "title": "Data Engineer", "desc": "Spark Hadoop", "score": null},
    ]
    
    jobs = []
    for data in jobs_data:
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name=data["company"],
            job_title=data["title"],
            job_description=data["desc"],
            status="Applied",
            match_score=data["score"]
        )
        db_session.add(job)
        jobs.append(job)
    
    db_session.commit()
    return jobs
```

---

## 11. Acceptance Criteria

### 11.1 Functional Requirements

- [ ] Users can request match score calculation for any job application
- [ ] Match scores are calculated using the weighted algorithm (50/20/20/10)
- [ ] Scores are stored in database and persist across sessions
- [ ] Users can view detailed score breakdown with component details
- [ ] Users can filter jobs by match score range
- [ ] Match scores are recalculated when resume is updated
- [ ] Users receive actionable suggestions for improving their match score
- [ ] Score calculation is multi-tenant safe (users only see their own scores)

### 11.2 Non-Functional Requirements

- [ ] Match score calculation completes within 2 seconds for single jobs
- [ ] Bulk operations process 10 jobs within 10 seconds
- [ ] API responses include proper error messages
- [ ] Score calculation fails gracefully without breaking job creation
- [ ] Caching reduces repeated calculations for unchanged data
- [ ] Rate limiting prevents abuse

### 11.3 Edge Cases

- [ ] Empty job description - Calculate score using only job title
- [ ] Empty resume - Return 400 error
- [ ] Special characters in text - Handled correctly (escaped)
- [ ] Very long text - Processed without timeout
- [ ] Concurrent requests - No race conditions
- [ ] Invalid job ID - Return 404
- [ ] Unauthorized access - Return 401/403
- [ ] Job description with only seniority keywords - Handle gracefully

---

## 12. Future Enhancements

### Priority 1 (Next Sprint)
1. **Resume Versioning** - Track multiple resume versions per user
2. **Job Description Updates** - Automatically trigger recalculation when job description changes
3. **Score Comparison** - Allow users to compare scores across different resume versions
4. **Industry-Specific Models** - Custom weights for different industries (tech, finance, healthcare)

### Priority 2
1. **Advanced NLP** - Use transformer models (BERT, etc.) for better skill extraction
2. **Custom Skill Taxonomy** - Allow users to define their own skill categories
3. **Score Trends** - Show how scores change over time with visualizations
4. **Team Comparisons** - Compare scores with other users (opt-in, anonymous)

### Priority 3
1. **Real-time Scoring** - Calculate scores as user types job description
2. **AI-Powered Suggestions** - Use LLMs to generate better improvement suggestions
3. **Integration with External ATS** - Import job descriptions directly from ATS platforms
4. **Batch Upload** - Upload multiple job descriptions at once (CSV/Excel)
5. **Custom Weighting** - Allow users to adjust the scoring weights

---

## 13. Build Order

Reordered so that a usable, correct scorer ships first and the optional infrastructure
is dropped. **Write the tests before the algorithm** — §0 exists precisely because the
v1.0 tests were written to fit an algorithm rather than to define its behaviour.

### Phase 1 — a correct, shippable scorer

| Step | Task | Dependency |
| :--- | :--- | :--- |
| 1 | Test suite from §10.1, all failing | None |
| 2 | Skill taxonomy + word-boundary extraction (D2) | Step 1 |
| 3 | Coverage scoring, asymmetric experience, unavailable components (D1/D3/D4/D5) | Step 2 |
| 4 | `match_score_breakdown` table + `POST`/`GET /jobs/{job_id}/match-score` | Step 3 |
| 5 | Score badge + breakdown modal UI | Step 4 |
| 6 | `min_score` / `max_score` on `GET /jobs/` | Step 4 |

At the end of Phase 1 the feature is complete for a single resume pasted per request.

### Phase 2 — resume persistence (unblocks the rest)

| Step | Task | Dependency |
| :--- | :--- | :--- |
| 7 | `resumes` table + persist text from `POST /resumes/analyze` (§6.3) | Alembic |
| 8 | Switch the request body from `resume_text` to `resume_id` | Step 7 |
| 9 | `match_score_history` + recalculate on resume change | Step 8 |
| 10 | Dashboard integration (§8.2) | Step 4 |

### Phase 3 — only if measurement justifies it

Bulk endpoint, Celery, Redis, rate limiting. Each was moved out of the critical path in
§4.2, §9.1 and §9.4; none should be built before a profile shows it is needed.

**On the estimate:** the v1.0 total of ~16 days is dominated by infrastructure that
§4.2/§9 recommend cutting. Phase 1 is roughly 2-3 days of work — the algorithm itself is
a few hundred lines of set operations. Calibrating the score bands against real resumes
(§3.3) will take longer than writing the code, and is the part most worth the time.

---

## Appendices

### Appendix A: Sample Score Calculation

**Resume:**
```
Senior Python Developer with 8 years of experience.
Skills: Python, Django, FastAPI, PostgreSQL, AWS, Docker
Strong in backend development and API design.
```

**Job Description:**
```
Senior Backend Engineer with 5+ years of experience.
Required: Python, Django, PostgreSQL, REST APIs
Nice to have: AWS, Kubernetes, GraphQL
```

**What v1.0 claimed (all three lines are wrong):**
- Hard Skills: `Missing = {REST APIs, Kubernetes, GraphQL}` — `rest apis` and `graphql`
  are **not in `HARD_SKILLS`**, so they can never be detected as required. Executed, the
  actual missing set is `['kubernetes']`.
- Soft Skills: `Matched = {backend, API design}` — neither term is in `SOFT_SKILLS`.
  Both sides extract the **empty set**, and the empty-set rule silently awards 100.
- Final score `74`. Executed, the v1.0 code returns **71**
  (`hard=62.5 soft=100 exp=85 kw=37`).

**Corrected calculation (v1.1 rules):**

Job skills detected: `{python, django, postgresql, aws, kubernetes}`
Resume skills detected: `{python, django, fastapi, postgresql, aws, docker}`

- **Hard skills — coverage, not Jaccard:** 4 of the job's 5 detected skills are covered
  (`kubernetes` is missing). `4/5 = 80.0` → `80.0 × 0.50 = 40.0`
  *(Jaccard would have given 4/7 = 57, penalising the candidate for also knowing FastAPI
  and Docker — neither of which the job asked for.)*
- **Soft skills — unavailable:** the job description states no recognised soft skill, so
  the component is excluded and its 0.20 weight is renormalised away.
- **Experience — asymmetric:** user 8 years ≥ required 5 years → `100.0` → `100.0 × 0.20 = 20.0`
- **Keyword overlap:** `0.37` → `37.0 × 0.10 = 3.7`

Available weight = `0.50 + 0.20 + 0.10 = 0.80`

**Final Score:** `(40.0 + 20.0 + 3.7) / 0.80 = 79.6` → **80** — "Strong match"

Note how the renormalisation in §3.4 matters: without it, the absent soft-skills
component would have silently contributed either a free 20 points (v1.0) or a 20-point
penalty, neither of which reflects anything about this candidate.

> Once implemented, replace these numbers with the output of the real code and assert
> them in a test, so this appendix cannot drift from the implementation again.

### Appendix B: API Response Examples

**Successful Calculation (201):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "match_score": 74,
  "breakdown": {
    "hard_skills": {
      "score": 57,
      "matched_skills": ["Python", "Django", "PostgreSQL", "AWS"],
      "missing_skills": ["REST APIs", "Kubernetes", "GraphQL"]
    },
    "soft_skills": {
      "score": 100,
      "matched_skills": ["backend", "API design"],
      "missing_skills": []
    },
    "experience": {
      "score": 85,
      "user_experience": "8 years",
      "required_experience": "5+ years"
    },
    "keyword_density": 82
  },
  "calculated_at": "2026-08-14T10:30:00Z",
  "status": "completed",
  "suggestions": [
    "Add REST APIs experience to your resume",
    "Mention Kubernetes experience",
    "Consider adding GraphQL experience"
  ]
}
```

**Pending (Async, 202):**
```json
{
  "task_id": "celery-12345678-1234-1234-1234-123456789012",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Error (400):**
```json
{
  "detail": "Resume text is required"
}
```

**Not Found (404):**
```json
{
  "detail": "Job not found or does not belong to you"
}
```

### Appendix C: Database Schema SQL

```sql
-- Match score history table
CREATE TABLE match_score_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    match_score INTEGER NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    hard_skills_score INTEGER NOT NULL CHECK (hard_skills_score >= 0 AND hard_skills_score <= 100),
    soft_skills_score INTEGER NOT NULL CHECK (soft_skills_score >= 0 AND soft_skills_score <= 100),
    experience_score INTEGER NOT NULL CHECK (experience_score >= 0 AND experience_score <= 100),
    keyword_density_score INTEGER NOT NULL CHECK (keyword_density_score >= 0 AND keyword_density_score <= 100),
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resume_version VARCHAR(64) NOT NULL,
    algorithm_version VARCHAR(20) NOT NULL DEFAULT 'v1.0'
);

CREATE INDEX ix_match_score_history_job ON match_score_history(job_id);
CREATE INDEX ix_match_score_history_user_job ON match_score_history(user_id, job_id);
CREATE INDEX ix_match_score_history_calculated ON match_score_history(calculated_at);

-- Match score breakdown table
CREATE TABLE match_score_breakdown (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    hard_skills_matched JSONB NOT NULL DEFAULT '[]',
    hard_skills_missing JSONB NOT NULL DEFAULT '[]',
    soft_skills_matched JSONB NOT NULL DEFAULT '[]',
    soft_skills_missing JSONB NOT NULL DEFAULT '[]',
    experience_details JSONB NOT NULL DEFAULT '{}',
    keyword_similarity FLOAT NOT NULL CHECK (keyword_similarity >= 0.0 AND keyword_similarity <= 1.0),
    suggestions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_match_score_breakdown_job ON match_score_breakdown(job_id);
```

### Appendix D: Required Dependencies

**Phase 1 — everything actually required:**

```
scikit-learn==1.3.2      # TF-IDF + cosine similarity for the keyword component
nltk==3.8.1              # stopword list only
```

```python
# One-time, at build/deploy: _tokenize() imports nltk stopwords at call time and
# raises LookupError if this has never been run. Do it in the Dockerfile, not lazily
# on the first user request.
python -m nltk.downloader stopwords
```

**Deliberately excluded:**

| Package | Why not |
| :--- | :--- |
| `spacy` + `en_core_web_sm` | Listed in v1.0 but **never imported** anywhere in §7.1. A ~50 MB model for code that does not use it. Drop it, or replace the naive taxonomy match with real NER and then justify it. |
| `celery`, `redis` | §4.2 and §9.1 — infrastructure for a computation measured in milliseconds. |
| `slowapi` | §9.4 — deferred, and it should protect the Groq-backed routes first. |
| `transformers`, `sentence-transformers` | Multi-hundred-MB dependency for a Priority 2 idea (§12). Not v1. |

Note `scikit-learn` pulls in `numpy` and `scipy` (~100 MB installed). If the keyword
component is only worth 10% of the score, weigh that against implementing plain cosine
similarity over token counts in ~15 lines and dropping the dependency entirely.

### Appendix E: Environment Variables

```bash
# NLP Configuration
MATCH_SCORE_HARD_SKILLS_WEIGHT=0.50
MATCH_SCORE_SOFT_SKILLS_WEIGHT=0.20
MATCH_SCORE_EXPERIENCE_WEIGHT=0.20
MATCH_SCORE_KEYWORD_WEIGHT=0.10

# Background Processing
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Caching
REDIS_URL=redis://localhost:6379/0
MATCH_SCORE_CACHE_TTL=604800  # 7 days

# Rate Limiting
RATE_LIMIT_CALCULATE=10/minute
RATE_LIMIT_RETRIEVE=100/minute
```

### Appendix F: Glossary

| Term | Definition |
| :--- | :--- |
| ATS | Applicant Tracking System - Software used by employers to manage job applications |
| Hard Skills | Technical, teachable abilities specific to a job (e.g., Python, Django) |
| Soft Skills | Interpersonal skills and personality traits (e.g., communication, leadership) |
| Jaccard Similarity | Measure of similarity between two sets: intersection / union |
| TF-IDF | Term Frequency-Inverse Document Frequency - Statistical measure for word importance in a document |
| Cosine Similarity | Measure of similarity between two vectors in a multi-dimensional space (0 to 1) |
| NLP | Natural Language Processing - AI field for understanding and generating human language |
| Multi-tenant | System architecture where multiple users share the same application but have isolated data |

---

*Document version: v1.1 — algorithm corrected against execution results (see §0)*
*Last updated: 2026-08-14*
*Author: System Design Team*
