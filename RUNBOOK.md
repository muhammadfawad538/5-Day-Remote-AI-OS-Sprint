# RUNBOOK — Operator Instructions

This document is for whoever runs, maintains, or extends the Recruiting Screener
after handoff. It covers day-to-day operations, common error responses, and how
to extend the system without breaking it.

---

## Who This Is For

- **Primary operator:** The in-house recruiter using the Streamlit app.
- **Secondary operator:** The engineer maintaining the pipeline (you or a future
  developer). This section is marked **[Maintainer]**.

---

## [Recruiter] Daily Use

### Starting the App

```bash
streamlit run app.py
```

The app opens in your default browser. No terminal work needed after this.

### Screening a Batch

1. Paste or upload a JD (text, PDF, or DOCX).
2. Upload resumes — one at a time or in bulk. Supported formats: PDF, DOCX, Markdown.
3. Click **"Score Candidates"**.
4. Review the results table. For each candidate:
   - Read the **overall recommendation** (advance / hold / reject).
   - Check the **rationale** — this is the model's written explanation.
   - Click into a candidate to see per-criterion scores with the exact resume
     text cited as evidence.
5. **Hold** candidates are candidates the model is uncertain about. These always
   need a human decision. Do not treat "hold" as a rejection.
6. Export or copy scorecards as needed (the app displays them in-browser; copy
   from the detail view).

### When a Resume Fails to Parse

If you see `ParseError: PDF contained no extractable text`, the resume is likely
a scanned image. Options:

- Ask the candidate to send a text-readable version.
- Run the file through an OCR tool first, then re-upload the OCR'd text.
- Mark the candidate as **needs human review** — do not silently skip.

The pipeline never silently skips a file. Every parse failure surfaces a clear
error message.

---

## [Maintainer] Environment Setup

### Adding a New Groq Model

Edit `.env`:

```
GROQ_MODEL=qwen/your-new-model-id
```

No code changes required. The model name flows through `config.py` to every
Groq call.

### Rotating API Keys

1. Generate a new key at https://console.groq.com
2. Update `.env`:
   ```
   GROQ_API_KEY=gsk_your_new_key
   ```
3. Restart the app if it is running.

**Do not commit the new key.** `.env` is gitignored. If a key is accidentally
committed, rotate it immediately at the Groq console.

### Running the Eval Harness

**Important: Groq free-tier rate limits.** The free tier has a tokens-per-day
cap. A full 12-case run can exceed it mid-batch and stop with HTTP 429 errors.
For a reliable full eval, use the batched runner:

```bash
python eval/run_batches.py
```

This splits 12 cases into 3 batches of 4 with 90-second inter-batch waits.

To re-run a single case or debug one failure, use the individual runner instead
of `run_eval.py` directly — it spaces calls by 90 seconds to stay within limits:

```bash
python eval/run_individual.py
```

`run_eval.py` on all 12 cases at once is the fastest path but the most likely
to hit the daily token cap. If you get 429 errors, switch to `run_batches.py`
or `run_individual.py`.

For the authoritative regression table and Category A/B failure analysis, see
`eval/failures.md`. The file `eval/results_full.json` shows the most recent
completed run (may be partial if rate limits interrupted it).

### Reading Run Logs

Run logs are stored in `logs/runs.db` (SQLite). Query with any SQLite client:

```sql
-- Recent runs
SELECT timestamp, model, recommendation, latency_seconds
FROM runs ORDER BY id DESC LIMIT 20;

-- All rejections
SELECT timestamp, candidate_name, jd_role, rationale
FROM runs WHERE recommendation = 'reject';

-- Average latency per model
SELECT model, AVG(latency_seconds) as avg_latency
FROM runs GROUP BY model;
```

Schema: `logs/runs.db` — table `runs` with columns:
`id, timestamp, model, jd_raw, resume_raw, scorecard_json, latency_seconds, error`

### Adding a New Test Case

Edit `eval/test_cases.json`. Add a new entry to the `test_cases` list:

```json
{
  "id": "TC-13",
  "label": "synthetic",
  "category": "advance",
  "description": "One-line description of the scenario",
  "jd_file": "data/samples/jd_senior_backend_engineer.txt",
  "resume_file": "data/samples/resume_candidate_strong.md",
  "expected_outcome": "advance",
  "expected_key_evidence": [
    "Evidence phrase 1",
    "Evidence phrase 2"
  ]
}
```

