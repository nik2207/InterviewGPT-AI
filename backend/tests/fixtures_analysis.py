from schemas.analysis_schema import (
    GeminiResumeAnalysisResult,
    InterviewQuestionSchema,
    ResumeAnalysisPayloadSchema,
)


def sample_gemini_analysis_result() -> GeminiResumeAnalysisResult:
    questions = [
        InterviewQuestionSchema(
            question=f"Sample interview question number {index}?",
            category="technical",
            difficulty="intermediate",
            relevance="Python",
            evaluates="Problem-solving depth",
        )
        for index in range(1, 11)
    ]
    payload = ResumeAnalysisPayloadSchema(
        professional_summary=(
            "Experienced software engineer with backend and API development focus."
        ),
        skills=["Python", "FastAPI", "MongoDB"],
        experience_analysis="Demonstrates backend engineering experience across multiple roles.",
        projects_analysis="Projects show API design and database integration work.",
        strengths=["Clear backend focus", "Practical project examples"],
        areas_to_improve=["Add measurable outcomes to project bullets"],
        missing_or_unclear_information=["Certifications not mentioned"],
        ats_readability_suggestions=["Use consistent section headings"],
        role_recommendations=["Backend Engineer", "Platform Engineer"],
        skill_gaps=["Cloud platform details not mentioned"],
        interview_questions=questions,
    )
    return GeminiResumeAnalysisResult(analysis=payload)
