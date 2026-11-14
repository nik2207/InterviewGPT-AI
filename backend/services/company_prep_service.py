from bson import ObjectId

from repositories.company_prep_repository import CompanyPrepRepository, CompanyPrepRepositoryError
from repositories.interview_repository import InterviewRepository
from schemas.company_prep_schema import (
    COMPANY_PREP_DISCLAIMER,
    ChecklistItem,
    CompanyPrepDetailResponse,
    CompanyPrepListItem,
    CompanyPrepListResponse,
    CompanyPrepQuestion,
    CreateCompanyPrepRequest,
    StartCompanyPrepInterviewRequest,
    StartCompanyPrepInterviewResponse,
    UpdateCompanyPrepChecklistRequest,
)
from schemas.interview_schema import CreateInterviewSessionRequest, CustomInterviewQuestionInput
from services.company_catalogue_service import get_company, list_companies
from services.gemini_company_prep_service import (
    CompanyPrepGeminiError,
    CompanyPrepGeminiUnavailableError,
    build_catalogue_checklist_seed,
    generate_company_prep_content,
)
from services.interview_service import InterviewServiceError, create_interview_session


class CompanyPrepServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _oid_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _merge_checklist(
    catalogue_items: list[ChecklistItem],
    generated: list[ChecklistItem],
) -> list[ChecklistItem]:
    seen: set[str] = set()
    merged: list[ChecklistItem] = []
    for item in catalogue_items + generated:
        key = item.label.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:30]


