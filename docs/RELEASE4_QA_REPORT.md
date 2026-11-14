# Release 4 Commercial QA & Security Report — InterviewGPT AI

**Date:** 2026-11-12  
**Scope:** Subscription plans, usage limits, premium AI credits, Razorpay integration (mocked in CI).

**Payment safety:** All automated payment tests use **dev checkout** or **mocked** Razorpay. No live charges were executed in this pass.

---

## Executive summary

| Area | Result |
|------|--------|
| Backend pytest (full suite) | **226 passed** |
| Frontend vitest | **10 passed** |
| Frontend production build | **PASS** |
| Releases 1–3 regression | Included in full suite — **no new failures** |

**Sign-off:** Commercial logic is **conditionally acceptable** for staging with `BILLING_DEV_CHECKOUT` / mocked webhooks only. **Production payment security is NOT PASSED** until Razorpay **test mode** live checks below are completed.

---

## Security findings (separate)

| ID | Severity | Finding | Status | Recommendation |
|----|----------|---------|--------|----------------|
| **SEC-R4-01** | **HIGH** | `POST /api/v1/credits/refund` is callable by any authenticated user with a valid charge `idempotency_key`, restoring plan allowance or purchased balance without server-only guard. | **Open (design)** | Restrict refunds to internal service paths (feature routes call `safe_refund_ai_operation` only), or require admin scope / signed server token. |
| **SEC-R4-02** | **CRITICAL** (if misconfigured) | `BILLING_DEV_CHECKOUT=true` accepts `dev_mode_signature` for subscription and top-up verify, bypassing HMAC. | **Mitigated by config** | Enforce `BILLING_DEV_CHECKOUT=false` in production; add startup assert in deployment checklist. |
| **SEC-R4-03** | **MEDIUM** | `POST /api/v1/credits/charge` exposes direct debit API to clients (intended for tests); could be abused to burn own credits or probe operations. | **Open (low abuse)** | Document as debug-only or remove from public API surface. |
| **SEC-R4-04** | **LOW** | Webhook handler activates subscriptions using `notes.user_id` from Razorpay entity (standard pattern). Forged activation requires valid webhook HMAC. | **Accepted** | Keep webhook secret rotated; monitor ledger. |
| **SEC-R4-05** | **LOW** | No PAN/card storage observed; only Razorpay IDs in ledger/transactions. | **PASS** | Continue — never log secrets. |
| **SEC-R4-06** | **INFO** | Frontend does not ship `RAZORPAY_KEY_SECRET`; checkout uses public `key_id` only. | **PASS** | — |

**No CRITICAL code defect** was confirmed under correct production configuration. **SEC-R4-02** becomes **CRITICAL** if dev checkout is left enabled in production.

---

## Phase A — Implementation map

| Area | Backend | Frontend | Tests |
|------|---------|----------|-------|
| Plans & limits | `plan_catalog.json`, `entitlement_service.py`, meters on `billing_repository` | `pricing`, `dashboard/billing` | `test_billing_entitlements.py` |
| Razorpay | `razorpay_billing_service.py`, `/billing/checkout|verify|cancel|webhook` | `lib/api/billing.ts` | `test_release4_commercial.py` |
| Credits | `credit_service.py`, `credit_topup_service.py`, `/credits/*` | `CreditBalanceBadge`, `lib/api/credits.ts` | `test_credits.py` |

Entitlements enforced server-side via `require_feature`, `consume_meter`, and `ensure_ai_operation_allowed` on feature routes (Release 1–3 regression).

---

## 1 — Subscription plans & usage limits

| ID | Case | Status | Evidence |
|----|------|--------|----------|
| SUB-01 | Free plan default (no subscription) | PASS | `test_new_user_defaults_to_free_plan`, `effective_plan_id` |
| SUB-02 | Public plan catalog | PASS | `test_plan_catalog_public` |
| SUB-03 | Free meter limit enforcement | PASS | `test_free_plan_usage_limit` |
| SUB-04 | Meter reservation idempotency | PASS | `test_reservation_idempotent` |
| SUB-05 | Checkout dev mode (pro/premium) | PASS | `test_dev_checkout_and_verify`, `test_full_dev_subscribe_cancel_flow` |
| SUB-06 | Checkout rejects `free` | PASS | `test_checkout_rejects_free_plan` 422 |
| SUB-07 | Invalid payment signature (HMAC unit) | PASS | `test_invalid_payment_signature` |
| SUB-08 | Verify wrong subscription for user | PASS | `test_verify_rejects_wrong_subscription` 403 |
| SUB-09 | Dev verify rejects bad signature | PASS | `test_dev_verify_rejects_bad_signature` 400 |
| SUB-10 | Webhook HMAC | PASS | `test_webhook_signature_roundtrip` |
| SUB-11 | Duplicate webhook events | PASS | `test_duplicate_webhook_skipped`, `test_webhook_duplicate_idempotent` |
| SUB-12 | Webhook invalid signature | PASS | `test_webhook_rejects_invalid_signature`, HTTP 400 on `/billing/webhook` |
| SUB-13 | `payment.failed` → `past_due` | PASS | `test_webhook_payment_failed_marks_past_due` |
| SUB-14 | Cancellation (immediate dev) | PASS | `test_full_dev_subscribe_cancel_flow` |
| SUB-15 | Renewal / Razorpay live cycle | NOT TESTED | Requires test-mode dashboard |
| SUB-16 | Refund via Razorpay | NOT TESTED | No refund API wrapper in scope |
| SUB-17 | Expiration after period end | PARTIAL | `effective_plan_id` logic for cancelled + past `current_period_end`; no dedicated test |
| SUB-18 | Pro entitlements after verify | PASS | `test_active_pro_plan`, billing `/me` in flow test |
| SUB-19 | Client cannot set `effective_plan_id` in API body | PASS | Plan from DB on verify, not client override |
| SUB-20 | Failed payment (subscription verify) | NOT TESTED | Live signature failure paths |

