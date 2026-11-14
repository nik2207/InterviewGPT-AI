import json
from datetime import datetime, timezone
from io import BytesIO

from models.user_model import UserPublic
from repositories.institution_analytics_repository import InstitutionAnalyticsRepository
from repositories.institution_repository import InstitutionRepository
from services.institution_rbac import MANAGE_ASSIGNMENTS_ROLES, PRIVACY_NOTE
from services.institution_service import InstitutionServiceError, _require_membership

MIN_AGGREGATION_SAMPLE = 5

NOT_HIRING_NOTE = (
    "These metrics describe interview practice and preparation activity only. "
    "They are not hiring decisions or employment outcomes."
)


def _maybe_suppress(sample_size: int, value):
    if sample_size < MIN_AGGREGATION_SAMPLE:
        return None, True
    return value, False


def _filter_dict(filters) -> dict:
    if hasattr(filters, "model_dump"):
        return filters.model_dump()
    return dict(filters or {})


async def resolve_filtered_students(
    repo: InstitutionRepository, institution_id: str, filters
) -> list[str]:
    return await repo.list_filtered_student_user_ids(institution_id, _filter_dict(filters))


async def build_analytics_dashboard(
    inst_repo: InstitutionRepository,
    analytics_repo: InstitutionAnalyticsRepository,
    institution_id: str,
    user: UserPublic,
    filters,
) -> dict:
    await _require_membership(inst_repo, institution_id, user, MANAGE_ASSIGNMENTS_ROLES)
    fdict = _filter_dict(filters)
    user_ids = await inst_repo.list_filtered_student_user_ids(institution_id, fdict)
    sample_size = len(user_ids)

    job_role = fdict.get("job_role") or None
    date_from = fdict.get("date_from")
    date_to = fdict.get("date_to")

    interview = await analytics_repo.aggregate_interview_summary(
        user_ids,
        date_from=date_from,
        date_to=date_to,
        job_role=job_role,
    )
    monthly = await analytics_repo.aggregate_monthly_activity(
        user_ids,
        date_from=date_from,
        date_to=date_to,
        job_role=job_role,
    )
    skills = await analytics_repo.aggregate_skill_distribution(
        user_ids,
        date_from=date_from,
        date_to=date_to,
        job_role=job_role,
    )
    gaps_raw = await analytics_repo.aggregate_common_skill_gaps(
        user_ids,
        date_from=date_from,
        date_to=date_to,
        job_role=job_role,
    )
    prep = await analytics_repo.aggregate_preparation_plan_completion(user_ids)

    assignments = await inst_repo.list_assignments(institution_id)
    if fdict.get("cohort_id"):
        cohort_id = fdict["cohort_id"]
        assignments = [a for a in assignments if a.get("cohort_id") == cohort_id]

    total_assigned = sum(int(a.get("assigned_count", 0)) for a in assignments)
    total_completed = sum(int(a.get("completion_count", 0)) for a in assignments)
    assign_rate = (total_completed / total_assigned) if total_assigned else 0.0

    avg_score, score_suppressed = _maybe_suppress(
        sample_size, interview.get("average_score")
    )
    if avg_score is not None:
        avg_score = round(float(avg_score), 2)

    skill_distribution = skills if sample_size >= MIN_AGGREGATION_SAMPLE else {}
    common_gaps = (
        gaps_raw if sample_size >= MIN_AGGREGATION_SAMPLE else []
    )

    cohort_rows = await inst_repo.list_cohorts(institution_id)
    cohort_comparisons: list[dict] = []
    for cohort in cohort_rows:
        cid = inst_repo.oid_str(cohort["_id"])
        if fdict.get("department") and cohort.get("department") != fdict["department"]:
            continue
        if fdict.get("course") and cohort.get("course") != fdict["course"]:
            continue
        members = await inst_repo.list_cohort_member_user_ids(cid)
        if fdict.get("batch_label"):
            filtered = []
            for uid in members:
                m = await inst_repo.get_membership(institution_id, uid)
                if m and m.get("batch_label") == fdict["batch_label"]:
                    filtered.append(uid)
            members = filtered
        c_sample = len(members)
        c_interview = await analytics_repo.aggregate_interview_summary(
            members, date_from=date_from, date_to=date_to, job_role=job_role
        )
        c_avg, c_sup = _maybe_suppress(c_sample, c_interview.get("average_score"))
        cohort_assignments = [a for a in assignments if a.get("cohort_id") == cid]
        c_assigned = sum(int(a.get("assigned_count", 0)) for a in cohort_assignments)
        c_done = sum(int(a.get("completion_count", 0)) for a in cohort_assignments)
        c_rate = (c_done / c_assigned) if c_assigned else None
        c_rate, rate_sup = _maybe_suppress(c_sample, c_rate)
        cohort_comparisons.append(
            {
                "cohort_id": cid,
                "cohort_name": cohort.get("name", ""),
                "sample_size": c_sample,
                "sessions_completed": c_interview.get("sessions_completed")
                if not c_sup
                else None,
                "average_score": round(float(c_avg), 2) if c_avg is not None else None,
                "assignment_completion_rate": round(c_rate, 3) if c_rate is not None else None,
                "suppressed": c_sup or c_sample == 0,
            }
        )

    period = {
        "from": date_from.isoformat() if isinstance(date_from, datetime) else None,
        "to": date_to.isoformat() if isinstance(date_to, datetime) else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    prep_rate, prep_sup = _maybe_suppress(sample_size, prep.get("average_completion_rate"))

    cards = [
        {
            "label": "Enrolled students",
            "value": sample_size,
            "sample_size": sample_size,
            "suppressed": False,
            "note": "",
        },
        {
            "label": "Active students (sessions in range)",
            "value": interview.get("active_students"),
            "sample_size": sample_size,
            "suppressed": sample_size < MIN_AGGREGATION_SAMPLE,
            "note": "Students with ≥1 completed practice session in the filter range.",
        },
        {
            "label": "Practice sessions",
            "value": interview.get("sessions_completed", 0),
            "sample_size": sample_size,
            "suppressed": False,
            "note": "",
        },
        {
            "label": "Average interview score",
            "value": avg_score,
            "sample_size": sample_size,
            "suppressed": score_suppressed,
            "note": f"Hidden when sample < {MIN_AGGREGATION_SAMPLE}.",
        },
    ]

    return {
        "institution_id": institution_id,
        "reporting_period": period,
        "filters_applied": fdict,
        "disclaimer": PRIVACY_NOTE,
        "not_hiring_outcome_note": NOT_HIRING_NOTE,
        "total_enrolled_students": sample_size,
        "active_students": interview.get("active_students"),
        "practice_sessions_completed": int(interview.get("sessions_completed", 0)),
        "average_interview_score": avg_score if not score_suppressed else None,
        "assignment_completion_rate": round(assign_rate, 3),
        "preparation_plan_completion_rate": prep_rate if not prep_sup else None,
        "skill_distribution": skill_distribution,
        "common_skill_gaps": common_gaps,
        "monthly_activity_trend": [
            {
                **row,
                "average_score": round(float(row["average_score"]), 2)
                if row.get("average_score") is not None
                and sample_size >= MIN_AGGREGATION_SAMPLE
                else None,
            }
            for row in monthly
        ],
        "cohort_comparisons": cohort_comparisons,
        "cards": cards,
    }


async def build_report(
    inst_repo: InstitutionRepository,
    analytics_repo: InstitutionAnalyticsRepository,
    institution_id: str,
    user: UserPublic,
    report_type: str,
    filters,
) -> dict:
    dashboard = await build_analytics_dashboard(
        inst_repo, analytics_repo, institution_id, user, filters
    )
    if report_type == "summary":
        return {
            "type": report_type,
            "dashboard": dashboard,
        }
    if report_type == "cohort_performance":
        return {
            "type": report_type,
            "cohorts": dashboard["cohort_comparisons"],
            "disclaimer": dashboard["disclaimer"],
        }
    if report_type == "participation":
        return {
            "type": report_type,
            "monthly_activity_trend": dashboard["monthly_activity_trend"],
            "active_students": dashboard["active_students"],
            "total_enrolled_students": dashboard["total_enrolled_students"],
        }
    if report_type == "skill_gaps":
        return {
            "type": report_type,
            "skill_distribution": dashboard["skill_distribution"],
            "common_skill_gaps": dashboard["common_skill_gaps"],
            "sample_size": dashboard["total_enrolled_students"],
        }
    if report_type == "assignments":
        rows = await inst_repo.list_assignments(institution_id)
        return {"type": report_type, "assignments": rows}
    raise InstitutionServiceError("Unknown report type.", status_code=400)


def export_report_csv(report: dict) -> str:
    lines = ["InterviewGPT institution report", NOT_HIRING_NOTE, ""]
    if report.get("type") == "summary" and report.get("dashboard"):
        d = report["dashboard"]
        for key in (
            "total_enrolled_students",
            "active_students",
            "practice_sessions_completed",
            "average_interview_score",
            "assignment_completion_rate",
            "preparation_plan_completion_rate",
        ):
            lines.append(f"{key},{d.get(key)}")
    else:
        lines.append(json.dumps(report, default=str))
    return "\n".join(lines) + "\n"


def export_report_pdf(report: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    y = letter[1] - 72
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "InterviewGPT — Institution analytics")
    y -= 20
    pdf.setFont("Helvetica", 9)
    pdf.drawString(72, y, NOT_HIRING_NOTE[:95])
    y -= 24
    body = export_report_csv(report).splitlines()
    for line in body[:40]:
        if y < 72:
            pdf.showPage()
            y = letter[1] - 72
            pdf.setFont("Helvetica", 9)
        pdf.drawString(72, y, line[:100])
        y -= 12
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
