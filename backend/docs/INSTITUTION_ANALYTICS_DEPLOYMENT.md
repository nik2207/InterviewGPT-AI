# Institution analytics (4.4) — deployment notes

## MongoDB indexes

On first request, the API ensures indexes for:

- `institution_memberships` — filter fields (`institution_id`, `status`, `role`, `department`, `course`, `batch_label`)
- `interview_sessions` — `user_id`, `status`, `completed_at` (analytics aggregations)
- `preparation_plans` — `user_id`, `status`
- `institution_audit_log` — `institution_id`, `created_at`

For large deployments, run index creation during a maintenance window if auto-creation on cold start is too slow.

## Environment

- `PLATFORM_SUPER_ADMIN_EMAILS` — optional comma-separated emails with cross-tenant admin read access.
- Institution seat limits are stored on the institution document (`subscription_plan`, `seat_limit`); student AI billing remains on individual `/api/v1/billing` and `/api/v1/credits`.

## Privacy & compliance

- Aggregates suppress sensitive averages when the filtered student sample is below **5** (`MIN_AGGREGATION_SAMPLE` in `institution_analytics_service.py`).
- Reports and PDF/CSV exports include a **not hiring outcome** disclaimer.
- Trainers do not receive student emails; individual metrics require student consent (`consent_share_progress`).

## Performance

- Analytics use MongoDB `$aggregate` pipelines scoped by `user_id $in` lists resolved from membership filters — avoid N+1 per-student interview fetches in new code paths.
- Admin member lists are paginated (`page`, `page_size` ≤ 100).
- No server-side response cache is enabled by default; add CDN/cache only for static export files if needed.

## Operations

- Monitor `institution_audit_log` growth; archive or TTL old rows in Atlas if required.
- After major data backfills, run `db.interview_sessions.reIndex()` only if Atlas support recommends it.
- Frontend institution workspace lives at `/institution/*` and does not replace `/dashboard` personal flows.

## Smoke test after deploy

1. Create institution → verify audit entry `institution_created`.
2. Invite student → accept → dashboard `total_enrolled_students` increases.
3. `GET /api/v1/institutions/{id}/analytics/dashboard` with `department` filter.
4. Export CSV and PDF from `/reports/export`.
5. Confirm non-member receives **403** on dashboard and admin routes.
