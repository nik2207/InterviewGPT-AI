# Stage 1 QA & Regression Report — InterviewGPT AI

**Date:** 2026-11-12  
**Scope:** Features 1.1–1.4 only (Release 1 career stack). Billing/credits/institution covered by separate release QA.

---

## Executive summary

| Area | Result |
|------|--------|
| Backend pytest | **194 passed** (includes Stage 1 + platform tests) |
| Frontend vitest | **8 passed** (5 files) |
| Frontend production build | **PASS** (`npm run build`, 2026-11-12) |
| Confirmed bug fixed in this pass | Plan **regenerate** now uses same entitlement + credit gate as initial generate |

Stage 1 core flows are implemented end-to-end with mocked Gemini in automated tests. Several UI areas remain **partial** (static copy, job-specific interview deep link, readiness history list). Full E2E against live Gemini/Mongo was **NOT TESTED** in automation.

---

## Phase A — Implementation map (abbreviated)

See audit agent summary: job match (`job_matches`), coach (nested on `interview_sessions`), 7-day plan (`preparation_plans` + LangGraph), readiness (`career_readiness_reports`, deterministic scoring + PDF).

**Notable gaps (no code change this pass unless noted):**
- Career page skills/resources sections are static placeholders (`frontend/app/dashboard/career/page.tsx`).
- Job match “Start mock interview” does not pass JD questions into session create (`JobMatchResults.tsx`).
- Readiness `fetchCareerReadinessReports` not wired to UI.
- Free tier coach redaction is server-side; limited upgrade messaging in UI.

---

## Phase B–E — Test matrix (Stage 1)

Status key: **PASS** | **FAIL** | **BLOCKED** | **NOT TESTED**

### 1.1 Job description match

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| JM-01 | Valid analysed resume + JD | PASS | `test_create_job_match_success` 201, score + questions | Persisted match | — |
| JM-02 | Missing resume | NOT TESTED | — | 404 | — |
| JM-03 | Other user's resume | NOT TESTED | Service uses `find_by_id_for_user` | 404 | — |
| JM-04 | No analysis | PASS | `test_create_job_match_requires_analysis` 422 | Block without analysis | — |
| JM-05 | Empty/oversized JD | NOT TESTED | Schema limits exist | 422/413 | — |
| JM-06 | Skill extraction / score | PASS | `test_job_match_score_service.py` | Deterministic score | — |
| JM-07 | Save & retrieve | PARTIAL | Create mocked; list/get routes exist | Round-trip | — |
| JM-08 | Gemini failure | NOT TESTED | Route mocks Gemini success only | 502 + safe message | — |
| JM-09 | Cross-user GET match | PASS | `test_job_match_other_user_returns_404` | 404 | — |

### 1.2 Answer improvement coach

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| AC-01 | Coach in Gemini payload | PASS | `test_evaluate_answer_includes_improvement_coach` | Coach fields present | — |
| AC-02 | Malformed Gemini JSON | PASS | `test_evaluate_answer_rejects_invalid_payload` | Validation error | — |
| AC-03 | Empty answer | NOT TESTED | Route validation | 422 | — |
| AC-04 | Persistence on session | PASS | Via `test_interview_routes` (mocked repo) | Saved on answer | — |
| AC-05 | Free tier redaction | PASS | `test_free_tier_strips_coach_payload` | No coach blob | — |
| AC-06 | Technical vs behavioural variants | NOT TESTED | — | Distinct prompts | — |

### 1.3 Seven-day preparation plan

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| PP-01 | Generate with evidence | PASS | `test_preparation_plan_routes` (mocked graph) | 201 plan | — |
| PP-02 | No analysed resume | PASS | `test_generate_requires_analysed_resume` 422 | Block | — |
| PP-03 | Task completion persistence | PASS | `test_update_task_ownership` | Updated counts | — |
| PP-04 | Regenerate billing | **PASS (fixed)** | Was ungated; now credit + feature + refund on fail | Same as generate | **Medium** |
| PP-05 | Regenerate automated test | PASS | `test_regenerate_plan_success` 201 | 201 + charge | — |
| PP-06 | Cross-user GET plan | PASS | `test_preparation_plan_other_user_returns_404` | 404 | — |
| PP-07 | LangGraph workflow unit | PASS | `test_preparation_plan_workflow.py` | Valid structure | — |

