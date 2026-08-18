"""Test cases for the ATS match scoring algorithm.

This is the §10.1 suite from `docs/ATS-matching-scorer.md`, which is the specification
for `services/match_score.py`. The document's §0 records that the v1.0 algorithm failed
three of these six cases; they are kept verbatim so that can never regress silently.

`TestDocumentedDefects` adds the §0 examples the document describes but never turned
into tests, and `TestEvidenceCeiling` covers a guard rail added during implementation
(§11.3's "job description with only seniority keywords" case).

The scorer is pure: no database, no network, no fixtures beyond the calculator itself.
"""
import pytest

from app.services.match_score import (
    MIN_JOB_SKILLS_FOR_CONFIDENCE,
    NO_SKILL_OVERLAP_CEILING,
    THIN_EVIDENCE_CEILING,
    MatchScoreCalculator,
    calculate_match_score,
    interpret,
)


@pytest.fixture
def calc():
    return MatchScoreCalculator()


class TestScoring:
    """The headline number, end to end."""

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

    def test_module_level_helper_matches_the_class(self, calc):
        args = ("Python Django AWS", "Python Django, 5 years")
        assert calculate_match_score(*args) == calc.calculate(*args)


class TestCoverageNotJaccard:
    """D1: extra skills must never reduce the score."""

    def test_breadth_is_not_penalised(self, calc):
        jd = "We need Python, Django and PostgreSQL"
        narrow = calc.calculate(jd, "Python Django PostgreSQL")
        broad = calc.calculate(jd, "Python Django PostgreSQL AWS Docker React Redis Go")
        assert broad.hard_skills_score == narrow.hard_skills_score == 100
        assert broad.final_score >= narrow.final_score

    def test_coverage_denominator_is_the_job_not_the_union(self, calc):
        """A resume listing nine extra technologies still covers 3 of 3."""
        r = calc.calculate(
            "Requires Python, Django, PostgreSQL",
            "Python Django PostgreSQL AWS Docker React Redis Go Kubernetes Flask",
        )
        assert r.hard_skills_score == 100
        assert r.missing_hard_skills == []


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

    @pytest.mark.parametrize("text,expected", [
        # A skill ending a sentence must still be found. The character class §3.2
        # suggests groups the dot with the other skill characters, which silently
        # dropped every skill followed by a full stop.
        ("Packaged with Docker.", "docker"),
        ("I use Python.", "python"),
        # ...while a dot joining two identifier halves must still bind them together
        ("Backend built on Node.js", "node.js"),
        ("Built on ASP.NET", "asp.net"),
    ])
    def test_dot_handling(self, calc, text, expected):
        hard, _ = calc._extract_skills(text)
        assert expected in hard

    def test_sentence_final_soft_skill_is_found(self, calc):
        _, soft = calc._extract_skills("We value full-stack collaboration.")
        assert "collaboration" in soft

    def test_aliases_collapse_onto_one_canonical_skill(self, calc):
        """k8s and Kubernetes are one requirement, not two."""
        hard, _ = calc._extract_skills("Experience with k8s and Kubernetes")
        assert hard == {"kubernetes"}


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

    def test_unavailable_component_is_excluded_not_zeroed(self, calc):
        """A missing component must not drag the score down either (§3.4)."""
        r = calc.calculate("Requires Python, Django and PostgreSQL",
                           "Python Django PostgreSQL")
        assert r.soft_skills.available is False
        assert r.soft_skills.score is None
        # Renormalisation: hard=100 and keyword high, with soft's weight removed
        assert r.final_score >= 90

    def test_null_score_is_not_a_zero(self, calc):
        r = calc.calculate("", "")
        assert r.final_score is None
        assert r.interpretation == "Not enough data"


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

    @pytest.mark.parametrize("text,expected", [
        ("Minimum 2 years required, 10 years preferred", 10.0),
        ("3 years at Acme, then 8 years at Globex", 8.0),
    ])
    def test_d5_documented_examples(self, calc, text, expected):
        assert calc._extract_years(text) == expected

    def test_shortfall_is_graduated(self, calc):
        """Two years light is a near miss; six years light is not (§3.2)."""
        near = calc.calculate("Requires 5 years of Python", "3 years of Python")
        far = calc.calculate("Requires 8 years of Python", "2 years of Python")
        assert near.experience_score == 70
        assert far.experience_score == 10

    def test_seniority_words_stand_in_for_a_figure(self, calc):
        assert calc._extract_years("Senior Backend Engineer") == 6.0
        assert calc._extract_years("Junior developer") == 1.0

    def test_leadership_is_not_read_as_lead(self, calc):
        """The seniority fallback needs word boundaries too."""
        assert calc._extract_years("Strong leadership and communication") is None

    def test_no_figure_on_either_side_is_unavailable(self, calc):
        r = calc.calculate("Python developer", "Python developer")
        assert r.experience.available is False
        assert r.user_experience == "Not specified"
        assert r.required_experience == "Not specified"


class TestGuardRails:
    """§3.4: absence of overlap must never present as a good match."""

    def test_matching_years_alone_is_not_a_strong_match(self, calc):
        """Both sides say "years" and nothing else; uncapped this reached 83."""
        r = calc.calculate("Requires 5 years", "8 years")
        assert r.final_score <= NO_SKILL_OVERLAP_CEILING
        assert r.notes, "a capped score must explain itself"

    def test_cap_is_not_applied_when_skills_do_overlap(self, calc):
        r = calc.calculate("Requires Python, Django, PostgreSQL and AWS",
                           "Python Django PostgreSQL AWS, 5 years")
        assert r.final_score > NO_SKILL_OVERLAP_CEILING
        assert r.notes == []


