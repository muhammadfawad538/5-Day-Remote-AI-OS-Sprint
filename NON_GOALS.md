# Non-Goals — Recruiting Screener (5-day sprint)

This document explicitly states what the system will **not** do. These boundaries
keep the scope realistic and honest.

---

## Will Not Do

### 1. Auto-reject candidates
The system will **never** auto-reject without a human reviewing the rationale. It
outputs `advance / hold / reject` recommendations only. A recruiter must confirm
any reject decision.

### 2. Source candidates from job boards or ATS integrations
No integrations with LinkedIn, Indeed, Greenhouse, Lever, or any external
candidate database. Input is manual: recruiter uploads a JD file + resume files.

### 3. Schedule interviews or send communications
No calendar integration, no email sending, no candidate outreach. The system ends
at the recommendation + scorecard output.

### 4. Parse video interviews, cover letters, or portfolios
Resume (PDF/DOCX) + JD (PDF/DOCX) only. Cover letters, GitHub profiles, and
portfolio links are out of scope.

### 5. Handle batch sizes beyond what a single recruiter can manage in one session
No background job queue, no async pipeline, no multi-user authentication. Streamlit
single-session model; one recruiter, one batch at a time.

### 6. Support non-English resumes or JDs (initially)
Phase 1–3 will handle English only. Non-English support is flagged as a known
limitation and may be a future iteration.

### 7. Learn or update scoring weights from recruiter feedback
The scoring model is fixed for the 5-day sprint. No online learning, feedback loop,
or weight tuning from recruiter overrides. (This could be Phase 5+ work.)

### 8. Guarantee legal compliance for hiring decisions
The system provides decision support, not legal advice. Recruiters retain full
responsibility for hiring decisions. No bias-audit or EEOC compliance checking
is built in.

### 9. Operate without an internet connection
Requires Anthropic API access. No offline / local model fallback.

### 10. Replace the recruiter's judgment
The system is a screening aid. Final hiring decisions remain with the human.

---

## Why these boundaries

These non-goals were chosen to:
- Keep Day 3 (working app) achievable within the 5-day window.
- Avoid scope creep into infrastructure, integrations, or legal territory.
- Maintain the "explainable, human-in-the-loop" principle from CLAUDE.md.
