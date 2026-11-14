# Release 2 QA & Regression Report — InterviewGPT AI

**Date:** 2026-11-12  
**Scope:** Voice interviewer, dynamic follow-ups, transcript/replay, company-specific preparation.

---

## Executive summary

| Area | Result |
|------|--------|
| Backend pytest (full suite) | **202 passed** |
| Frontend vitest | **10 passed** (6 files) |
| Frontend production build | **PASS** |

Core Release 2 behaviour is implemented and covered primarily by **mocked** Gemini/speech tests. **Live** browser microphone, Web Speech API, and TTS provider behaviour is **NOT TESTED** in automation and must not be inferred from mocks.

**Architecture note:** Audio **recording/playback is not implemented**. Voice mode persists **text transcript lines** and speech **metrics** only; UI and API explicitly set `audio_playback_supported: false` and disclose a text-only retention policy.

---

## Phase A — Implementation map

| Feature | Backend | Frontend | Existing tests |
|---------|---------|----------|----------------|
| **Voice interviewer** | `voice_interview_service.py`, clarification via `gemini_voice_clarification_service.py`; routes under `/interviews/{id}/voice/*`; transcript append on session `voice_interview` | `VoiceInterviewExperience.tsx`, `SpeechAnswerInput.tsx`, `lib/api/voiceInterview.ts`, `useSpeechSynthesis` | `test_voice_interview_routes.py`, `SpeechAnswerInput.test.tsx`, `useSpeechSynthesis.test.ts` |
| **Dynamic follow-ups** | `follow_up_service.py`, `gemini_follow_up_service.py`; insert on answer submit; `skip` endpoint | Session UI (interview page) | `test_follow_up_service.py`, `test_interview_routes.py` (insert + skip) |
| **Transcript & replay** | `transcript_review_service.py`, `interview_transcript_pdf.py`; bookmarks, practice revision, PDF export | `InterviewTranscriptReviewView.tsx`, `.../history/[sessionId]/review` | `test_transcript_review.py`, `InterviewTranscriptReviewView.test.tsx` (new) |
| **Company prep** | `company_prep_service.py`, catalogue JSON, Gemini content; `start-interview` links session | `app/dashboard/company-prep/page.tsx` | `test_company_prep.py` |

---

## 1 — AI voice interviewer

| ID | Case | Status | Observed / evidence | Expected | Sev |
|----|------|--------|---------------------|----------|-----|
| VO-01 | Append transcript (voice enabled) | PASS | `test_append_transcript_ownership` 200 | Persist lines | — |
| VO-02 | Non-voice session append | PASS | `test_voice_append_rejects_non_voice_session` 422 | Reject | — |
| VO-03 | Cross-user voice API | PASS | `test_voice_transcript_other_user_404` | 404 | — |
| VO-04 | Unauthenticated voice API | PASS | `test_voice_transcript_unauthenticated` 401 | 401 | — |
| VO-05 | Empty-answer clarification | PASS | `test_clarification_empty_answer` (mocked Gemini) | Clarification prompt | — |
| VO-06 | Mic permission granted | NOT TESTED | UI handles `permissionState` in `SpeechAnswerInput.tsx` | Start recognition | — |
| VO-07 | Mic permission denied | NOT TESTED | UI shows denied banner + typed fallback | No crash | Low |
| VO-08 | Unsupported speech recognition | PARTIAL | Vitest mocks `supported: false`; UI copy exists | Typed fallback | — |
| VO-09 | Empty / interrupted speech | NOT TESTED | Metrics from `buildSpeechMetrics` | Partial transcript OK | — |
| VO-10 | Typed fallback | PASS | `SpeechAnswerInput.test.tsx` typing | Works | — |
| VO-11 | Mute / pause / resume | PARTIAL | `VoiceInterviewExperience` skips TTS when muted/paused; `PATCH .../voice/status` exists | State persisted | — |
| VO-12 | TTS / AI audio generation failure | NOT TESTED | Browser `speechSynthesis` only; errors not E2E | Graceful degrade | Med |
| VO-13 | Session completion + transcript persistence | PARTIAL | Repo methods tested via routes; completion in `test_interview_routes` | Survives reload | — |
| VO-14 | Voice session billing / entitlement | PARTIAL | `test_credits.py` charges `voice_interview_session` on create | Pro feature gate | — |
| VO-15 | Audio recording consent / retention | PASS (N/A) | No recording URLs; policy strings in transcript review | No hidden audio storage | — |

---

## 2 — Dynamic follow-up questions

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| FU-01 | Vague answer → follow-up | PASS | Heuristic + `test_maybe_insert_follow_up_inserts_once` | One follow-up | — |
| FU-02 | Strong answer → no follow-up | PASS | `test_maybe_insert_follow_up_skips_strong_answer` | No Gemini call | — |
| FU-03 | Technical / behavioural types | PARTIAL | `build_follow_up_question` preserves category; route test uses technical | Category preserved | — |
| FU-04 | Duplicate prevention | PASS | `test_maybe_insert_follow_up_prevents_duplicate` | No second child | — |
| FU-05 | Follow-up cap | PASS | `follow_up_cap` unit + `test_maybe_insert_follow_up_respects_cap` | Cap enforced | — |
| FU-06 | Skip follow-up | PASS | `test_skip_follow_up_endpoint` + service unit | Index advances | — |
| FU-07 | Submit inserts follow-up (API) | PASS | `test_submit_answer_inserts_follow_up` | Question list grows | — |
| FU-08 | Gemini failure | PASS | `test_maybe_insert_follow_up_gemini_failure_silent` | Continue without FU | — |
| FU-09 | Refresh persistence | NOT TESTED | Stored in Mongo session document | Same questions after reload | — |
| FU-10 | Complete with skipped follow-up | PASS | `test_complete_interview_allows_skipped_follow_up` | Session completes | — |