class TestEvidenceCeiling:
    """§11.3: a posting that states almost nothing cannot certify a strong match.

    Not in the §10.1 suite. Found while wiring up the API: a job saved with no
    description at all scored 100 "Excellent match" off its title, because the single
    skill the title mentions was covered and every other component was unavailable.
    """

    def test_title_only_job_is_capped(self, calc):
        r = calc.calculate("", "Senior Python Developer with 8 years of experience",
                           job_title="Senior Python Developer")
        assert r.final_score == THIN_EVIDENCE_CEILING
        assert r.notes

    def test_thin_posting_still_beats_no_overlap(self, calc):
        """The cap lowers confidence; it does not claim the match is bad."""
        thin = calc.calculate("Python role", "Python developer, 5 years")
        none = calc.calculate("Python Django PostgreSQL", "Java Spring Boot")
        assert none.final_score < thin.final_score <= THIN_EVIDENCE_CEILING

    def test_detailed_posting_is_not_capped(self, calc):
        jd = ("Required: Python, Django, PostgreSQL, AWS. "
              "Requires 5 years of experience.")
        r = calc.calculate(jd, "Python Django PostgreSQL AWS, 8 years")
        assert len(r.matched_hard_skills) >= MIN_JOB_SKILLS_FOR_CONFIDENCE
        assert r.final_score > THIN_EVIDENCE_CEILING
        assert r.notes == []


class TestSuggestions:
    def test_names_the_missing_skills(self, calc):
        r = calc.calculate("Required: Python, Django, PostgreSQL, AWS, Kubernetes",
                           "Python Django, 5 years")
        assert any("AWS" in s for s in r.suggestions)

    def test_capped_at_five(self, calc):
        r = calc.calculate(
            "Required: Python, Django, PostgreSQL, AWS, Kubernetes, React, Redis. "
            "Excellent communication, leadership and mentoring. Requires 10 years.",
            "Python, 1 year",
        )
        assert len(r.suggestions) <= 5

    def test_flags_a_shortfall_in_years(self, calc):
        r = calc.calculate("Requires 10 years of Python, Django and PostgreSQL",
                           "Python Django PostgreSQL, 4 years")
        assert any("10" in s and "4" in s for s in r.suggestions)


class TestDeterminism:
    def test_repeated_calls_are_identical(self, calc):
        jd, cv = "Python Django AWS Docker", "Python Django Redis"
        first = calc.calculate(jd, cv)
        assert all(calc.calculate(jd, cv) == first for _ in range(5)), \
            "suggestions built from unordered sets vary between runs; sort them"

    def test_skill_lists_are_sorted(self, calc):
        r = calc.calculate("Required: Redis, AWS, Python, Django, Kubernetes",
                           "Python, 5 years")
        assert r.missing_hard_skills == sorted(r.missing_hard_skills)


class TestInterpretation:
    @pytest.mark.parametrize("score,label", [
        (100, "Excellent match"), (85, "Excellent match"),
        (84, "Strong match"), (70, "Strong match"),
        (69, "Good match"), (55, "Good match"),
        (54, "Moderate match"), (40, "Moderate match"),
        (39, "Weak match"), (20, "Weak match"),
        (19, "Poor match"), (0, "Poor match"),
        (None, "Not enough data"),
    ])
    def test_bands(self, score, label):
        assert interpret(score) == label


class TestDocumentedDefects:
    """The §0 examples the document states as prose but never asserted."""

    def test_d1_breadth_gap_is_gone(self, calc):
        """§0: candidate B knew everything A knew plus nine more, and scored 38 lower."""
        jd = "job needs: python, django, postgresql"
        a = calc.calculate(jd, "python django postgresql")
        b = calc.calculate(jd, "python django postgresql aws docker react redis go "
                               "kubernetes terraform mongodb flask")
        assert a.hard_skills_score == b.hard_skills_score == 100
        assert b.final_score >= a.final_score

    def test_appendix_a(self, calc):
        """Appendix A's worked example, pinned to the real output.

        The appendix predicts 80 while assuming `REST APIs` and `GraphQL` stay
        undetectable - the very defect it reports. Adding them to the taxonomy (§3.2)
        grows the job side from 5 recognised skills to 7, so coverage is 4/7, not 4/5.
        The appendix asks for its numbers to be replaced by real output once
        implemented; these are them.
        """
        resume = ("Senior Python Developer with 8 years of experience.\n"
                  "Skills: Python, Django, FastAPI, PostgreSQL, AWS, Docker\n"
                  "Strong in backend development and API design.")
        jd = ("Senior Backend Engineer with 5+ years of experience.\n"
              "Required: Python, Django, PostgreSQL, REST APIs\n"
              "Nice to have: AWS, Kubernetes, GraphQL")

        r = calc.calculate(jd, resume)

        assert r.final_score == 67
        assert r.interpretation == "Good match"
        assert r.hard_skills_score == pytest.approx(57.14, abs=0.01)
        assert r.matched_hard_skills == ["AWS", "Django", "PostgreSQL", "Python"]
        # Both were reported as missing by the v1.0 appendix but were absent from the
        # taxonomy, so neither could ever actually be detected
        assert r.missing_hard_skills == ["GraphQL", "Kubernetes", "REST APIs"]
        assert r.soft_skills.available is False
        assert r.experience_score == 100
        assert r.user_experience == "8 years"
        assert r.required_experience == "5 years"