**Rules for new cases:**
- `label` must be `"synthetic"` or `"real"`. Real personal data is not included
  in this repo — if you add real data, handle it per your org's data policy.
- `category` must be one of: `advance`, `hold`, `reject`, `edge`, `failure`.
- `expected_outcome` for unreadable files is `"parse_error"`; include
  `expected_error` with a substring that must appear in the error message.
- Keep `expected_key_evidence` short (1–4 items). The evidence scorer does
  substring matching, so use distinctive phrases from the resume.

### Extending the Pipeline (Pydantic Schema Changes)

All cross-boundary data contracts are Pydantic models in `pipeline/schemas.py`.

**If you add a field:**

1. Add it to the relevant model with a type hint and a docstring.
2. Update the prompt template in `pipeline/extractor.py` or `pipeline/scorer.py`
   so the LLM produces the new field.
3. Run the existing test suite (`python eval/run_eval.py`) to confirm nothing
   regressed.
4. Add a test case that exercises the new field if it changes scoring logic.

**Do not** change field names on existing models without a migration plan for
existing `logs/runs.db` records — the logger serializes Pydantic models to JSON.

---

## [Maintainer] Troubleshooting

### 429 Rate Limit Errors

**Symptom:** Groq returns HTTP 429; pipeline logs `RateLimitError`.

**Cause:** Groq free-tier RPM/TPM limits exceeded.

**Fix:**
- Increase `EVAL_INTER_CASE_DELAY` and `EVAL_INTER_CALL_DELAY` in `.env`.
  Defaults are 5s between cases and 1s between LLM calls within a case.
- For full eval runs, use `python eval/run_batches.py` which includes
  inter-batch waits (default 90s between batches of 4).
- If the error happens in the app (not eval), add a small retry delay in
  `pipeline/scorer.py` — the current code does not retry on 429 in interactive
  mode.

### Timeout Errors

**Symptom:** `timeout_error` in eval results or the app hangs for > 30s.

**Cause:** Groq latency spike or network issue.

**Fix:**
- Retry the request. Groq free-tier has variable latency.
- If timeouts are persistent, reduce the number of resume fields extracted by
  the LLM (simpler prompt = faster response).
- Consider upgrading to Groq paid tier for higher rate limits and lower latency.

### Non-Deterministic Eval Results

**Symptom:** Running `python eval/run_eval.py` twice produces different
recommendations for the same test case.

**Cause:** Something changed the `temperature` parameter on a Groq call, or
Groq updated the underlying model version.

**Fix:**
1. Confirm `temperature=0` is set in all Groq calls (`pipeline/extractor.py`
   and `pipeline/scorer.py`). This is the expected state.
2. Check `logs/runs.db` for the `model` value on the affected run. If the model
   version changed, results may legitimately differ.
3. If `temperature=0` is missing from a call, restore it and re-run eval.

### SQLite Database Locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Two processes writing to `logs/runs.db` simultaneously.

**Fix:** Close the other process. SQLite allows one writer at a time. This is
unusual during normal operation (one app instance + eval runs don't overlap
in typical workflows).

---

## [Maintainer] What Not To Change Without Discussion

These are hard constraints from the original project spec. Changing them changes
the evaluation baseline and should be a deliberate decision:

- **No LangChain / CrewAI / AutoGen.** Use raw Groq SDK + JSON mode.
- **No database beyond SQLite.** Adding Postgres or another DB is out of scope.
- **Streamlit only for the UI.** Do not add a React/Next.js frontend.
- **Evidence-based scoring only.** Every criterion score must cite resume text.
  Do not remove the evidence requirement.
- **Human-in-the-loop.** Do not add an auto-reject-to-ATS path. The system
  recommends; a human confirms.

---

## Escalation

If you encounter a bug that you cannot resolve from this runbook:

1. Check `eval/failures.md` — documented failures may cover your case.
2. Check `CASE_STUDY.md` — the limitations section explains known edge cases.
3. Open an issue with the Groq error message, the test case ID (if from eval),
   and the relevant log entry from `logs/runs.db`.
