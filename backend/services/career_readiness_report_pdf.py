from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from schemas.career_readiness_schema import CareerReadinessReportResponse
from services.pdf_fonts import pdf_font_for


def _truncate(text: str, limit: int = 90) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _draw_heading(pdf: canvas.Canvas, y: float, title: str) -> float:
    pdf.setFont(pdf_font_for(title, bold=True), 13)
    pdf.drawString(0.75 * inch, y, title)
    return y - 0.28 * inch


def _draw_line(pdf: canvas.Canvas, y: float, text: str) -> float:
    if y < inch:
        pdf.showPage()
        y = letter[1] - inch
    line = _truncate(text, 95)
    pdf.setFont(pdf_font_for(line), 10)
    pdf.drawString(0.75 * inch, y, line)
    return y - 14


def generate_career_readiness_pdf(report: CareerReadinessReportResponse) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    y = height - inch

    y = _draw_heading(pdf, y, "InterviewGPT — Career Readiness Report")
    y = _draw_line(pdf, y, f"Target role: {report.target_role}")
    if isinstance(report.generated_at, datetime):
        y = _draw_line(pdf, y, f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    y = _draw_line(pdf, y, report.data_coverage.summary)

    overall = report.overall_readiness
    y = _draw_heading(pdf, y, "Overall readiness")
    if overall.status == "available" and overall.score is not None:
        y = _draw_line(pdf, y, f"Score: {overall.score}/100 — {overall.message}")
    else:
        y = _draw_line(pdf, y, overall.message)

    sections = [
        ("Resume–job alignment", report.resume_job_alignment),
        ("Technical knowledge", report.technical_knowledge),
        ("Answer relevance", report.answer_relevance),
        ("Answer completeness", report.answer_completeness),
        ("Answer structure", report.answer_structure),
    ]
    y = _draw_heading(pdf, y, "Score breakdown")
    for title, section in sections:
        if section.status == "available" and section.score is not None:
            y = _draw_line(
                pdf,
                y,
                f"{title}: {section.score}/100 (n={section.sample_size}) — {section.detail}",
            )
        else:
            y = _draw_line(pdf, y, f"{title}: Not enough practice data")

    comm = report.communication_indicators
    y = _draw_heading(pdf, y, "Communication indicators (speech)")
    if comm.status == "available":
        y = _draw_line(
            pdf,
            y,
            f"Speech answers: {comm.speech_answer_count}; Avg WPM: {comm.average_words_per_minute or '—'}; "
            f"Avg fillers: {comm.average_filler_words or '—'}",
        )
    else:
        y = _draw_line(pdf, y, comm.detail)
    y = _draw_line(pdf, y, comm.disclaimer)

    if report.strongest_skills:
        y = _draw_heading(pdf, y, "Strongest skills")
        for item in report.strongest_skills[:8]:
            y = _draw_line(pdf, y, f"• {item}")

    if report.skills_requiring_improvement:
        y = _draw_heading(pdf, y, "Skills requiring improvement")
        for item in report.skills_requiring_improvement[:8]:
            y = _draw_line(pdf, y, f"• {item}")

    if report.interview_performance_trends:
        y = _draw_heading(pdf, y, "Interview performance trends")
        for point in report.interview_performance_trends[:8]:
            score = point.overall_score if point.overall_score is not None else "—"
            y = _draw_line(pdf, y, f"{point.role}: {score}/100")

    if report.preparation_plan:
        prep = report.preparation_plan
        y = _draw_heading(pdf, y, "Preparation plan")
        y = _draw_line(
            pdf,
            y,
            f"Progress: {prep.progress_percent}% ({prep.tasks_completed}/{prep.tasks_total} tasks)",
        )

    y = _draw_heading(pdf, y, "Recommended next actions")
    for action in report.recommended_next_actions:
        y = _draw_line(pdf, y, f"• {action}")

    y = _draw_heading(pdf, y, "Scoring rules")
    for chunk in report.scoring_rules.split(". "):
        if chunk.strip():
            y = _draw_line(pdf, y, chunk.strip() + ".")

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