### 1.4 Career readiness report

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| CR-01 | Generate with evidence | PASS | `test_career_readiness_routes` | 201 report | — |
| CR-02 | Scoring aggregation | PASS | `test_career_readiness_scoring.py` | Deterministic scores | — |
| CR-03 | PDF endpoint | PASS | Route test returns PDF bytes | application/pdf | — |
| CR-04 | No interviews | NOT TESTED | — | Degraded report | — |
| CR-05 | Cross-user GET report | PASS | `test_readiness_report_other_user_returns_404` | 404 | — |
| CR-06 | Report history UI | BLOCKED | API list exists; UI not wired | List in UI | Low |

### Security (Stage 1 subset)

| ID | Case | Status | Notes |
|----|------|--------|-------|
| SEC-01 | Unauthenticated job match | PASS | 401 |
| SEC-02 | Cross-user job match | PASS | 404 |
| SEC-03 | Cross-user plan | PASS | 404 |
| SEC-04 | Cross-user readiness | PASS | 404 |
| SEC-05 | Cross-user resume GET | PASS | 404 |
| SEC-06 | JWT user_id spoof in body | PASS | Ownership via `current_user.id` in services |
| SEC-07 | Gemini secret leakage | NOT TESTED (manual) | Errors mapped in services |
| SEC-08 | Oversized payloads | PARTIAL | Resume upload 413 tested; JD length not dedicated |

---

## Phase C — Frontend (manual + automated)

| ID | Area | Status | Notes |
|----|------|--------|-------|
| FE-01 | Preparation plan UI | PASS | `PreparationPlanView.test.tsx` |
| FE-02 | Interview feedback / coach UI | PASS | `InterviewFeedback.test.tsx` |
| FE-03 | Job match results UI | NOT TESTED | No vitest |
| FE-04 | Readiness view UI | NOT TESTED | No vitest |
| FE-05 | Career form validation / errors | NOT TESTED | Manual recommended |
| FE-06 | Full journey (sign-in → PDF) | NOT TESTED | Requires manual or Playwright |

---

## Phase D — Integration journey

| Step | Status | Notes |
|------|--------|-------|
| 1–14 full journey | **NOT TESTED** (automated) | Backend pieces covered in isolation; no single Playwright/Cypress flow |

---

## Phase F — Files changed this QA pass

| File | Change |
|------|--------|
| `backend/app/api/routes/preparation_plans.py` | Regenerate: feature + credit charge + refund on failure |
| `backend/tests/test_stage1_security.py` | Cross-tenant 404s + free-tier coach redaction |
| `backend/tests/test_preparation_plan_routes.py` | `test_regenerate_plan_success` |
| `docs/STAGE1_QA_REPORT.md` | This report |

---

## API verification (representative)

| Endpoint | Verified by |
|----------|-------------|
| `POST /api/v1/job-matches` | `test_job_match_routes.py` |
| `POST /api/v1/interviews/{id}/answers` | `test_interview_routes.py` |
| `POST /api/v1/preparation-plans` | `test_preparation_plan_routes.py` |
| `POST /api/v1/preparation-plans/{id}/regenerate` | `test_regenerate_plan_success` |
| `POST /api/v1/career-readiness/reports` | `test_career_readiness_routes.py` |

---

## Regression (platform)

Included in **194** pytest: auth, resumes, interviews, speech, billing, credits, institutions, applications, etc.

---

## Manual testing still required

1. Live Gemini job match, plan generation, and answer evaluation (paid API, latency, rate limits).
2. Full Phase D journey in browser with real Google sign-in and MongoDB Atlas.
3. Free vs Pro coach visibility in UI copy and upgrade paths.
4. Job-specific mock interview from match page (currently generic interviews link).
5. Mobile/responsive pass on career and interview session pages.
6. Readiness report with zero completed interviews and with job-specific `job_match_id`.

---

## Recommendations (report before large changes)

1. Wire readiness report history list in UI.
2. Pass `job_match_id` / suggested questions into interview session creation from job match.
3. Replace static skills/resources blocks with data from latest match or analysis.
4. Add pytest for plan regenerate billing and Gemini failure paths for job match / plan.
5. Add vitest for `JobMatchResults` and `CareerReadinessView` loading/error states.

---

**Sign-off:** Stage 1 features are **substantially complete** with strong automated backend coverage (mocked AI). **Do not mark production-ready for paid AI** until manual Phase D and live Gemini checks are complete.
