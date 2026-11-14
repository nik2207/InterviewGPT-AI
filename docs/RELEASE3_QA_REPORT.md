# Release 3 QA & Regression Report — InterviewGPT AI

**Date:** 2026-11-12  
**Scope:** ATS resume builder, GitHub profile analyzer, job application tracker, multilingual interview practice.

---

## Executive summary

| Area | Result |
|------|--------|
| Backend pytest (full suite) | **215 passed** |
| Frontend vitest | **10 passed** (6 files) |
| Frontend production build | **PASS** |
| Release 1 & 2 regression | Included in full pytest/vitest (no new failures) |

Automated coverage is strong for **API contracts, ownership, and mocked GitHub/Gemini**. Live GitHub API, live Gemini resume improvements, and browser speech for hi/mr are **NOT TESTED** in CI.

---

## Phase A — Implementation map

| Feature | Backend | Frontend | Primary tests |
|---------|---------|----------|---------------|
| **ATS resume builder** | `resume_builder_*`, Gemini `SYSTEM_INSTRUCTION` anti-fabrication, PDF | `dashboard/resumes/builder`, `ResumeBuilderPreview` | `test_resume_builder.py` |
| **GitHub analyzer** | `github_api_client` (HTTP only), `github_input_parser`, Gemini analysis | `dashboard/github` | `test_github_analysis.py` |
| **Application tracker** | `job_applications` routes/service, duplicate key | `dashboard/applications` | `test_job_applications.py` |
| **Multilingual practice** | `interview_language_service`, localization on create, eval prompts | Interview session UI, `locales.ts` speech hints | `test_multilingual_interview.py` |

**Security design (verified by audit):**
- GitHub: metadata/README/path samples via REST only — **no repository code execution**.
- Resume AI: system prompt forbids inventing employers, dates, metrics; API returns `requires_user_confirmation` for applies.
- README truncated at `GITHUB_MAX_README_CHARS`; tree paths capped at `GITHUB_MAX_TREE_PATHS`.

---

## 1 — ATS resume builder

| ID | Case | Status | Evidence | Expected |
|----|------|--------|----------|----------|
| RB-01 | Create document | PASS | `test_create_resume_builder` 201 | Persist + disclaimer |
| RB-02 | Edit / patch title | PASS | `test_update_persists_draft` | Saved draft |
| RB-03 | Section ordering | PASS | `test_section_order_validation` | Reorder persisted |
| RB-04 | Validation (schema) | PARTIAL | Pydantic `max_length` on fields; no dedicated overflow route test | 422 on bad payloads |
| RB-05 | AI improve (mocked) | PASS | `test_ai_proposal_requires_confirmation` | No auto-apply |
| RB-06 | AI failure | PASS | `test_ai_failure_handling` 503 | Safe error |
| RB-07 | Anti-invention policy | PASS | `test_resume_ai_system_prompt_forbids_invention` + `RESUME_AI_DISCLAIMER` | No fabricated experience |
| RB-08 | Version history | PASS | `test_save_version_snapshot` | Version list grows |
| RB-09 | PDF export | PASS | `test_pdf_download_ownership`, `test_pdf_generation_readable` | Valid PDF |
| RB-10 | Ownership | PASS | get 404, `test_resume_builder_other_user_404` | Cross-user blocked |
| RB-11 | Auth | PASS | `test_unauthenticated_resume_builder` 401 | JWT required |
| RB-12 | Import from upload resume | NOT TESTED | `source_upload_resume_id` in schema | Optional link |
| RB-13 | UI editor flows | NOT TESTED | Pages exist | Manual |

---

## 2 — GitHub profile analyzer

| ID | Case | Status | Evidence | Expected |
|----|------|--------|----------|----------|
| GH-01 | Valid username | PASS | `test_parse_username_and_url` | Parsed owner |
| GH-02 | Invalid username | PASS | `test_parse_invalid_username` | Error |
| GH-03 | Non-GitHub URL | PASS | `test_parse_invalid_url` | Error |
| GH-04 | Empty input | PASS | `test_parse_empty_input` | Error |
| GH-05 | Lookup + cache | PASS | `test_lookup_success` | Repos list + cache upsert |
| GH-06 | Rate limit | PASS | `test_lookup_rate_limit` 429 | User-safe message |
| GH-07 | Repo analysis (mocked) | PASS | `test_analyze_repository` | Questions + authorship caveat |
| GH-08 | Missing README / AI down | PASS | `test_analyze_missing_readme` failed status | No crash |
| GH-09 | Ownership GET | PASS | `test_analysis_ownership_get` | 200 own / 404 other |
| GH-10 | Auth on lookup | PASS | `test_github_lookup_unauthenticated` | 401 |
| GH-11 | Large README / tree caps | PARTIAL | Logic in `github_api_client.py`; **no unit test** for truncation | Truncate only |
| GH-12 | Malicious README content | PARTIAL | Treated as plain text to Gemini; not executed server-side | No code exec |
| GH-13 | Private repos | NOT TESTED | API returns empty/403 paths | User messaging |
| GH-14 | UI repo selection | NOT TESTED | `github/page.tsx` | Manual |

---

