# Demo Script — 5-Minute Screen Recording

This is the outline for your demo video. Time estimates are approximate;
adjust based on your pace. Total target: **under 5 minutes**.

---

## Setup Before Recording

- [ ] App is running: `streamlit run app.py` — browser open at localhost:8501
- [ ] Have a JD ready (paste-ready or a sample file)
- [ ] Have 2–3 resumes ready to upload
- [ ] Close unnecessary tabs / notifications
- [ ] Screen resolution: 1920×1080 or higher; browser at 100% zoom

---

## Segment 1 — Introduction (0:00–0:30)

**What to show:** Desktop with the project folder visible, then the app.

**What to say (paraphrase):**

> "This is the Recruiting Screener — an AI-assisted tool that screens
> candidates against a job description, scores each one with cited evidence,
> and outputs an advance / hold / reject recommendation.
>
> The target user is an in-house technical recruiter who screens 40–60 resumes
> per requisition. The goal is to cut screening time by 50% while keeping
> every recommendation explainable with the specific resume text that supports it."

**On screen:**
- Brief view of the app title: "Recruiting Screener 🔍"
- Then the sidebar showing model name

---

## Segment 2 — Upload JD and Resumes (0:30–1:15)

**What to show:** The main app screen with the JD input area.

**What to say:**

> "Here's how it works. First, I'll paste a job description — or upload it
> as a PDF or Word file. Then I upload the resumes I want to screen."

**On screen:**
1. Click into the JD text area. Paste a JD (or use one of the sample JDs from
   `data/samples/`). Show the JD text appearing.
2. Use the resume uploader. Click "Browse files" and select 2–3 resumes
   from `data/samples/`. Show the file names appearing in the uploader.

**Tip:** Use `jd_senior_backend_engineer.txt` plus `resume_candidate_strong.md`
and `resume_candidate_marginal.md` for a clear advance vs. hold contrast.

> **Why 45 seconds:** File picker navigation takes 10–15 seconds alone.
> This segment needs extra time for the browser dialog, not just speaking.

---

## Segment 3 — Run the Pipeline (1:15–1:45)

**What to show:** Clicking the "Score Candidates" button, watching the progress.

**What to say:**

> "Now I'll click Score Candidates. The pipeline parses each file, extracts
> structured data using a Groq LLM, scores every criterion with evidence
> citations, and logs the run to SQLite — all in a few seconds per candidate."

**On screen:**
- Click the "Score Candidates" button.
- Show the loading/progress indicator.
- When results appear, show the results table briefly — the recommendation
  column with 🟢 advance / 🟡 hold / 🔴 reject badges.

---

## Segment 4 — Review a Scorecard (1:45–3:15)

**What to show:** Click into one candidate to see the full scorecard. Spend the
most time here — this is the core value proposition.

**What to say:**

> "Let me click into the strong candidate. This is the scorecard the recruiter
> sees.
>
> **Overall score: 87 out of 100. Recommendation: Advance.**
>
> Here's the rationale — the model's written explanation of why this candidate
> advances.
>
> Below that are the per-criterion scores. Each one shows a 0–100 score,
> the criterion name, and — this is the key part — the exact resume text that
> supports the score. No black-box numbers."

**On screen:**
- Show the overall score, recommendation badge, and rationale paragraph.
- Scroll through criterion scores, pointing out the evidence citations.
- Click into a second candidate (the marginal one) to show a "Hold" scorecard
  and contrast the two.

**For the hold candidate:**

> "This candidate gets a hold. The criterion scores are decent but there's a
> clear gap — no production PostgreSQL experience, and the LLM cited that
> directly from the resume. This is exactly the kind of candidate a recruiter
> should talk to before making a call."

---

## Segment 5 — Show the Evidence Layer (3:00–3:30)

**What to show:** Briefly show a criterion with a low score and its evidence
text to make the "no black box" point concrete.

**What to say:**

> "Every score has a citation. Here the model found no PostgreSQL evidence
> and scored it 12 out of 100, citing the exact text. The recruiter can verify
> this instantly — they don't have to trust a number they can't explain."

**On screen:**
- Point to one criterion score with a low number.
- Highlight the evidence text below it.
- Show that the evidence text matches what's actually in the resume (you can
  briefly switch to the file to prove it).

---

## Segment 6 — Show the Run Log (3:30–4:00)

**What to show:** Open the logs/runs.db in a SQLite browser, or show a code
snippet of a recent log entry.

**What to say:**

> "Every run is logged to a local SQLite database — timestamp, model version,
> inputs, outputs, latency. This gives the recruiter an audit trail and gives
> the team data for continuous improvement."

**On screen:**
- Show a SQLite query or the runs.db file.
- One or two rows is enough — you don't need to show the full schema.

---

## Segment 7 — Show the Eval Results (4:00–4:30)

**What to show:** Terminal window running `python eval/run_eval.py`, or the
`eval/failures.md` regression table.

**What to say:**

> "The system is evaluated against 12 labeled test cases — a mix of advance,
> hold, reject, edge, and failure scenarios. On clear-cut cases, the model
> matches the human label 83% of the time. The remaining divergences are
> judgment-boundary cases where both the model and a human reviewer could
> reasonably disagree — which is exactly why the hold tier exists."

**On screen:**
- Show the regression table from `eval/failures.md` (Category A/B framing).
- Point out: 0 hard failures, 83% primary accuracy, deterministic output
  with temperature=0.

---

## Segment 8 — Wrap Up and Call to Action (4:30–5:00)

**What to show:** Back to the app, or the project README.

**What to say:**

> "The system is ready for a proxy user to test end-to-end. To set it up,
> you need Python 3.11, a Groq API key, and three commands — documented in
> the README. The app runs locally, no cloud deployment needed.
>
> The key design principle: the AI recommends, the human decides. Every score
> cites evidence, every run is logged, and every candidate in the hold tier
> gets a human review before any decision is finalized."

**On screen:**
- Brief view of the README setup section.
- Final view of the app with a scorecard visible.

---

## Timing Checklist

| Segment | Time | Cumulative | Notes |
|---------|------|------------|-------|
| Introduction | 0:30 | 0:30 | |
| Upload JD + resumes | 0:45 | 1:15 | File picker needs extra time |
| Run pipeline | 0:30 | 1:45 | |
| Review scorecard (strong) | 0:30 | 2:15 | |
| Review scorecard (hold) | 0:30 | 2:45 | |
| Evidence layer walkthrough | 0:30 | 3:15 | |
| Run log | 0:30 | 3:45 | |
| Eval results | 0:30 | 4:15 | |
| Wrap up | 0:45 | 5:00 | Trimmed from 1:00 |

---

## Things to Avoid

- Don't show API keys or `.env` contents.
- Don't show personal data — all test data is synthetic.
- Don't claim 100% accuracy — be honest about the hold-tier divergence cases.
- Don't say "Claude built this" — the case study distinguishes build tool
  (Claude Code) from inference model (Groq/Llama).
- Don't skip the evidence citations — that's the most important visual.

---

## If Something Goes Wrong on Camera

- **Groq rate limit (429):** Pause, wait 60s, retry. The batch runner handles
  this automatically — if it happens during recording, note it and move on.
- **App won't start:** Restart the terminal. Keep a backup terminal tab open
  with the app already running before you start recording.
- **File won't upload:** Use a different sample file. Have the three sample
  files pre-pinned to your file picker's recent files so you don't have to
  navigate.
