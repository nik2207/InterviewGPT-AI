from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from schemas.interview_schema import SCORING_RULES_DESCRIPTION
from services.pdf_fonts import pdf_font_for

MAX_LINE_CHARS = 95
MAX_ANSWER_CHARS = 2500


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _wrap_lines(text: str, max_chars: int = MAX_LINE_CHARS) -> list[str]:
    words = _truncate(text, MAX_ANSWER_CHARS).split()
    if not words:
        return ["—"]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["—"]


def _draw_heading(pdf: canvas.Canvas, y: float, title: str) -> float:
    pdf.setFont(pdf_font_for(title, bold=True), 14)
    pdf.drawString(0.75 * inch, y, title)
    return y - 0.3 * inch


def _draw_body_lines(pdf: canvas.Canvas, y: float, lines: list[str]) -> float:
    for line in lines:
        if y < inch:
            pdf.showPage()
            y = letter[1] - inch
        pdf.setFont(pdf_font_for(line), 10)
        pdf.drawString(0.75 * inch, y, line)
        y -= 14
    return y


def generate_interview_report_pdf(session: dict) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch

    role = _truncate(session.get("role", "Interview"), 120)
    completed_at = session.get("completed_at")
    if isinstance(completed_at, datetime):
        date_label = completed_at.strftime("%Y-%m-%d %H:%M UTC")
    else:
        date_label = "Not completed"

    summary = session.get("summary") or {}
    total_questions = summary.get("total_questions", len(session.get("questions", [])))
    average_score = summary.get("average_score")

    y = _draw_heading(pdf, y, "InterviewGPT — Mock Interview Report")
    pdf.setFont(pdf_font_for(f"Role: {role}"), 10)
    pdf.drawString(0.75 * inch, y, f"Role: {role}")
    y -= 14
    pdf.drawString(0.75 * inch, y, f"Completed: {date_label}")
    y -= 14
    pdf.drawString(0.75 * inch, y, f"Questions: {total_questions}")
    y -= 14
    if average_score is not None:
        pdf.drawString(
            0.75 * inch,
            y,
            f"Overall interview score: {average_score}/100 (mean of per-answer scores)",
        )
    else:
        pdf.drawString(0.75 * inch, y, "Overall interview score: Not available")
    y -= 20

    y = _draw_body_lines(
        pdf,
        y,
        _wrap_lines(
            "Interview-level score = arithmetic mean of each evaluated answer's "
            "weighted dimension score. " + SCORING_RULES_DESCRIPTION
        ),
    )
    y -= 10

    highlights = summary.get("highlights") or []
    if highlights:
        y = _draw_heading(pdf, y, "Strengths")
        for item in highlights[:8]:
            y = _draw_body_lines(pdf, y, _wrap_lines(f"• {item}"))

    focus = summary.get("focus_areas") or []
    if focus:
        y = _draw_heading(pdf, y, "Improvement areas")
        for item in focus[:8]:
            y = _draw_body_lines(pdf, y, _wrap_lines(f"• {item}"))

    questions = {q["id"]: q for q in session.get("questions", [])}
    answers = session.get("answers", [])

    y = _draw_heading(pdf, y, "Question details")
    for index, answer in enumerate(answers, start=1):
        question = questions.get(answer.get("question_id"), {})
        q_text = question.get("question", "Question")
        if y < 1.5 * inch:
            pdf.showPage()
            y = height - inch

        pdf.setFont(pdf_font_for(f"Q{index}", bold=True), 11)
        pdf.drawString(0.75 * inch, y, f"Q{index}")
        y -= 16
        y = _draw_body_lines(pdf, y, _wrap_lines(q_text))

        pdf.setFont(pdf_font_for("Answer:"), 10)
        y = _draw_body_lines(pdf, y, ["Answer:"])
        y = _draw_body_lines(pdf, y, _wrap_lines(answer.get("answer_text", "")))

        evaluation = answer.get("evaluation")
        if evaluation:
            pdf.setFont(pdf_font_for("Score:", bold=True), 10)
            y = _draw_body_lines(
                pdf,
                y,
                [f"Score: {evaluation.get('overall_score', '—')}/100"],
            )
            dims = evaluation.get("dimension_scores") or {}
            dim_line = (
                f"Technical {dims.get('technical_correctness', '—')}/5 · "
                f"Relevance {dims.get('relevance', '—')}/5 · "
                f"Completeness {dims.get('completeness', '—')}/5 · "
                f"Structure {dims.get('answer_structure', '—')}/5"
            )
            y = _draw_body_lines(pdf, y, [dim_line])
            for suggestion in (evaluation.get("improvement_suggestions") or [])[:3]:
                y = _draw_body_lines(pdf, y, _wrap_lines(f"Improve: {suggestion}"))
        else:
            y = _draw_body_lines(pdf, y, ["Evaluation: Not available"])

        speech = answer.get("speech_metrics")
        if speech and speech.get("input_mode") != "typed":
            wpm = speech.get("words_per_minute")
            wpm_label = f"{wpm} WPM" if wpm is not None else "WPM unavailable"
            dur = speech.get("duration_seconds")
            dur_label = f"{dur}s" if dur is not None else "duration unavailable"
            y = _draw_body_lines(
                pdf,
                y,
                [
                    f"Speech metrics (descriptive): {speech.get('word_count', '—')} words, "
                    f"{dur_label}, {wpm_label}, fillers {speech.get('filler_word_count', '—')}"
                ],
            )
        y -= 8

    pdf.save()
    return buffer.getvalue()