def _detail_from_document(document: dict) -> CompanyPrepDetailResponse:
    company = get_company(document["company_id"])
    if company is None:
        raise CompanyPrepServiceError("Company catalogue entry missing.", status_code=500)

    questions = [
        CompanyPrepQuestion.model_validate(q) for q in document.get("questions", [])
    ]
    checklist = [
        ChecklistItem.model_validate(c) for c in document.get("checklist", [])
    ]

    return CompanyPrepDetailResponse(
        id=_oid_str(document["_id"]),
        user_id=document["user_id"],
        company=company,
        job_role=document["job_role"],
        experience_level=document["experience_level"],
        categories=document["categories"],
        user_notes=document.get("user_notes"),
        questions=questions,
        checklist=checklist,
        interview_session_id=document.get("interview_session_id"),
        disclaimer=COMPANY_PREP_DISCLAIMER,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


async def search_companies(search: str | None = None):
    return list_companies(search)


async def get_company_detail(company_id: str):
    company = get_company(company_id)
    if company is None:
        raise CompanyPrepServiceError("Company not found.", status_code=404)
    return company


async def create_company_preparation(
    user_id: str,
    payload: CreateCompanyPrepRequest,
    repo: CompanyPrepRepository,
) -> CompanyPrepDetailResponse:
    company = get_company(payload.company_id)
    if company is None:
        raise CompanyPrepServiceError("Company not found in catalogue.", status_code=404)

    catalogue_checklist = build_catalogue_checklist_seed(company)

    try:
        questions, generated_checklist = generate_company_prep_content(
            company=company,
            job_role=payload.job_role.strip(),
            experience_level=payload.experience_level,
            categories=payload.categories,
            user_notes=payload.user_notes,
        )
    except CompanyPrepGeminiUnavailableError as exc:
        raise CompanyPrepServiceError(
            "Question generation is temporarily unavailable.",
            status_code=503,
        ) from exc
    except CompanyPrepGeminiError as exc:
        raise CompanyPrepServiceError(
            "Unable to generate practice content.",
            status_code=422,
        ) from exc

    checklist = _merge_checklist(catalogue_checklist, generated_checklist)

    document = {
        "user_id": user_id,
        "company_id": company.id,
        "company_name": company.name,
        "job_role": payload.job_role.strip(),
        "experience_level": payload.experience_level,
        "categories": payload.categories,
        "user_notes": payload.user_notes,
        "questions": [q.model_dump() for q in questions],
        "checklist": [c.model_dump() for c in checklist],
        "interview_session_id": None,
    }

    try:
        saved = await repo.create_prep(document)
    except CompanyPrepRepositoryError:
        raise CompanyPrepServiceError("Failed to save preparation.", status_code=500) from None

    return _detail_from_document(saved)


async def list_company_preparations(
    user_id: str,
    repo: CompanyPrepRepository,
) -> CompanyPrepListResponse:
    documents = await repo.list_by_user(user_id)
    items: list[CompanyPrepListItem] = []
    for doc in documents:
        items.append(
            CompanyPrepListItem(
                id=_oid_str(doc["_id"]),
                company_id=doc["company_id"],
                company_name=doc.get("company_name", doc["company_id"]),
                job_role=doc["job_role"],
                experience_level=doc["experience_level"],
                categories=doc["categories"],
                question_count=len(doc.get("questions", [])),
                created_at=doc["created_at"],
                interview_session_id=doc.get("interview_session_id"),
            )
        )
    return CompanyPrepListResponse(preparations=items)


async def get_company_preparation(
    user_id: str,
    prep_id: str,
    repo: CompanyPrepRepository,
) -> CompanyPrepDetailResponse:
    document = await repo.find_by_id_for_user(prep_id, user_id)
    if document is None:
        raise CompanyPrepServiceError("Preparation not found.", status_code=404)
    return _detail_from_document(document)


async def update_preparation_checklist(
    user_id: str,
    prep_id: str,
    payload: UpdateCompanyPrepChecklistRequest,
    repo: CompanyPrepRepository,
) -> CompanyPrepDetailResponse:
    document = await repo.find_by_id_for_user(prep_id, user_id)
    if document is None:
        raise CompanyPrepServiceError("Preparation not found.", status_code=404)

    existing_ids = {item["id"] for item in document.get("checklist", [])}
    for item in payload.items:
        if item.id not in existing_ids:
            raise CompanyPrepServiceError(
                "Checklist contains unknown item ids.", status_code=422
            )

    try:
        updated = await repo.update_checklist(
            prep_id,
            user_id,
            [item.model_dump() for item in payload.items],
        )
    except CompanyPrepRepositoryError:
        raise CompanyPrepServiceError("Failed to update checklist.", status_code=500) from None

    if updated is None:
        raise CompanyPrepServiceError("Preparation not found.", status_code=404)
    return _detail_from_document(updated)


def _interview_type_for_categories(categories: list[str]) -> str:
    if categories == ["behavioural"] or categories == ["hr"]:
        return "behavioral"
    if "coding" in categories and "technical" not in categories:
        return "technical"
    if "hr" in categories and len(categories) == 1:
        return "behavioral"
    return "mixed"


def _difficulty_from_experience(level: str) -> str:
    return {"junior": "beginner", "mid": "intermediate", "senior": "advanced"}[level]


async def start_mock_interview_from_prep(
    user_id: str,
    prep_id: str,
    payload: StartCompanyPrepInterviewRequest,
    prep_repo: CompanyPrepRepository,
    interview_repo: InterviewRepository,
    resume_repo,
    analysis_repo,
) -> StartCompanyPrepInterviewResponse:
    document = await prep_repo.find_by_id_for_user(prep_id, user_id)
    if document is None:
        raise CompanyPrepServiceError("Preparation not found.", status_code=404)

    questions_raw = document.get("questions", [])
    if len(questions_raw) < 3:
        raise CompanyPrepServiceError(
            "Not enough practice questions to start a mock interview.",
            status_code=422,
        )

    count = min(payload.question_count, len(questions_raw))
    selected = questions_raw[:count]

    custom_questions = [
        CustomInterviewQuestionInput(
            question=item["question"],
            category=item.get("prep_category", item.get("category", "general")),
            difficulty=item.get("difficulty", _difficulty_from_experience(document["experience_level"])),
            relevance=item.get("relevance", f"{document['company_name']} practice"),
            evaluates=item.get("evaluates", "Role fit"),
        )
        for item in selected
    ]

    create_payload = CreateInterviewSessionRequest(
        role=f"{document['job_role']} — {document['company_name']} prep",
        difficulty=_difficulty_from_experience(document["experience_level"]),
        interview_type=_interview_type_for_categories(document.get("categories", [])),
        resume_id=payload.resume_id,
        question_count=count,
        custom_questions=custom_questions,
        voice_interview_enabled=payload.voice_interview_enabled,
    )

    try:
        session = await create_interview_session(
            user_id=user_id,
            payload=create_payload,
            interview_repo=interview_repo,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
        )
    except InterviewServiceError as exc:
        raise CompanyPrepServiceError(str(exc), status_code=exc.status_code) from exc

    session_id = session.id
    try:
        await prep_repo.link_interview_session(prep_id, user_id, session_id)
    except CompanyPrepRepositoryError:
        pass

    return StartCompanyPrepInterviewResponse(
        preparation_id=prep_id,
        interview_session_id=session_id,
    )
