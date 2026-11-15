# InterviewGPT AI

Full-stack interview coaching platform (Next.js + FastAPI + MongoDB Atlas).

**Deploy on Railway:** see [docs/RAILWAY_DEPLOY.md](docs/RAILWAY_DEPLOY.md).

**Repository:** [github.com/nik2207/InterviewGPT-AI](https://github.com/nik2207/InterviewGPT-AI.git)

InterviewGPT AI
AI-powered interview preparation and career development platform

InterviewGPT AI is a full-stack application designed to help candidates
prepare for technical and behavioral interviews, understand their job
readiness, improve their answers, and organize their career-preparation
journey.

The project uses a Next.js frontend, FastAPI backend, MongoDB
Atlas, and Google Gemini for AI-powered workflows. It supports
Google OAuth authentication and is structured as a monorepo with
separate frontend and backend services.
Repository: https://github.com/nik2207/InterviewGPT-AI

Table of Contents
- Overview
- Features
- Technology Stack
- System Architecture
- Project Structure
- Getting Started
  - Prerequisites
  - Clone the Repository
  - Backend Setup
  - Frontend Setup
- Environment Variables
- Running the Application
- Testing
- API and Health Check
- Deployment
- Security Notes
- Troubleshooting
- Future Scope
- Contributing
- License
Overview
InterviewGPT AI brings multiple interview-preparation and
career-development workflows into one application. Users can prepare
using their resume and target job description, practice interviews,
receive AI-generated feedback, and review their progress.

The platform is intended to support:
- Students preparing for campus placements.
- Fresh graduates preparing for entry-level roles.
- Working professionals preparing for job changes.
- Candidates who want structured practice for technical and behavioral
  interviews.
- Colleges and placement teams that need visibility into student
  preparation activities.
Features
The application is organized around the following feature areas.
Availability of provider-dependent workflows can depend on the
configured API keys and deployment environment.
1. Authentication and User Access
- Google sign-in using OAuth.
- Backend-issued JWT access tokens.
- Protected application routes and authenticated API requests.
- Logout and token revocation support.
2. Resume Analysis and Job Description Matching
- Upload and parse a resume in PDF format.
- Use AI to analyse resume content.
- Compare resume evidence with a target job description.
- Identify relevant, partially matched, and missing or unproven
  skills.
- Use the job match as context for more focused interview preparation.
3. AI Mock Interview Practice
- Create interview sessions based on preparation context.
- Practice technical and behavioral questions.
- Submit answers using typed or supported speech-input workflows.
- Receive AI-generated answer evaluation and improvement feedback.
- Review interview results and previous sessions.
4. Answer Improvement Coach
- Review an interview answer and identify areas to improve.
- Get structured feedback and a suggested stronger response.
- Compare the original answer with the improved version.
- Keep suggestions grounded in the candidate's actual experience;
  users should verify generated content before reusing it.
5. Personalized Preparation and Readiness
- Generate a structured preparation plan.
- Track preparation tasks and progress.
- Review interview performance and areas that need more practice.
- View career-readiness information and reports based on available
  preparation data.
6. Advanced Interview Preparation
- AI-assisted voice-interview workflows where browser and service
  support are available.
- Dynamic follow-up questions based on the candidate's responses.
- Interview transcript and session review.
- Company- and role-oriented preparation workflows.
7. Career Development Tools
- ATS-oriented resume editing and improvement workflows.
- GitHub profile and repository analysis for public profile
  information.
- Job application tracking.
- Multilingual interview-practice workflows where configured.
8. Subscription and Institution Workflows
- Subscription and usage-limit management.
- AI credit and billing workflows.
- Institution, cohort, trainer, and student-oriented workflows.
- Institution-level preparation analytics and administration.
Payment processing and production billing require correctly configured
payment-provider credentials and webhook verification. Do not use live
payment credentials for local testing.
Technology Stack
  Layer                              Technologies
  Frontend                           Next.js 15, React 19, TypeScript
Styling                            Tailwind CSS
Frontend data/API                  Axios
Authentication                     Google OAuth, JWT
Backend                            Python, FastAPI, Uvicorn
Database                           MongoDB Atlas, Motor
AI                                 Google Gemini API (google-genai)
AI workflow orchestration          LangGraph
Resume/PDF processing              PyMuPDF, ReportLab
Backend validation/configuration   Pydantic Settings
Frontend testing                   Vitest, Testing Library
Deployment                         Railway (frontend and backend services)
DF[PDF Processing and Reports]