## 3 — Job application tracker

| ID | Case | Status | Evidence | Expected |
|----|------|--------|----------|----------|
| JA-01 | Create | PASS | `test_create_application` | 201 |
| JA-02 | Duplicate | PASS | `test_duplicate_application` 409 | Block duplicate |
| JA-03 | Invalid posting URL | PASS | `test_invalid_url` 422 | ftp rejected |
| JA-04 | Status update | PASS | `test_update_status` | Persist status |
| JA-05 | Search/filter/pagination | PASS | `test_list_filter_pagination` | Query params |
| JA-06 | Stats | PASS | `test_stats` | Aggregates |
| JA-07 | Link resume + job match | PASS | `test_update_links_resume_and_match` | IDs stored |
| JA-08 | Ownership | PASS | `test_ownership_get_not_found`, `test_application_other_user_404` | 404 |
| JA-09 | Auth | PASS | `test_applications_unauthenticated` | 401 |
| JA-10 | Start practice interview | PASS | `test_start_practice` | Session linked |
| JA-11 | Date/timezone edge cases | NOT TESTED | ISO dates in schema | Manual |
| JA-12 | UI kanban/list | NOT TESTED | applications pages | Manual |

---

## 4 — Multilingual interview practice

| ID | Case | Status | Evidence | Expected |
|----|------|--------|----------|----------|
| ML-01 | Default English | PASS | `test_resolve_language_settings_defaults` | en/en/en |
| ML-02 | Hindi session create | PASS | `test_create_interview_persists_hindi_language` | localize called |
| ML-03 | Marathi session create | PASS | `test_create_interview_marathi_triggers_localization` | mr persisted |
| ML-04 | English skips localization | PASS | `test_english_session_skips_localization` | No extra AI |
| ML-05 | Backward compat GET | PASS | `test_get_session_backward_compatible_language` | Defaults en |
| ML-06 | Hindi evaluation prompt | PASS | `test_evaluate_answer_hindi_language_in_prompt` (mocked Gemini) | Hindi in system |
| ML-07 | Bilingual answers flag | PARTIAL | Stored in settings; heuristic eval uses text only | Allow mixed text |
| ML-08 | Marathi speech in browser | NOT TESTED | `SPEECH_RECOGNITION_HINTS.mr = limited_support` | Typed fallback |
| ML-09 | Transcript language labels | PARTIAL | `InterviewLanguageIndicators` in transcript review | UI labels |
| ML-10 | Technical terms in non-English | NOT TESTED | Localization service | Manual quality |
| ML-11 | Language switch mid-session | NOT TESTED | Settings fixed at create | By design? |

---

## Integration journey (Release 3)

| Step | Status |
|------|--------|
| Build resume → GitHub analyze → track application → multilingual interview | **NOT TESTED** (E2E) |

---

## Security (Release 3)

| ID | Case | Status |
|----|------|--------|
| SEC-R3-01 | JWT on builder/github/applications | PASS |
| SEC-R3-02 | Cross-user 404 (`test_release3_security.py`) | PASS |
| SEC-R3-03 | GitHub URL allowlist (github.com only) | PASS (parser tests) |
| SEC-R3-04 | No repo code execution | PASS (audit — HTTP fetch only) |
| SEC-R3-05 | Untrusted README size limits | PARTIAL (config, no dedicated test) |
| SEC-R3-06 | Resume AI confirmation gate | PASS |
| SEC-R3-07 | Application URL validation | PASS (http/https) |

---

## Automation added this pass

| File | Change |
|------|--------|
| `backend/tests/test_release3_security.py` | Cross-tenant + GitHub auth |
| `backend/tests/test_resume_builder.py` | Version save, section order, AI prompt, auth |
| `backend/tests/test_github_analysis.py` | Invalid username / empty input |
| `backend/tests/test_multilingual_interview.py` | Marathi create |
| `backend/tests/test_job_applications.py` | Resume/match links, auth |

---

## Bugs found

| ID | Severity | Status | Notes |
|----|----------|--------|-------|
| — | — | — | No new defects confirmed in this pass |

---

## Regression

Full **215** pytest covers Release 1 career features, Release 2 voice/follow-ups/transcript/company prep, billing, institutions, legacy resume upload/analysis, interviews, PDFs.

Frontend vitest: speech input, coaching feedback, transcript review, preparation plan — **PASS**.

---

## Manual testing still required

1. Resume builder UI: drag-order sections, apply AI suggestion only after confirm, restore version snapshot.
2. Live Gemini resume improve — verify no hallucinated employers/metrics on real drafts.
3. Live GitHub: private repos, empty profile, huge monorepo tree, abusive README (XSS in UI only).
4. Application tracker UI: filters, dates, linking real resume/match IDs from Mongo.
5. Hindi/Marathi: browser STT/TTS, bilingual answers, interview feedback readability.
6. End-to-end Release 3 journey with Google auth and Atlas DB.

---

## Sign-off

Release 3 features are **implemented and regression-clean** under mocked external services. **Conditional PASS** for backend logic; **NOT TESTED** for live GitHub/Gemini and full integration. Do not start Release 4 QA until stakeholders accept manual checklist or add E2E automation.
