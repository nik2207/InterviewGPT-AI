import json
from unittest.mock import AsyncMock, MagicMock, patch

from schemas.interview_schema import InterviewLanguageSettings
from services.interview_language_service import resolve_language_settings
from services.gemini_answer_evaluation_service import evaluate_answer_text
from tests.fixtures_interview import custom_questions_payload
from tests.test_interview_routes import _session_doc, interview_client


def test_resolve_language_settings_defaults():
    settings = resolve_language_settings({})
    assert settings.question_language == "en"
    assert settings.answer_language == "en"


def test_resolve_language_settings_from_document():
    doc = {
        "language_settings": {
            "question_language": "hi",
            "answer_language": "hi",
            "feedback_language": "hi",
            "allow_bilingual_answers": True,
            "practice_professional_english": False,
        }
    }
    settings = resolve_language_settings(doc)
    assert settings.question_language == "hi"
    assert settings.allow_bilingual_answers is True


@patch("services.interview_service.localize_interview_questions")
def test_create_interview_persists_hindi_language(mock_localize, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["language_settings"] = {
        "question_language": "hi",
        "answer_language": "hi",
        "feedback_language": "hi",
        "allow_bilingual_answers": False,
        "practice_professional_english": False,
    }
    mock_localize.return_value = [
        {
            "id": "q1",
            "question": "आप Python में async कैसे समझाते हैं?",
            "category": "technical",
            "difficulty": "intermediate",
            "relevance": "Python",
            "evaluates": "Depth",
        },
        {
            "id": "q2",
            "question": "प्रश्न 2?",
            "category": "technical",
            "difficulty": "intermediate",
            "relevance": "Python",
            "evaluates": "Depth",
        },
        {
            "id": "q3",
            "question": "प्रश्न 3?",
            "category": "technical",
            "difficulty": "intermediate",
            "relevance": "Python",
            "evaluates": "Depth",
        },
    ]
    interview_repo.create_session = AsyncMock(return_value=doc)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "custom_questions": custom_questions_payload(3),
            "language": {
                "question_language": "hi",
                "answer_language": "hi",
                "feedback_language": "hi",
                "allow_bilingual_answers": False,
                "practice_professional_english": False,
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["language_settings"]["question_language"] == "hi"
    mock_localize.assert_called_once()
    saved = interview_repo.create_session.await_args.args[0]
    assert saved["language_settings"]["question_language"] == "hi"


def test_get_session_backward_compatible_language(interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    session_id = str(doc["_id"])

    response = client.get(f"/api/v1/interviews/{session_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["language_settings"]["question_language"] == "en"


@patch(
    "services.gemini_answer_evaluation_service.call_with_transient_retries",
    side_effect=lambda fn, **kwargs: fn(),
)
@patch("services.gemini_answer_evaluation_service.build_gemini_client")
@patch("services.gemini_answer_evaluation_service.get_gemini_api_key", return_value="key")
@patch("services.gemini_answer_evaluation_service.get_gemini_model", return_value="gemini-test")
def test_evaluate_answer_hindi_language_in_prompt(
    mock_model, mock_key, mock_client, _retry
):
    response = MagicMock()
    response.text = json.dumps(
        {
            "dimension_scores": {
                "technical_correctness": 4,
                "relevance": 4,
                "completeness": 4,
                "answer_structure": 4,
            },
            "strengths": ["सही दिशा"],
            "missing_concepts": [],
            "improvement_suggestions": ["उदाहरण जोड़ें"],
            "feedback_summary": "अच्छी शुरुआत।",
            "language_fluency_feedback": "वाक्य संरचना सुधार योग्य है।",
            "improvement_coach": {
                "missing_important_points": [],
                "incorrect_or_unclear": [],
                "relevance_to_question": "प्रश्न से जुड़ा।",
                "improved_example_answer": "REST API शुरू में परिभाषित करें।",
                "why_example_is_stronger": "स्पष्ट संरचना।",
                "concepts_to_revise": [],
                "follow_up_practice_question": "AsyncIO बताइए?",
                "action_to_take": "एक प्रोजेक्ट उदाहरण याद करें।",
                "star_assessment": None,
            },
        }
    )
    mock_client.return_value.models.generate_content.return_value = response

    result = evaluate_answer_text(
        role="Engineer",
        question="Async Python कैसे काम करता है?",
        category="technical",
        evaluates="Technical depth",
        answer_text="asyncio event loop tasks चलाता है।",
        language_settings=InterviewLanguageSettings(
            question_language="hi",
            answer_language="hi",
            feedback_language="hi",
            allow_bilingual_answers=True,
        ),
    )
    assert result.language_fluency_feedback
    call_kwargs = mock_client.return_value.models.generate_content.call_args.kwargs
    system = call_kwargs["config"].system_instruction
    assert "Hindi" in system
    assert "language_fluency_feedback" in system


@patch("services.interview_service.localize_interview_questions")
def test_english_session_skips_localization(mock_localize, interview_client):
    client, interview_repo, headers, user_id = interview_client
    interview_repo.create_session = AsyncMock(return_value=_session_doc(user_id))

    client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "custom_questions": custom_questions_payload(3),
        },
    )
    mock_localize.assert_not_called()


@patch("services.interview_service.localize_interview_questions")
def test_create_interview_marathi_triggers_localization(mock_localize, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["language_settings"] = {
        "question_language": "mr",
        "answer_language": "mr",
        "feedback_language": "mr",
        "allow_bilingual_answers": True,
        "practice_professional_english": False,
    }
    mock_localize.return_value = custom_questions_payload(3)
    interview_repo.create_session = AsyncMock(return_value=doc)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Developer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "custom_questions": custom_questions_payload(3),
            "language": {
                "question_language": "mr",
                "answer_language": "mr",
                "feedback_language": "mr",
                "allow_bilingual_answers": True,
                "practice_professional_english": False,
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["language_settings"]["question_language"] == "mr"
    mock_localize.assert_called_once()
