import logging
from uuid import uuid4

from google.genai import types
from pydantic import ValidationError

from core.config.settings import settings
from schemas.company_prep_schema import (
    AI_PRACTICE_QUESTION_DISCLAIMER,
    ChecklistItem,
    CompanyCatalogueEntry,
    CompanyPrepQuestion,
    ExperienceLevel,
    GeminiCompanyPrepPayload,
    PrepCategory,
)
from services.gemini_client import (
    build_gemini_client,
    call_with_transient_retries,
    sanitize_provider_error,
)
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You create company-focused INTERVIEW PRACTICE materials.

Strict rules:
- NEVER claim questions are from real, leaked, or guaranteed company interviews.
- NEVER invent private hiring rounds, interviewer scripts, or internal processes.
- Use only the company public profile and materials provided in the prompt.
- Every practice question must be suitable for mock interview practice only.
- source_type for generated questions must be "ai_generated_practice".
- source_label must state it is AI practice content.
- Checklist items may use catalogue_public only when directly grounded in provided public material summaries; otherwise ai_generated_practice.
- Organise questions into requested categories: technical, hr, coding, behavioural.
- Match difficulty to experience level: junior=beginner, mid=intermediate, senior=advanced.
- Do not reproduce copyrighted question banks verbatim.
"""


class CompanyPrepGeminiError(Exception):
    pass


class CompanyPrepGeminiUnavailableError(CompanyPrepGeminiError):
    pass


def _level_to_difficulty(level: ExperienceLevel) -> str:
    return {"junior": "beginner", "mid": "intermediate", "senior": "advanced"}[level]


def _build_prompt(
    *,
    company: CompanyCatalogueEntry,
    job_role: str,
    experience_level: ExperienceLevel,
    categories: list[PrepCategory],
    user_notes: str | None,
) -> str:
    sources = "\n".join(
        f"- {s.label}: {s.url}" for s in company.verified_public_sources[:6]
    )
    topics = "\n".join(f"- {t}" for t in company.public_prep_topics[:8])
    materials = "\n".join(
        f"- {m.title}: {m.summary[:400]}" for m in company.prep_material[:4]
    )
    notes = (user_notes or "").strip()[:1500]
    return (
        f"Company: {company.name} ({company.industry})\n"
        f"Public summary: {company.public_profile_summary}\n"
        f"Verified public sources:\n{sources or '(none listed)'}\n"
        f"Public prep topics (not interview guarantees):\n{topics or '(none)'}\n"
        f"Catalogue materials:\n{materials or '(none)'}\n\n"
        f"Target job role: {job_role}\n"
        f"Experience level: {experience_level} (difficulty {_level_to_difficulty(experience_level)})\n"
        f"Categories to cover: {', '.join(categories)}\n"
        f"User-provided notes (treat as user_provided context only, may be empty):\n{notes or '(none)'}\n"
    )


def _normalize_payload(payload: GeminiCompanyPrepPayload) -> tuple[list[CompanyPrepQuestion], list[ChecklistItem]]:
    questions: list[CompanyPrepQuestion] = []
    for item in payload.practice_questions:
        questions.append(
            CompanyPrepQuestion(
                id=uuid4().hex,
                question=item.question,
                prep_category=item.prep_category,
                difficulty=item.difficulty,
                relevance=item.relevance,
                evaluates=item.evaluates,
                source_type="ai_generated_practice",
                source_label=item.source_label,
                disclaimer=AI_PRACTICE_QUESTION_DISCLAIMER,
            )
        )
    checklist: list[ChecklistItem] = []
    for item in payload.checklist_items:
        checklist.append(
            ChecklistItem(
                id=uuid4().hex,
                label=item.label,
                prep_category=item.prep_category,
                completed=False,
                source_type=item.source_type,
                source_label=item.source_label,
            )
        )
    return questions, checklist


def generate_company_prep_content(
    *,
    company: CompanyCatalogueEntry,
    job_role: str,
    experience_level: ExperienceLevel,
    categories: list[PrepCategory],
    user_notes: str | None,
) -> tuple[list[CompanyPrepQuestion], list[ChecklistItem]]:
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(
                company=company,
                job_role=job_role,
                experience_level=experience_level,
                categories=categories,
                user_notes=user_notes,
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.35,
                response_mime_type="application/json",
                response_schema=GeminiCompanyPrepPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="gemini_company_prep",
        )
    except Exception as exc:
        logger.warning(
            "Company prep generation failed: %s", sanitize_provider_error(exc)
        )
        raise CompanyPrepGeminiUnavailableError("Generation unavailable.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise CompanyPrepGeminiError("Empty generation response.")

    try:
        parsed = GeminiCompanyPrepPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise CompanyPrepGeminiError("Invalid generation structure.") from exc

    return _normalize_payload(parsed)


def build_catalogue_checklist_seed(
    company: CompanyCatalogueEntry,
) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    for material in company.prep_material[:6]:
        items.append(
            ChecklistItem(
                id=uuid4().hex,
                label=f"Review public material: {material.title}",
                prep_category="general",
                completed=False,
                source_type="catalogue_public",
                source_label=material.source_url or material.title,
            )
        )
    for topic in company.public_prep_topics[:4]:
        items.append(
            ChecklistItem(
                id=uuid4().hex,
                label=f"Research public topic: {topic}",
                prep_category="general",
                completed=False,
                source_type="catalogue_public",
                source_label="Company catalogue (public topics)",
            )
        )
    return items
