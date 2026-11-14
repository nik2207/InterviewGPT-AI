from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_resume_builder_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from schemas.resume_builder_schema import PersonalInfoSection, ResumeBuilderContent
from services.resume_builder_pdf import generate_resume_builder_pdf
from tests.test_auth_routes import InMemorySessionRepository


class FakeResumeBuilderRepository:
    def __init__(self) -> None:
        self.create_document = AsyncMock()
        self.find_by_id_for_user = AsyncMock(return_value=None)
        self.list_by_user = AsyncMock(return_value=[])
        self.update_document = AsyncMock()
        self.append_version = AsyncMock()
        self.delete_document = AsyncMock(return_value=True)


@pytest.fixture
def builder_client(client: TestClient, sample_user_document: dict):
    repo = FakeResumeBuilderRepository()
    resume_repo = AsyncMock()
    analysis_repo = AsyncMock()

    from app.main import app

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    session_repo = InMemorySessionRepository()

    app.dependency_overrides[get_resume_builder_repository] = lambda: repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])

    yield client, repo, headers, user_id
    app.dependency_overrides.clear()


def _doc(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    content = ResumeBuilderContent().model_dump()
    content["professional_summary"] = "Engineer with five years building APIs."
    return {
        "_id": ObjectId("507f1f77bcf86cd799439050"),
        "user_id": user_id,
        "title": "My Resume",
        "template": "classic",
        "section_order": ["professional_summary", "work_experience"],
        "content": content,
        "versions": [],
        "source_upload_resume_id": None,
        "created_at": now,
        "updated_at": now,
    }


def test_pdf_generation_readable():
    content = ResumeBuilderContent(
        personal_info=PersonalInfoSection(
            full_name="Alex Taylor",
            email="alex@example.com",
            location="Remote",
        ),
        professional_summary="Backend engineer focused on APIs.",
        technical_skills=["Python", "MongoDB"],
    )
    pdf = generate_resume_builder_pdf(
        title="My Resume",
        template="classic",
        content=content,
        section_order=["professional_summary", "technical_skills"],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 200


def test_create_resume_builder(builder_client):
    client, repo, headers, user_id = builder_client
    saved = _doc(user_id)
    repo.create_document = AsyncMock(return_value=saved)

    response = client.post(
        "/api/v1/resume-builder",
        headers=headers,
        json={"title": "My Resume"},
    )
    assert response.status_code == 201
    assert "disclaimer" in response.json()


def test_get_resume_ownership(builder_client):
    client, repo, headers, user_id = builder_client
    repo.find_by_id_for_user = AsyncMock(return_value=_doc(user_id))

    response = client.get(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050",
        headers=headers,
    )
    assert response.status_code == 200


def test_get_resume_not_found(builder_client):
    client, repo, headers, _ = builder_client
    response = client.get(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050",
        headers=headers,
    )
    assert response.status_code == 404


def test_update_persists_draft(builder_client):
    client, repo, headers, user_id = builder_client
    doc = _doc(user_id)
    repo.find_by_id_for_user = AsyncMock(return_value=doc)
    updated = {**doc, "title": "Updated title"}
    repo.update_document = AsyncMock(return_value=updated)

    response = client.patch(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050",
        headers=headers,
        json={"title": "Updated title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"


def test_pdf_download_ownership(builder_client):
    client, repo, headers, user_id = builder_client
    repo.find_by_id_for_user = AsyncMock(return_value=_doc(user_id))

    response = client.get(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050/pdf",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


@patch("services.resume_builder_service.run_resume_builder_ai")
def test_ai_failure_handling(mock_ai, builder_client):
    client, repo, headers, user_id = builder_client
    repo.find_by_id_for_user = AsyncMock(return_value=_doc(user_id))
    from services.gemini_resume_builder_service import ResumeBuilderAiUnavailableError

    mock_ai.side_effect = ResumeBuilderAiUnavailableError("down")

    response = client.post(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050/ai/missing-info",
        headers=headers,
    )
    assert response.status_code == 503


@patch("services.resume_builder_service.run_resume_builder_ai")
def test_ai_proposal_requires_confirmation(mock_ai, builder_client):
    client, repo, headers, user_id = builder_client
    repo.find_by_id_for_user = AsyncMock(return_value=_doc(user_id))
    from services.gemini_resume_builder_service import GeminiResumeAiPayload

    mock_ai.return_value = GeminiResumeAiPayload(
        original_text="Engineer with five years building APIs.",
        improved_text="Backend engineer with five years building APIs.",
        comparison_notes="Added clarity without new facts.",
        missing_information=["Phone number"],
        keyword_suggestions=[],
        ats_formatting_notes=["Summary is concise"],
    )

    response = client.post(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050/ai/improve-summary",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requires_user_confirmation"] is True
    assert body["improved_text"]


def test_resume_ai_system_prompt_forbids_invention():
    from services.gemini_resume_builder_service import SYSTEM_INSTRUCTION

    assert "NEVER invent" in SYSTEM_INSTRUCTION
    assert "improved_text must not add facts" in SYSTEM_INSTRUCTION


def test_save_version_snapshot(builder_client):
    client, repo, headers, user_id = builder_client
    doc = _doc(user_id)
    doc["versions"] = []
    repo.find_by_id_for_user = AsyncMock(return_value=doc)
    versioned = {
        **doc,
        "versions": [
            {
                "version_number": 1,
                "label": "Before edit",
                "content": doc["content"],
                "created_at": datetime.now(timezone.utc),
            }
        ],
    }
    repo.append_version = AsyncMock(return_value=versioned)

    response = client.post(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050/versions",
        headers=headers,
        json={"label": "Before edit"},
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 1


def test_section_order_validation(builder_client):
    client, repo, headers, user_id = builder_client
    repo.find_by_id_for_user = AsyncMock(return_value=_doc(user_id))
    updated = _doc(user_id)
    updated["section_order"] = [
        "technical_skills",
        "professional_summary",
        "work_experience",
    ]
    repo.update_document = AsyncMock(return_value=updated)

    response = client.patch(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050",
        headers=headers,
        json={
            "section_order": [
                "technical_skills",
                "professional_summary",
                "work_experience",
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["section_order"][0] == "technical_skills"


def test_unauthenticated_resume_builder(client: TestClient):
    response = client.post("/api/v1/resume-builder", json={"title": "x"})
    assert response.status_code == 401
