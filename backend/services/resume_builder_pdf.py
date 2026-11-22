from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from schemas.resume_builder_schema import ResumeBuilderContent, ResumeBuilderTemplate
from services.pdf_fonts import pdf_font_for


def _draw_line(pdf: canvas.Canvas, y: float, text: str, font: str, size: int) -> float:
    selected_font = pdf_font_for(text, bold="Bold" in font)
    if selected_font == "Helvetica" or selected_font == "Helvetica-Bold":
        selected_font = font
    pdf.setFont(selected_font, size)
    if y < inch:
        pdf.showPage()
        y = letter[1] - inch
        pdf.setFont(selected_font, size)
    pdf.drawString(0.75 * inch, y, text[:110])
    return y - (size + 4)


def _bullet_block(pdf: canvas.Canvas, y: float, bullets: list[str], font: str, size: int) -> float:
    for bullet in bullets:
        if not bullet.strip():
            continue
        wrapped = bullet.strip()
        if len(wrapped) > 100:
            wrapped = wrapped[:97] + "..."
        y = _draw_line(pdf, y, f"• {wrapped}", font, size)
    return y


def generate_resume_builder_pdf(
    *,
    title: str,
    template: ResumeBuilderTemplate,
    content: ResumeBuilderContent,
    section_order: list[str],
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    height = letter[1]
    y = height - inch

    body_font = "Helvetica"
    heading_font = "Helvetica-Bold"
    body_size = 10 if template != "compact" else 9
    heading_size = 12 if template != "compact" else 11
    if template == "professional":
        body_font = "Times-Roman"
        heading_font = "Times-Bold"

    name = content.personal_info.full_name.strip() or title
    y = _draw_line(pdf, y, name, heading_font, 16)
    contact_parts = [
        p
        for p in [
            content.personal_info.email,
            content.personal_info.phone,
            content.personal_info.location,
        ]
        if p.strip()
    ]
    if contact_parts:
        y = _draw_line(pdf, y, " | ".join(contact_parts), body_font, body_size)
    links = [
        content.personal_info.linkedin,
        content.personal_info.github,
        content.personal_info.portfolio,
    ]
    links = [link for link in links if link.strip()]
    if links:
        y = _draw_line(pdf, y, " · ".join(links), body_font, body_size - 1)
    y -= 8

    def section_heading(label: str) -> None:
        nonlocal y
        y = _draw_line(pdf, y, label.upper(), heading_font, heading_size)

    sections = {
        "professional_summary": lambda: render_summary(),
        "education": lambda: render_education(),
        "work_experience": lambda: render_experience(content.work_experience, "Experience"),
        "internships": lambda: render_experience(content.internships, "Internships"),
        "technical_skills": lambda: render_skills(),
        "projects": lambda: render_projects(),
        "certifications": lambda: render_certifications(),
        "achievements": lambda: render_achievements(),
        "languages": lambda: render_languages(),
    }

    def render_summary() -> None:
        nonlocal y
        if not content.professional_summary.strip():
            return
        section_heading("Professional Summary")
        y = _draw_line(pdf, y, content.professional_summary.strip(), body_font, body_size)
        y -= 6

    def render_education() -> None:
        nonlocal y
        if not content.education:
            return
        section_heading("Education")
        for edu in content.education:
            line = f"{edu.degree} — {edu.institution}"
            y = _draw_line(pdf, y, line, heading_font, body_size)
            dates = f"{edu.start_date} – {edu.end_date}".strip(" –")
            if dates:
                y = _draw_line(pdf, y, dates, body_font, body_size - 1)
            y = _bullet_block(pdf, y, edu.details, body_font, body_size)
        y -= 4

    def render_experience(entries: list, heading: str) -> None:
        nonlocal y
        if not entries:
            return
        section_heading(heading)
        for entry in entries:
            header = f"{entry.title} — {entry.company}"
            y = _draw_line(pdf, y, header, heading_font, body_size)
            meta = " · ".join(
                p
                for p in [entry.location, f"{entry.start_date} – {entry.end_date}"]
                if p and p.strip(" –")
            )
            if meta:
                y = _draw_line(pdf, y, meta, body_font, body_size - 1)
            y = _bullet_block(pdf, y, entry.bullets, body_font, body_size)
        y -= 4

    def render_skills() -> None:
        nonlocal y
        if not content.technical_skills:
            return
        section_heading("Technical Skills")
        y = _draw_line(pdf, y, ", ".join(content.technical_skills), body_font, body_size)
        y -= 6

    def render_projects() -> None:
        nonlocal y
        if not content.projects:
            return
        section_heading("Projects")
        for project in content.projects:
            y = _draw_line(pdf, y, project.name, heading_font, body_size)
            if project.description.strip():
                y = _draw_line(pdf, y, project.description.strip(), body_font, body_size)
            y = _bullet_block(pdf, y, project.bullets, body_font, body_size)
        y -= 4

    def render_certifications() -> None:
        nonlocal y
        if not content.certifications:
            return
        section_heading("Certifications")
        for cert in content.certifications:
            y = _draw_line(
                pdf,
                y,
                f"{cert.name} — {cert.issuer} ({cert.date})".strip(),
                body_font,
                body_size,
            )
        y -= 4

    def render_achievements() -> None:
        nonlocal y
        if not content.achievements:
            return
        section_heading("Achievements")
        y = _bullet_block(pdf, y, content.achievements, body_font, body_size)
        y -= 4

    def render_languages() -> None:
        nonlocal y
        if not content.languages:
            return
        section_heading("Languages")
        for lang in content.languages:
            y = _draw_line(
                pdf,
                y,
                f"{lang.language} — {lang.proficiency}",
                body_font,
                body_size,
            )
        y -= 4

    for key in section_order:
        renderer = sections.get(key)
        if renderer:
            renderer()

    pdf.save()
    return buffer.getvalue()
