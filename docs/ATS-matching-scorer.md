# ATS Matching Score — System Design

**User story:** US-09 — As a Job Seeker, I want to see how well my resume matches each job description, so that I can prioritize applications where I have the strongest fit.

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

### 3.2 Component Details

**Hard Skills Match (50%)**
- Extract skills from job description and resume using NLP
- Calculate Jaccard similarity: (intersection / union) * 100
- Weight by skill importance in job description

**Soft Skills Match (20%)**
- Extract soft skills from both documents
- Calculate cosine similarity between skill vectors

**Experience Level Match (20%)**
- Parse years of experience from job description and resume
- Normalize to 0-100 scale (capped at 20 years)
- Score based on difference: max(0, 100 - abs(user_norm - required_norm))

**Keyword Density Match (10%)**
- Tokenize both documents
- Calculate TF-IDF vectors
- Compute cosine similarity, normalize to 0-100

### 3.3 Score Interpretation

| Score Range | Interpretation | Action |
| :--- | :--- | :--- |
| 85-100 | Excellent match | Apply immediately |
| 70-84 | Strong match | Apply with minor tweaks |
| 55-69 | Good match | Review and tailor resume |
| 40-54 | Moderate match | Consider other factors |
| 20-39 | Weak match | Significant revision needed |
| 0-19 | Poor match | Likely not a good fit |

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

### 4.2 Asynchronous Processing
For better UX, calculation can be done asynchronously:
1. API returns 202 Accepted immediately
2. Background task calculates score
3. Job record updated with match_score
4. Optional: WebSocket notification to frontend

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

Response (201 Created):
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

interface MatchScoreBreakdownProps {
  isOpen: boolean;
  onClose: () => void;
  data: {
    match_score: number;
    breakdown: {
      hard_skills: { score: number; matched: string[]; missing: string[] };
      soft_skills: { score: number; matched: string[]; missing: string[] };
      experience: { score: number; user_experience: string; required_experience: string };
      keyword_density: number;
    };
    suggestions: string[];
  };
}