---

## 3 — Interview transcript and replay

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| TR-01 | Question / answer ordering | PASS | `test_transcript_ordering_and_weak_highlight` | Sequence 1..n | — |
| TR-02 | Weak answer highlight | PASS | Same unit test | `is_weak` true when score low | — |
| TR-03 | Skipped follow-up in timeline | PASS | ordering test item 2 `skipped` | Visible status | — |
| TR-04 | Search (UI) | PASS | `InterviewTranscriptReviewView.test.tsx` filters timeline | Client filter | — |
| TR-05 | Bookmarks API | PASS | `test_transcript_bookmarks_update` | Persist IDs | — |
| TR-06 | Evaluation feedback in review | PARTIAL | `InterviewFeedback` in detail panel; backend embeds evaluation on items | Show coach/scores | — |
| TR-07 | Transcript PDF export | PASS | `test_transcript_export_pdf` | PDF bytes | — |
| TR-08 | Score report PDF | PARTIAL | UI button; separate interview report route (regression via interview tests) | Download | — |
| TR-09 | Audio playback | PASS | `audio_playback_supported: false`; UI policy footer | No fake audio player | — |
| TR-10 | Ownership | PASS | `test_transcript_review_not_found`, delete wrong owner 404 | 404 | — |
| TR-11 | Voice transcript lines in review | PASS | Unit test `voice_transcript` length 1 | Shown in review DTO | — |
| TR-12 | Practice revision | NOT TESTED | API route exists; no dedicated pytest in this pass | Save draft | Low |

---

## 4 — Company-specific preparation

| ID | Case | Status | Observed | Expected | Sev |
|----|------|--------|----------|----------|-----|
| CP-01 | Company search / catalogue | PASS | `test_list_companies_with_auth`, `test_catalogue_lists_google` | List + disclaimer | — |
| CP-02 | Role + experience in create | PASS | `test_create_preparation_persists` | 201 saved | — |
| CP-03 | Question generation (mocked) | PASS | Mocked Gemini in create test | Questions array | — |
| CP-04 | HR + technical categories | PARTIAL | Schema allows `hr`; UI offers all four categories; create test uses technical/coding only | Mixed categories in output | Low |
| CP-05 | Source labelling | PASS | `source_type` / `source_label` on questions + checklist | Visible in API | — |
| CP-06 | Save + reload prep | PASS | `test_get_preparation_ownership` | GET by id | — |
| CP-07 | Cross-user prep | PASS | `test_get_preparation_not_found`, `test_company_prep_other_user_404` | 404 | — |
| CP-08 | Start mock from prep | PASS | `test_start_mock_interview` | Links `interview_session_id` | — |
| CP-09 | Checklist updates | NOT TESTED | Repo + route exist; no pytest in `test_company_prep.py` | PATCH checklist | Low |
| CP-10 | Company prep UI flows | NOT TESTED | Page wired to API | Manual | Med |

---

## Phase D — Integration journey

| Step | Status | Notes |
|------|--------|-------|
| Company select → generate prep → start interview → voice answer → follow-up → complete → transcript review → PDF | **NOT TESTED** (manual/E2E) | Individual APIs/components tested in isolation |

---

## Phase E — Security

| ID | Case | Status |
|----|------|--------|
| SEC-R2-01 | JWT required on voice/transcript/company prep | PASS (401/404 tests) |
| SEC-R2-02 | Cross-user interview / voice / transcript / prep | PASS (`test_release2_security.py` + transcript tests) |
| SEC-R2-03 | User ID spoofing via body | PASS (ownership via `current_user.id` in services) |
| SEC-R2-04 | Microphone consent / audio privacy | PASS — no server-side audio blobs; text-only transcript |
| SEC-R2-05 | Gemini error secret leakage | NOT TESTED (manual spot-check recommended) |

---

## Phase F — Automation added this pass

| File | Change |
|------|--------|
| `backend/tests/test_release2_security.py` | Voice/transcript/prep auth + non-voice 422 |
| `backend/tests/test_follow_up_service.py` | Strong answer skip, cap, Gemini failure |
| `frontend/components/interviews/InterviewTranscriptReviewView.test.tsx` | Search filter + audio policy copy |

---

## Regression (Stage 1 + platform)

Full **202** pytest includes: auth, resumes, Stage 1 career features, billing/credits, institutions, multilingual interviews, coaching, dashboard-related routes.

Frontend: typed interviews (`SpeechAnswerInput`), `InterviewFeedback` (coaching), speech metrics, preparation plan view — all still pass vitest.

---

## Bugs fixed

None confirmed in Release 2 scope during this pass (audit-only + test additions).

---

## Manual testing still required

1. Chrome/Edge/Safari: microphone grant, deny, and unsupported browser paths.
2. Live TTS volume, mute, pause/resume during a real voice session.
3. Full integration: company prep → voice interview → follow-up → transcript review → both PDFs → browser refresh.
4. Gemini live: follow-up quality, voice clarification, company question variety (including **hr** category).
5. Mobile layout for voice controls and transcript review.
6. Verify free vs Pro **voice_interview** entitlement in UI when starting sessions.

---

## Sign-off statement

Release 2 features are **implemented and regression-clean** under mocked AI/speech. Status is **conditional PASS** for backend logic and **BLOCKED / NOT TESTED** for live provider and full E2E flows. Do **not** start Release 3 QA until stakeholders accept the manual checklist above or add Playwright E2E.
