"""Shared Pydantic models for the recruiting-screener pipeline.

All cross-boundary data flows through these schemas. The LLM is constrained to
return structured output matching these models via Anthropic tool use.
"""

from __future__ import annotations

from enum import StrEnum
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Recommendation(StrEnum):
    ADVANCE = "advance"
    HOLD = "hold"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class JobDescription(BaseModel):
    """Structured job description, extracted from JD text by the LLM."""

    role_title: str = Field(description="Exact or near-exact job title from the JD")
    company: Optional[str] = Field(default=None, description="Company name if present")
    department: Optional[str] = Field(default=None, description="Department or team")
    employment_type: Optional[str] = Field(
        default=None, description="Full-time, contract, etc."
    )
    location: Optional[str] = Field(default=None, description="Location or remote/hybrid")
    raw_text: str = Field(description="Full plain-text of the job description")

    # Structured criteria derived from the JD
    must_have_skills: List[str] = Field(
        default_factory=list,
        description="Skills or qualifications explicitly labelled required / must-have",
    )
    nice_to_have_skills: List[str] = Field(
        default_factory=list,
        description="Preferred / nice-to-have skills and qualifications",
    )
    min_years_experience: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum years of experience required (null if not specified)",
    )
    education_requirements: List[str] = Field(
        default_factory=list,
        description="Degrees, certifications, or education requirements",
    )
    key_responsibilities: List[str] = Field(
        default_factory=list,
        description="Primary day-to-day responsibilities from the JD",
    )


class ResumeData(BaseModel):
    """Structured candidate data extracted from a resume by the LLM."""

    full_name: str = Field(description="Candidate's full name")
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)

    # Experience: most recent first
    years_of_experience: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total professional experience in years (estimated from dates)",
    )
    current_title: Optional[str] = Field(default=None)
    current_company: Optional[str] = Field(default=None)

    work_history: List[dict] = Field(
        default_factory=list,
        description="List of {title, company, start_date, end_date, description}",
    )

    # Education: most recent first
    education: List[dict] = Field(
        default_factory=list,
        description="List of {degree, institution, year, field_of_study}",
    )

    # Skills and achievements
    skills: List[str] = Field(
        default_factory=list, description="Technical and soft skills explicitly mentioned"
    )
    certifications: List[str] = Field(default_factory=list)
    notable_achievements: List[str] = Field(
        default_factory=list, description="Key accomplishments worth citing during scoring"
    )

    raw_text: str = Field(description="Full plain-text of the resume")


# ---------------------------------------------------------------------------
# Scoring schemas
# ---------------------------------------------------------------------------


class CriterionScore(BaseModel):
    """Score for a single criterion against a single candidate."""

    criterion: str = Field(description="The criterion being scored")
    score: int = Field(
        ge=0,
        le=100,
        description="Score 0–100, where 100 is a perfect match for this criterion",
    )
    evidence: str = Field(
        default="",
        description="Verbatim or near-verbatim text from the resume that justifies this score",
    )
    notes: Optional[str] = Field(
        default=None, description="Brief explanation if the evidence is ambiguous"
    )


class Scorecard(BaseModel):
    """Full scorecard for one candidate against one JD."""

    candidate_name: str
    jd_role: str
    criterion_scores: List[CriterionScore]
    overall_score: float = Field(
        ge=0,
        le=100,
        description="Weighted average of criterion_scores",
    )
    recommendation: Recommendation
    rationale: str = Field(
        description="2–4 sentence summary explaining the overall recommendation"
    )
    confidence: Optional[str] = Field(
        default=None,
        description="high / medium / low — reflects data completeness and ambiguity",
    )
    structural_checks: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results of mandatory seniority/gap checks",
    )
