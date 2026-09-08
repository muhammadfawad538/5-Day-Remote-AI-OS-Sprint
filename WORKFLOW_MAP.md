# Workflow Map — Manual Recruiting Screening

This document traces the current manual workflow from job description intake
to candidate recommendation, step by step. It surfaces pain points that the
AI system will address.

---

## End-to-End Workflow

```
[1. JD posted internally]
        │
        ▼
[2. Recruiter receives JD — two supported input paths]
        │
        ├── Path A (primary): Recruiter pastes JD text directly into the app
        │
        └── Path B (secondary): Recruiter uploads JD as PDF or DOCX
        │
        ▼
[3. System parses JD and extracts structured criteria]
    • Must-have skills, nice-to-have skills, years of experience,
      education requirements, key responsibilities
        │  ← Previously manual interpretation; now AI-extracted with recruiter review
        ▼
[4. Recruiter opens each resume — PDF or DOCX attachment]
        │
        ▼
[5. Recruiter manually scans resume for key criteria]
    • Years of experience
    • Required skills / technologies
    • Education / certifications
    • Relevant titles / companies
        │  ← Time-consuming; inconsistent across recruiters
        ▼
[6. Recruiter mentally scores candidate against criteria]
        │  ← No written evidence; subjective weighting
        ▼
[7. Recruiter makes advance / hold / reject decision]
        │
        ▼
[8. Recruiter adds brief notes to ATS or spreadsheet]
        │  ← Notes quality varies widely; rarely cites specific evidence
        ▼
[9. Hiring manager reviews recruiter's summary for shortlisted candidates]
        │
        ▼
[10. Decision confirmed or revised by hiring manager]
```

---

## Pain Points Identified

| # | Pain Point | Impact | AI System Addresses |
|---|-----------|--------|---------------------|
| 1 | Criteria interpretation varies by recruiter | Inconsistent screening across candidates | Structured criteria extraction from JD |
| 2 | Resume scanning is repetitive and slow | ~5–15 min per resume | Automated text extraction + structured scoring |
| 3 | No written evidence for scores | Hard to defend or audit decisions | Evidence citation per criterion |
| 4 | Notes quality varies | Hiring manager can't reliably assess recruiter's rationale | Standardized scorecard with rationale |
| 5 | Batch inconsistency | Some candidates over-scored, others under-scored | Consistent criteria applied to every candidate |
| 6 | Human memory bias | Recruiters anchor on first/last resume reviewed | Structured scoring reduces anchoring |

---

## Exception Paths

| Exception | Current Handling | Proposed System Handling |
|-----------|-----------------|-------------------------|
| Unreadable/scanned PDF | Recruiter skips or manually OCRs | System surfaces clear ParseError; recruiter decides |
| Resume in non-English language | Handled ad-hoc (often skipped) | System flags language; recruiter decides |
| Ambiguous JD (unclear requirements) | Recruiter interprets subjectively | System extracts criteria with confidence score; recruiter reviews |
| Candidate with non-standard career path | High variance in scoring | Evidence-based scoring with explicit notes |
| Duplicate / multiple submissions | Manual dedup | Not in scope (see NON_GOALS.md) |

---

## Confirmed Parameters

All open questions have been resolved. The following parameters are locked:

| Parameter | Value |
|-----------|-------|
| Primary user | Single in-house technical recruiter at a mid-size company (50–500 employees) |
| Target batch size | 40–60 resumes per requisition; designed to support 30–80 |
| JD input — primary | Recruiter pastes JD text directly into the app |
| JD input — secondary | Recruiter uploads JD as PDF or DOCX file |
| Turnaround (screening phase) | 5–10 business days (estimated) |
| Data type | Synthetic, clearly labeled, plausible tech-company scenario |
| Agreement metric | 80% applies to advance/reject only; hold cases are excluded |
| Time reduction target | 50% (from 5–15 min to ≤3 min per resume) |

These are documented in detail in `BASELINE.md`.
