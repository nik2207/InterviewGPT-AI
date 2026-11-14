from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from schemas.interview_schema import TRANSCRIPT_TEXT_DISCLAIMER
from services.transcript_review_service import build_transcript_review


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _wrap(text: str, max_chars: int = 95) -> list[str]:
    words = _truncate(text, 4000).split()
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
    return lines


def _draw(pdf: canvas.Canvas, y: float, lines: list[str], bold: bool = False) -> float:
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
    for line in lines:
        if y < inch:
            pdf.showPage()
            y = letter[1] - inch
            pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        pdf.drawString(0.75 * inch, y, line)
        y -= 14
    return y


def generate_interview_transcript_pdf(document: dict, *, session_id: str) -> bytes:
    review = build_transcript_review(document, session_id=session_id)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    height = letter[1]
    y = height - inch

    y = _draw(pdf, y, ["InterviewGPT — Interview Transcript"], bold=True)
    y = _draw(pdf, y, [f"Role: {_truncate(review.role, 120)}"])
    if review.completed_at:
        label = review.completed_at.strftime("%Y-%m-%d %H:%M UTC")
        y = _draw(pdf, y, [f"Completed: {label}"])
    y = _draw(pdf, y, [_truncate(TRANSCRIPT_TEXT_DISCLAIMER, 400)])
    y -= 8

    for item in review.items:
        heading = f"{item.sequence}. {item.question.question}"
        if item.question.is_follow_up:
            heading += " (follow-up)"
        y = _draw(pdf, y, _wrap(heading), bold=True)

        if item.answer_status == "skipped":
            y = _draw(pdf, y, ["Status: skipped by candidate"])
        elif item.answer and item.answer.answer_text:
            y = _draw(pdf, y, _wrap(f"Answer: {item.answer.answer_text}"))
            if item.timing and item.timing.timing_reliable and item.timing.duration_seconds:
                y = _draw(
                    pdf,
                    y,
                    [
                        f"Duration: {item.timing.duration_seconds:.0f}s · "
                        f"WPM: {item.timing.words_per_minute or '—'}"
                    ],
                )
            elif item.answer.submitted_at:
                ts = item.answer.submitted_at
                if isinstance(ts, datetime):
                    y = _draw(pdf, y, [f"Submitted: {ts.strftime('%Y-%m-%d %H:%M UTC')}"])
            if item.answer.evaluation:
                y = _draw(
                    pdf,
                    y,
                    [
                        f"Score: {item.answer.evaluation.overall_score}/100 — "
                        f"{_truncate(item.answer.evaluation.feedback_summary, 200)}"
                    ],
                )
        elif item.answer_status == "unanswered":
            y = _draw(pdf, y, ["Answer: not submitted"])

        for voice_line in item.voice_transcript:
            y = _draw(
                pdf,
                y,
                _wrap(f"[{voice_line.role}] {voice_line.text}"),
            )
        y -= 6

    pdf.save()
    return buffer.getvalue()