---

## 2 — Premium AI credits

| ID | Case | Status | Evidence |
|----|------|--------|----------|
| CR-01 | Public catalog | PASS | `test_credit_catalog_public` |
| CR-02 | Balance auth required | PASS | `test_credit_balance_requires_auth` |
| CR-03 | Initial balance (zero purchased) | PASS | implicit in balance tests |
| CR-04 | Consumption (purchased) | PASS | `test_charge_idempotent_via_api` |
| CR-05 | Idempotent charge | PASS | `test_idempotent_charge`, API duplicate POST |
| CR-06 | Insufficient balance | PASS | `test_insufficient_balance` 402 |
| CR-07 | Refund after charge | PASS | `test_refund_restores_purchased` |
| CR-08 | Refund without charge | PASS | `test_refund_without_prior_charge_returns_404` |
| CR-09 | Concurrent consumption cap | PASS | `test_concurrent_debit_does_not_overspend` |
| CR-10 | Top-up dev checkout + verify | PASS | `test_topup_dev_verify` |
| CR-11 | Top-up verify idempotent | PASS | retry in `test_topup_dev_verify` |
| CR-12 | Top-up order mismatch | PASS | `test_topup_verify_order_mismatch` 400 |
| CR-13 | Plan allowance before purchased | PARTIAL | `try_meter_first` in `ensure_ai_operation_allowed`; resume_analysis meter in charge test |
| CR-14 | Credit expiry lots | NOT TESTED | `expiry_days` in catalog; repository supports `expires_at` |
| CR-15 | Transaction history API | NOT TESTED | Route exists; no dedicated pytest |
| CR-16 | Cross-user idempotency | PARTIAL | 403 if key belongs to other user (service logic) |

---

## Security test matrix (attempted attacks)

| ID | Attack | Status | Result |
|----|--------|--------|--------|
| ATT-01 | Frontend plan spoof (`plan_id: free` checkout) | PASS | 422 / rejected |
| ATT-02 | Verify another user’s subscription id | PASS | 403 mismatch |
| ATT-03 | Forged dev signature when dev mode on | PASS | 400 |
| ATT-04 | Replayed webhook (same event id) | PASS | Second process skipped |
| ATT-05 | Webhook without signature | PASS | 400 |
| ATT-06 | Client-submitted credit balance | PASS | No API to set balance; only verify top-up |
| ATT-07 | Concurrent overspend | PASS | FakeCreditRepository lock tests |
| ATT-08 | Self-refund credit farming | **FAIL (design)** | See **SEC-R4-01** |
| ATT-09 | Replay top-up verify | PASS | Idempotent credit amount |
| ATT-10 | Live Razorpay signature forgery | NOT TESTED | Requires test keys |

---

## Integration (dev mode)

| Step | Status |
|------|--------|
| New user → `/billing/me` free → checkout pro → verify → pro entitlements → cancel | PASS (`test_full_dev_subscribe_cancel_flow`) |
| Top-up → balance → charge AI op | PASS (`test_credits.py` combined) |
| Full journey with real AI feature + credits | NOT TESTED | Manual |

---

## Automation added this pass

| File | Content |
|------|---------|
| `backend/tests/test_release4_commercial.py` | Webhook failure, duplicate webhooks, auth, subscribe/cancel flow |
| `backend/tests/test_credits.py` | Refund without charge, top-up order mismatch |

---

## Regression

**226** pytest tests include auth, resumes, interviews, Releases 1–3 features, institutions. Frontend **10** vitest + **build** PASS.

---

## Live test-mode verification still required

Do **not** mark payment security **PASS** for production until:

1. Razorpay **test mode** checkout with real `key_id` / HMAC verify (not `dev_mode_signature`).
2. Webhook delivery to staging URL with valid `X-Razorpay-Signature` (activation, `payment.failed`, `subscription.cancelled`).
3. Subscription renewal cycle and `past_due` recovery in test mode.
4. Credit top-up order verify with real order/payment ids.
5. Confirm production env: `BILLING_DEV_CHECKOUT=false`, secrets in vault only, webhook secret matches dashboard.
6. Pen-test **SEC-R4-01**: attempt refund after successful AI call via API in staging.

---

## Files changed (QA pass)

- `backend/tests/test_release4_commercial.py` (new)
- `backend/tests/test_credits.py` (extended)
- `docs/RELEASE4_QA_REPORT.md` (this report)

---

## Overall feature status

| Feature | Functional (mocked) | Production payment security |
|---------|---------------------|-----------------------------|
| Subscriptions & limits | **Conditional PASS** | **NOT TESTED (live)** |
| AI credits | **Conditional PASS** | **NOT TESTED (live)** |

Release 5+ QA was **not** started per instruction.
