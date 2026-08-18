"""ATS match scoring: how much of a job's requirements does this resume cover?

Implements the v1.1 algorithm from `docs/ATS-matching-scorer.md`. The v1.0 code in
that document's §7.1 is deliberately *not* transcribed here — §0 proves it fails three
of its own six tests. The five defects it identifies are fixed as follows:

  D1  Jaccard punished breadth (a candidate who knew more scored lower). Replaced with
      coverage of the *job's* requirements: |resume ∩ job| / |job|.
  D2  `skill in text` credited a JavaScript developer with Java and an HR document with
      AWS. Replaced with word-boundary matching, longest term first.
  D3  Empty inputs scored 90 because missing data defaulted to 100. Replaced with an
      explicit unavailable state.
  D4  Soft skills and experience defaulting to 100 put a 40-point floor under every
      score. Unavailable components are now dropped and the weights renormalised.
  D5  Years-of-experience took the first regex match. Now takes the largest plausible
      one, ignoring figures that are not about work experience.

Two deviations from the document, both deliberate:

  * No scikit-learn and no NLTK. Appendix D lists them for the keyword component but
    also points out that ~100 MB of numpy/scipy for 10% of the score is a poor trade,
    and that TF-IDF over a two-document corpus carries no real IDF signal anyway. The
    keyword component is term-overlap in plain Python, and the stopword list is inline.
  * Keyword overlap is measured as coverage of the job's terms, not cosine similarity.
    Cosine divides by both documents' magnitudes, which reintroduces D1 through the
    back door — a longer resume scores lower for saying more.

The service is pure and synchronous: no I/O, no database, no network. §4.2 measured the
whole computation in single-digit milliseconds, so callers run it inline.
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# Bumped whenever a change would alter the score for unchanged inputs. Persisted
# alongside each score so stored results can be identified as stale (§6.2).
ALGORITHM_VERSION = "v1.1"

# §3.1. These do not have to sum to 1.0 - unavailable components are dropped and the
# survivors renormalised (§3.4), so the sum is recomputed per call regardless.
HARD_SKILLS_WEIGHT = 0.50
SOFT_SKILLS_WEIGHT = 0.20
EXPERIENCE_WEIGHT = 0.20
KEYWORD_WEIGHT = 0.10

# §3.4 guard rail: an empty resume, an empty job description, or a pairing with no
# skills in common must never present as better than "Weak match".
NO_SKILL_OVERLAP_CEILING = 39

# §11.3's "job description with only seniority keywords" case. A posting that states
# one recognised skill makes the hard component binary - 0 or 100, with no gradation -
# and a job with no description at all scored a confident 100 "apply immediately" off
# its title. Coverage of one requirement is not evidence of an excellent match, so a
# thin posting is capped at the top of the "Good match" band and told why.
#
# §3.3 asks for these boundaries to be re-verified against real resumes; this is the
# knob to turn when doing that.
MIN_JOB_SKILLS_FOR_CONFIDENCE = 3
THIN_EVIDENCE_CEILING = 69

# §3.3. Ordered high to low; the first band whose floor is met wins.
SCORE_BANDS: Tuple[Tuple[int, str], ...] = (
    (85, "Excellent match"),
    (70, "Strong match"),
    (55, "Good match"),
    (40, "Moderate match"),
    (20, "Weak match"),
    (0, "Poor match"),
)


# --- SKILL TAXONOMY ---
# Canonical names are lowercase; matching and set arithmetic use these. Display names
# are only applied on the way out, so the API returns "PostgreSQL" rather than
# "postgresql" without complicating the comparison logic.
_HARD_SKILL_DISPLAY: Dict[str, str] = {
    # Languages
    "python": "Python", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "c++": "C++", "c#": "C#", "go": "Go",
    "rust": "Rust", "ruby": "Ruby", "php": "PHP", "scala": "Scala",
    "kotlin": "Kotlin", "swift": "Swift", "sql": "SQL", "bash": "Bash",
    # Backend frameworks
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "spring": "Spring", "spring boot": "Spring Boot", "express": "Express",
    "rails": "Ruby on Rails", "asp.net": "ASP.NET",
    # Frontend
    "react": "React", "angular": "Angular", "vue": "Vue", "next.js": "Next.js",
    "node.js": "Node.js", "html": "HTML", "css": "CSS", "tailwind": "Tailwind CSS",
    # Data stores
    "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "redis": "Redis", "elasticsearch": "Elasticsearch", "sqlite": "SQLite",
    "dynamodb": "DynamoDB", "cassandra": "Cassandra",
    # Cloud and infrastructure
    "aws": "AWS", "gcp": "GCP", "azure": "Azure", "docker": "Docker",
    "kubernetes": "Kubernetes", "terraform": "Terraform", "jenkins": "Jenkins",
    "github actions": "GitHub Actions", "ci/cd": "CI/CD", "nginx": "Nginx",
    "linux": "Linux", "git": "Git", "serverless": "Serverless",
    # API and architecture. §3.2 flags these as missing from v1.0: Appendix A reported
    # "REST APIs" and "GraphQL" as gaps the scorer could never actually detect.
    "rest api": "REST APIs", "graphql": "GraphQL", "grpc": "gRPC",
    "microservices": "Microservices", "websockets": "WebSockets",
    "kafka": "Kafka", "rabbitmq": "RabbitMQ", "celery": "Celery",
    # Security
    "oauth2": "OAuth2", "jwt": "JWT", "owasp": "OWASP",
    # Data and ML
    "machine learning": "Machine Learning", "deep learning": "Deep Learning",
    "nlp": "NLP", "computer vision": "Computer Vision", "llm": "LLMs",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "pandas": "pandas",
    "numpy": "NumPy", "scikit-learn": "scikit-learn", "spark": "Spark",
    # Tooling
    "sqlalchemy": "SQLAlchemy", "alembic": "Alembic", "pytest": "pytest",
    "graphite": "Graphite", "prometheus": "Prometheus", "grafana": "Grafana",
}

_SOFT_SKILL_DISPLAY: Dict[str, str] = {
    "communication": "communication", "leadership": "leadership",
    "teamwork": "teamwork", "collaboration": "collaboration",
    "problem solving": "problem solving", "critical thinking": "critical thinking",
    "adaptability": "adaptability", "creativity": "creativity",
    "time management": "time management", "project management": "project management",
    "stakeholder management": "stakeholder management", "mentoring": "mentoring",
    "coaching": "coaching", "negotiation": "negotiation",
    "conflict resolution": "conflict resolution", "presentation": "presentation",
    "writing": "writing", "ownership": "ownership", "attention to detail":
    "attention to detail",
}

# Surface form -> canonical name. Keeps "k8s" and "Kubernetes" from being counted as
# two separate requirements, which would inflate the coverage denominator.
_ALIASES: Dict[str, str] = {
    "golang": "go",
    "postgres": "postgresql", "psql": "postgresql",
    "node": "node.js", "nodejs": "node.js", "node js": "node.js",
    "nextjs": "next.js", "vue.js": "vue", "vuejs": "vue",
    "k8s": "kubernetes", "amazon web services": "aws",
    "google cloud": "gcp", "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "rest apis": "rest api", "restful api": "rest api", "restful apis": "rest api",
    "restful": "rest api",
    "ci / cd": "ci/cd", "cicd": "ci/cd", "ci cd": "ci/cd",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "natural language processing": "nlp",
    "large language model": "llm", "large language models": "llm",
    "oauth": "oauth2", "oauth 2.0": "oauth2",
    "json web token": "jwt", "json web tokens": "jwt",
    "problem-solving": "problem solving",
    "team work": "teamwork",
    "detail oriented": "attention to detail",
    "detail-oriented": "attention to detail",
}

# Exported under the names §7.1 uses, so a router importing them keeps working.
HARD_SKILLS: Set[str] = set(_HARD_SKILL_DISPLAY)
SOFT_SKILLS: Set[str] = set(_SOFT_SKILL_DISPLAY)


def _surface_forms(canonical: Set[str]) -> List[str]:
    """Every string worth searching for, longest first.

    Length order is what stops "spring" from consuming "spring boot" and "java" from
    consuming "javascript" (§3.2). The caller blanks each match out of the text, so a
    longer term always claims its span before a shorter one can.
    """
    forms = set(canonical)
    forms.update(surface for surface, target in _ALIASES.items() if target in canonical)
    return sorted(forms, key=lambda s: (-len(s), s))


def _boundary_pattern(term: str) -> "re.Pattern":
    """Word-boundary matcher that survives `c++`, `c#`, `node.js` and `scikit-learn`.

    A plain `\\b` is not enough (§3.2): after the `+` in `c++` the boundary sits between
    two non-word characters and never fires. These lookarounds test for adjacent
    *skill* characters instead, which is the property that actually matters - `aws`
    inside `laws` is a false positive, `aws` next to a comma is not.

    The dot is handled separately from the other skill characters. §3.2's suggested
    class lumps them together, but that rejects every skill ending a sentence:
    "Packaged with Docker." scored as *missing* Docker, and "full-stack collaboration."
    made the whole soft-skills component unavailable. A dot only blocks a match when it
    joins two identifier halves (`node.js`, `asp.net`), never when it ends a sentence.
    """
    return re.compile(
        r"(?<![a-z0-9+#])(?<![a-z0-9]\.)"
        + re.escape(term)
        + r"(?![a-z0-9+#])(?!\.[a-z0-9])"
    )


_HARD_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    (_ALIASES.get(form, form), _boundary_pattern(form)) for form in _surface_forms(HARD_SKILLS)
]
_SOFT_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    (_ALIASES.get(form, form), _boundary_pattern(form)) for form in _surface_forms(SOFT_SKILLS)
]


# --- EXPERIENCE EXTRACTION ---
# `(?<!\d)` keeps "2019" from reading as 20 years. Two digits is the plausible range;
# nobody claims 150 years of Python.
_YEARS_RE = re.compile(r"(?<!\d)(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b")

# D5: figures that are about vesting schedules, visas or notice periods are not claims
# about work experience. "401k vests after 2 years" must not become 2 years of Python.
_NOT_EXPERIENCE_RE = re.compile(
    r"401\s*\(?k\)?|vest|pension|tenure|warrant|lease|visa|sponsorship|"
    r"notice period|probation|holiday|pto|paid time off|\bago\b|\bold\b|"
    r"founded|established|incorporated"
)

_SENIORITY_LEVELS: Tuple[Tuple["re.Pattern", float], ...] = (
    (re.compile(r"\b(senior|principal|staff|lead|architect|head of)\b"), 6.0),
    (re.compile(r"\b(mid[- ]level|intermediate)\b"), 3.5),
    (re.compile(r"\b(junior|entry[- ]level|graduate|intern|trainee)\b"), 1.0),
)

# Each additional year short of the requirement costs 15 points, so a candidate two
# years light still scores 70 while one six years light scores 10 (§3.2).
EXPERIENCE_PENALTY_PER_YEAR = 15.0


# --- KEYWORD OVERLAP ---
# Inline rather than nltk (see module docstring). Trimmed to words that carry no signal
# in a resume/JD pairing; domain words like "lead" or "design" are deliberately kept.
_STOPWORDS = frozenset("""
about above after again against all also and any are because been before being below
between both but can did does doing down during each few for from further had has have
having her here hers him his how into its itself just more most not now off once only
other our ours ourselves out over own same she should some such than that the their
theirs them themselves then there these they this those through too under until very
was were what when where which while who whom why will with you your yours yourself
yourselves will would could shall must may might etc via per within across upon
""".split())

_TOKEN_SPLIT_RE = re.compile(r"[^\w+#./-]+")


@dataclass(frozen=True)
class ComponentScore:
    """One of the four weighted components.

    `available=False` means the inputs could not be evaluated - not that the candidate
    scored zero. Unavailable components are excluded from both the numerator and the
    weight sum (§3.4), and `reason` is surfaced so the UI can explain the gap rather
    than render a blank.
    """
    score: Optional[float]
    weight: float
    available: bool = True
    reason: Optional[str] = None


@dataclass(frozen=True)
class SkillComponent(ComponentScore):
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperienceComponent(ComponentScore):
    user_experience: str = "Not specified"
    required_experience: str = "Not specified"
    user_years: Optional[float] = None
    required_years: Optional[float] = None


@dataclass(frozen=True)
class MatchScoreResult:
    """Outcome of one comparison.

    `final_score` is `None`, never 0, when no component could be evaluated - the same
    no-data-is-not-a-zero rule the dashboard uses for conversion rates (§3.4).

    Every collection is a sorted list rather than a set: `list(missing)[:3]` over a set
    returns an arbitrary three entries that change between interpreter runs, so the same
    resume produced different advice on every call (§10.1, TestDeterminism).
    """
    final_score: Optional[int]
    interpretation: str
    hard_skills: SkillComponent
    soft_skills: SkillComponent
    experience: ExperienceComponent
    keyword_density: ComponentScore
    suggestions: List[str]
    algorithm_version: str = ALGORITHM_VERSION
    notes: List[str] = field(default_factory=list)

    # Flat accessors. The weighted components carry the detail, but callers that only
    # want a number (the history table's per-component columns, §6.2) should not have
    # to reach through two objects for it.
    @property
    def hard_skills_score(self) -> Optional[float]:
        return self.hard_skills.score

    @property
    def soft_skills_score(self) -> Optional[float]:
        return self.soft_skills.score

    @property
    def experience_score(self) -> Optional[float]:
        return self.experience.score

    @property
    def keyword_density_score(self) -> Optional[float]:
        return self.keyword_density.score

    @property
    def matched_hard_skills(self) -> List[str]:
        return self.hard_skills.matched_skills

    @property
    def missing_hard_skills(self) -> List[str]:
        return self.hard_skills.missing_skills

    @property
    def matched_soft_skills(self) -> List[str]:
        return self.soft_skills.matched_skills

    @property
    def missing_soft_skills(self) -> List[str]:
        return self.soft_skills.missing_skills

    @property
    def user_experience(self) -> str:
        return self.experience.user_experience

    @property
    def required_experience(self) -> str:
        return self.experience.required_experience


def interpret(score: Optional[int]) -> str:
    """Maps a score onto the §3.3 bands."""
    if score is None:
        return "Not enough data"
    for floor, label in SCORE_BANDS:
        if score >= floor:
            return label
    return "Poor match"


class MatchScoreCalculator:
    """Stateless scorer. Safe to share; `calculate` holds no instance state."""

    def calculate(
        self,
        job_description: str,
        resume_text: str,
        job_title: str = "",
    ) -> MatchScoreResult:
        # The title carries real signal - "Senior Backend Engineer" states both a
        # seniority level and a discipline that the body often only implies.
        job_text = f"{job_description or ''}\n{job_title or ''}"
        resume = resume_text or ""

        job_hard, job_soft = self._extract_skills(job_text)
        resume_hard, resume_soft = self._extract_skills(resume)

        hard = self._score_skills(
            job_hard, resume_hard, HARD_SKILLS_WEIGHT, _HARD_SKILL_DISPLAY,
            "no recognised technical skills in the job description",
        )
        soft = self._score_skills(
            job_soft, resume_soft, SOFT_SKILLS_WEIGHT, _SOFT_SKILL_DISPLAY,
            "no recognised soft skills in the job description",
        )
        experience = self._score_experience(job_text, resume)
        keywords = self._score_keywords(job_text, resume)

        components: Tuple[ComponentScore, ...] = (hard, soft, experience, keywords)
        available = [c for c in components if c.available and c.score is not None]

        notes: List[str] = []
        if not available:
            final: Optional[int] = None
        else:
            total_weight = sum(c.weight for c in available)
            raw = sum(c.score * c.weight for c in available) / total_weight
            final = int(round(raw))

            # Both ceilings answer the same question - how much does the headline number
            # actually know? - so the stricter one wins rather than the later one.
            ceiling = 100
            if not hard.matched_skills:
                # §3.4 guard rail. Without it a pair that shares no skills at all can
                # still score well on whichever components happen to be available: two
                # documents both mentioning "5 years" and nothing else reach 83.
                ceiling = NO_SKILL_OVERLAP_CEILING
                capped_because = (
                    "the resume and job description share no recognised skills"
                )
            elif len(job_hard) < MIN_JOB_SKILLS_FOR_CONFIDENCE:
                ceiling = THIN_EVIDENCE_CEILING
                capped_because = (
                    f"this posting names only {len(job_hard)} recognised skill"
                    f"{'' if len(job_hard) == 1 else 's'}, which is too little to "
                    "certify a strong match"
                )

            if final > ceiling:
                notes.append(f"Score capped at {ceiling}: {capped_because}.")
                final = ceiling

        return MatchScoreResult(
            final_score=final,
            interpretation=interpret(final),
            hard_skills=hard,
            soft_skills=soft,
            experience=experience,
            keyword_density=keywords,
            suggestions=self._generate_suggestions(hard, soft, experience),
            notes=notes,
        )

    # --- extraction ---

    def _extract_skills(self, text: str) -> Tuple[Set[str], Set[str]]:
        """Returns (hard, soft) canonical skill names found in `text`.

        Matched spans are blanked out as we go, longest term first, so "Spring Boot"
        is not also counted as "Spring" and "JavaScript" is not also counted as "Java".
        Blanking preserves length (spaces, not deletion) to keep the boundary
        lookarounds around neighbouring matches honest.
        """
        working = (text or "").lower()
        hard, working = self._claim(working, _HARD_PATTERNS)
        soft, _ = self._claim(working, _SOFT_PATTERNS)
        return hard, soft

    @staticmethod
    def _claim(
        text: str, patterns: List[Tuple[str, "re.Pattern"]]
    ) -> Tuple[Set[str], str]:
        found: Set[str] = set()
        chars = list(text)
        for canonical, pattern in patterns:
            for match in pattern.finditer("".join(chars)):
                found.add(canonical)
                for i in range(match.start(), match.end()):
                    chars[i] = " "
        return found, "".join(chars)

    def _extract_years(self, text: str) -> Optional[float]:
        """Largest plausible years-of-experience figure, or None.

        D5: v1.0 took the first match, so "Minimum 2 years required, 10 years
        preferred" read as 2. Figures in a non-experience context are discarded before
        the maximum is taken.
        """
        lowered = (text or "").lower()

        candidates = [
            float(match.group(1))
            for match in _YEARS_RE.finditer(lowered)
            if not _NOT_EXPERIENCE_RE.search(self._context_before(lowered, match.start()))
        ]
        if candidates:
            return max(candidates)

        # No explicit figure: fall back to what the seniority language implies.
        for pattern, years in _SENIORITY_LEVELS:
            if pattern.search(lowered):
                return years
        return None

    @staticmethod
    def _context_before(text: str, start: int, window: int = 40) -> str:
        """The words immediately preceding a match, clipped at the sentence boundary.

        Clipping matters: in "401k vests after 2 years. Seeking 10+ years" a flat
        40-character window would drag "401k" forward and disqualify the 10 as well.
        """
        chunk = text[max(0, start - window):start]
        for terminator in (".", ";", "\n", "•"):
            _, sep, tail = chunk.rpartition(terminator)
            if sep:
                chunk = tail
        return chunk

    def _tokenize(self, text: str) -> List[str]:
        """Content words, duplicates kept so term frequency still means something."""
        tokens = _TOKEN_SPLIT_RE.split((text or "").lower())
        return [t for t in tokens if len(t) > 2 and t not in _STOPWORDS]

    # --- components ---

    def _score_skills(
        self,
        job_skills: Set[str],
        resume_skills: Set[str],
        weight: float,
        display: Dict[str, str],
        unavailable_reason: str,
    ) -> SkillComponent:
        """Coverage of the job's requirements, not set overlap.

        D1: Jaccard divided by the union, so a candidate who knew everything the job
        asked for *plus* nine other technologies scored 38 points below one who knew
        only the three required. The denominator here is the job's requirements alone,
        which is also the question the user is asking - "how much of what they want do
        I have?"
        """
        if not job_skills:
            return SkillComponent(
                score=None, weight=weight, available=False, reason=unavailable_reason
            )

        matched = job_skills & resume_skills
        missing = job_skills - resume_skills
        return SkillComponent(
            score=len(matched) / len(job_skills) * 100.0,
            weight=weight,
            matched_skills=sorted(display.get(s, s) for s in matched),
            missing_skills=sorted(display.get(s, s) for s in missing),
        )

    def _score_experience(self, job_text: str, resume_text: str) -> ExperienceComponent:
        """Asymmetric: exceeding the requirement is a match, not a mismatch.

        v1.0 scored on absolute difference, which rated a 20-year veteran applying to a
        5-year role at 25/100 (§3.2).
        """
        required = self._extract_years(job_text)
        user = self._extract_years(resume_text)

        req_label = f"{required:g} years" if required is not None else "Not specified"
        user_label = f"{user:g} years" if user is not None else "Not specified"

        if required is None or user is None:
            missing_side = (
                "job description" if required is None else "resume"
            )
            return ExperienceComponent(
                score=None,
                weight=EXPERIENCE_WEIGHT,
                available=False,
                reason=f"no experience statement found in the {missing_side}",
                user_experience=user_label,
                required_experience=req_label,
                user_years=user,
                required_years=required,
            )

        if user >= required:
            score = 100.0
        else:
            score = max(0.0, 100.0 - (required - user) * EXPERIENCE_PENALTY_PER_YEAR)

        return ExperienceComponent(
            score=score,
            weight=EXPERIENCE_WEIGHT,
            user_experience=user_label,
            required_experience=req_label,
            user_years=user,
            required_years=required,
        )

    def _score_keywords(self, job_text: str, resume_text: str) -> ComponentScore:
        """Share of the job's vocabulary the resume actually uses.

        Frequency-weighted, so a term the posting repeats five times counts for more
        than one it mentions once. Deliberately *not* cosine similarity: cosine divides
        by both documents' magnitudes, so a longer resume scores lower for saying more -
        the same breadth penalty D1 removed from the skills component.
        """
        job_tokens = self._tokenize(job_text)
        if not job_tokens:
            return ComponentScore(
                score=None,
                weight=KEYWORD_WEIGHT,
                available=False,
                reason="job description has no scoreable terms",
            )

        resume_tokens = set(self._tokenize(resume_text))
        counts = Counter(job_tokens)
        total = sum(counts.values())
        covered = sum(n for term, n in counts.items() if term in resume_tokens)
        return ComponentScore(score=covered / total * 100.0, weight=KEYWORD_WEIGHT)

    # --- advice ---

    def _generate_suggestions(
        self,
        hard: SkillComponent,
        soft: SkillComponent,
        experience: ExperienceComponent,
    ) -> List[str]:
        """Up to five concrete actions, in a stable order.

        The lists are already sorted by `_score_skills`, which is what makes repeated
        calls on identical input return identical advice.
        """
        suggestions: List[str] = []

        if hard.missing_skills:
            suggestions.append(
                f"Add experience with: {', '.join(hard.missing_skills[:3])}"
            )
        if soft.missing_skills:
            suggestions.append(
                f"Highlight soft skills: {', '.join(soft.missing_skills[:3])}"
            )

        if (
            experience.available
            and experience.user_years is not None
            and experience.required_years is not None
            and experience.user_years < experience.required_years
        ):
            gap = experience.required_years - experience.user_years
            suggestions.append(
                f"The role asks for {experience.required_years:g} years and your resume "
                f"states {experience.user_years:g}; close the {gap:g}-year gap or lead "
                "with the most relevant projects."
            )
        elif not experience.available:
            suggestions.append(
                "State your total years of experience explicitly - neither side of this "
                "comparison could be read."
            )

        if not hard.available:
            suggestions.append(
                "This posting lists no recognised technical skills, so the score leans "
                "on weaker signals. Treat it as indicative only."
            )

        return suggestions[:5]


# Module-level singleton. The calculator is stateless, so one instance is enough and
# the compiled patterns above are built once at import.
match_score_calculator = MatchScoreCalculator()


def calculate_match_score(
    job_description: str,
    resume_text: str,
    job_title: str = "",
) -> MatchScoreResult:
    """Scores `resume_text` against a job posting. See `MatchScoreCalculator.calculate`."""
    return match_score_calculator.calculate(job_description, resume_text, job_title)