export function MatchScoreBreakdown({ isOpen, onClose, data }: MatchScoreBreakdownProps) {
  const components = [
    { name: 'Hard Skills', score: data.breakdown.hard_skills.score, weight: 50, color: 'bg-blue-500' },
    { name: 'Soft Skills', score: data.breakdown.soft_skills.score, weight: 20, color: 'bg-green-500' },
    { name: 'Experience', score: data.breakdown.experience.score, weight: 20, color: 'bg-purple-500' },
    { name: 'Keyword Density', score: data.breakdown.keyword_density * 100, weight: 10, color: 'bg-orange-500' },
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

        {(data.breakdown.hard_skills.missing.length > 0 || 
          data.breakdown.soft_skills.missing.length > 0) && (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Missing Skills</h3>
            <div className="grid grid-cols-2 gap-2">
              {data.breakdown.hard_skills.missing.map(skill => (
                <div key={skill} className="bg-red-50 text-red-700 px-2 py-1 rounded text-sm">
                  {skill}
                </div>
              ))}
              {data.breakdown.soft_skills.missing.map(skill => (
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

### 9.1 Caching Strategy

| Data | Cache | TTL | Invalidation |
| :--- | :--- | :--- | :--- |
| Match Score | Redis | 7 days | Resume update, Job description update |
| Score Breakdown | Redis | 7 days | Same as above |
| History/ Breakdown | Database | N/A | N/A |

**Rationale:** NLP processing is expensive, but resume/job data doesn't change frequently.

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
| Calculation failed | 500 | `{"detail": "Score calculation failed", "error": "..."}` |
| Unauthorized | 401 | `{"detail": "Not authenticated"}` |

### 9.4 Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/{job_id}/match-score")
@limiter.limit("10/minute")
async def calculate_job_match_score(...):
    ...

@router.get("/{job_id}/match-score")
@limiter.limit("100/minute")
async def get_job_match_score(...):
    ...
```

**Limits:**
- 10 requests/minute for score calculation
- 100 requests/minute for score retrieval
- 1 request/5 seconds for bulk operations

---

## 10. Testing Strategy

### 10.1 Unit Tests

Test the scoring algorithm in isolation:

```python
# tests/test_match_score.py
import pytest
from app.services.match_score import MatchScoreCalculator

class TestMatchScoreCalculator:
    def test_perfect_match(self):
        calculator = MatchScoreCalculator()
        resume = "Python Django PostgreSQL 5 years of experience"
        job_desc = "Looking for Python Django developer with PostgreSQL experience"
        result = calculator.calculate(job_desc, resume)
        assert result.final_score >= 90
    
    def test_no_match(self):
        calculator = MatchScoreCalculator()
        resume = "Java Spring Boot"
        job_desc = "Python Django PostgreSQL"
        result = calculator.calculate(job_desc, resume)
        assert result.final_score <= 10
    
    def test_partial_match(self):
        calculator = MatchScoreCalculator()
        resume = "Python Django"
        job_desc = "Python Django PostgreSQL AWS"
        result = calculator.calculate(job_desc, resume)
        # Should match Python and Django (50% of required skills)
        assert 40 <= result.final_score <= 60
    
    def test_experience_match(self):
        calculator = MatchScoreCalculator()
        resume = "8 years of Python development"
        job_desc = "Requires 5+ years of Python experience"
        result = calculator.calculate(job_desc, resume)
        assert result.experience_score >= 90
    
    def test_special_characters(self):
        calculator = MatchScoreCalculator()
        resume = "C++ C# .NET developer"
        job_desc = "C++ C# .NET experience required"
        result = calculator.calculate(job_desc, resume)
        assert result.final_score >= 80
    
    def test_empty_inputs(self):
        calculator = MatchScoreCalculator()
        result = calculator.calculate("", "")
        # Should handle gracefully
        assert 0 <= result.final_score <= 100
```

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

| Step | Task | Dependency | Estimated Time |
| :--- | :--- | :--- | :--- |
| 1 | Create match score service with algorithm | None | 2 days |
| 2 | Add database schema (history & breakdown tables) | Step 1 | 1 day |
| 3 | Implement calculation endpoint | Step 2 | 1 day |
| 4 | Implement retrieval endpoint | Step 3 | 0.5 day |
| 5 | Add UI components (badge, breakdown modal) | Step 3 | 2 days |
| 6 | Integrate with search/filter | Step 4 | 0.5 day |
| 7 | Add score breakdown modal UI | Step 5 | 1 day |
| 8 | Implement resume update recalculation | Step 3 | 1 day |
| 9 | Implement bulk calculation endpoint | Step 3 | 1 day |
| 10 | Add Redis caching | Step 4 | 0.5 day |
| 11 | Add Celery background processing | Step 3 | 1 day |
| 12 | Write unit tests | Step 1 | 1 day |
| 13 | Write integration tests | Step 4 | 1 day |
| 14 | Performance optimization | Step 10 | 1 day |
| 15 | Add documentation | All | 0.5 day |

**Total Estimated Time:** ~16 days (3-4 sprints)

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

**Calculation:**
- Hard Skills: Matched = {Python, Django, PostgreSQL, AWS}, Missing = {REST APIs, Kubernetes, GraphQL}
  - Jaccard: 4/7 = 57.14%
  - Score: 57.14 * 0.50 = 28.57
- Soft Skills: Matched = {backend, API design}, Missing = {}
  - Jaccard: 2/2 = 100%
  - Score: 100 * 0.20 = 20.0
- Experience: User = 8 years, Required = 5+ years
  - Normalized: user = 40/100, required = 25/100, diff = 15
  - Score: max(0, 100-15) = 85 * 0.20 = 17.0
- Keyword Density: TF-IDF cosine similarity = 0.82
  - Score: 82 * 0.10 = 8.2

**Final Score:** 28.57 + 20.0 + 17.0 + 8.2 = 73.77 → **74**

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

```
# Core NLP packages
spacy==3.7.2
nltk==3.8.1
scikit-learn==1.3.2

# For production (optional)
transformers==4.36.2
sentence-transformers==2.2.2

# Background processing
celery==5.3.4
redis==5.0.1

# Caching
redis==5.0.1

# Rate limiting
slowapi==0.1.8

# Download spaCy model
python -m spacy download en_core_web_sm
```

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

*Document version: v1.0*  
*Last updated: 2026-08-14*  
*Author: System Design Team*
