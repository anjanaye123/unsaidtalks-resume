# UnsaidTalks: AI-Powered Resume Ecosystem

## Project Overview

UnsaidTalks is a professional-grade resume orchestration platform that integrates real-time building, ATS-optimized analysis, and AI-driven content refinement. The system is designed to provide candidates with data-backed insights into their resume's performance against industry standards and specific job descriptions.

## Technical Architecture

The platform utilizes a hybrid microservices architecture composed of three distinct services to ensure optimal performance, scalability, and cost-efficiency.

### Service Breakdown

1.  **Node.js Gateway (Port 3001)**: Acts as the primary orchestrator. It manages user sessions, persistence via Supabase, and handles high-level AI interactions using the Google Gemini API.
2.  **Python Resume Builder (Port 8000)**: A dedicated service for real-time resume generation and PDF rendering. It ensures that the document maintains a standard A4 format and industry-compliant structure.
3.  **Python ATS Engine (Port 8001)**: A specialized scoring service that performs deterministic analysis on raw resume text.

### Architecture Rationale: Hybrid Intelligence

A key design decision was the implementation of a hybrid intelligence model. While LLMs (like Gemini) are exceptional at nuance and content generation, relying on them for core scoring metrics is inefficient. 

By offloading the ATS scoring to a deterministic Python engine, we achieve:
- **Reduced Latency**: Scoring results are returned instantly without waiting for LLM inference.
- **Cost Optimization**: Minimized API token usage by only calling the LLM for high-value suggestions and natural language coaching.
- **Consistency**: Deterministic regex-based matching provides reliable, reproducible scores that do not vary between API calls.

## Interactive Resume Builder

The platform includes a sophisticated, real-time resume building interface designed for professional document orchestration.

### Core Features
**Live Preview Synchronization**: Instant visual feedback as data is entered into the editor.
**AI-Guided Content Generation**: Leverages the Gemini AI API to provide contextually relevant summaries and professional achievement bullet points.
**Industry-Standard Templates**: Support for multiple design layouts optimized for modern ATS parsers and human recruiters.
**High-Fidelity PDF Engine**: A specialized rendering pipeline ensures pixel-perfect A4 document generation with consistent typography and spacing.


## ATS Scoring Methodology

The ATS Engine evaluates resumes based on five core pillars, reflecting industry-standard parsing algorithms:

 1. Impact and Quantification (30%)
Analyzes the resume for measurable achievements. The engine scans for numerical data (percentages, currency, scale) and matches them against a database of high-impact verbs (e.g., Spearheaded, Optimized, Delivered).

 2. Job Description (JD) Alignment (25%)
When a JD is provided, the engine performs a gap analysis against a bank of over 150 industry-specific skills. It identifies both matched competencies and missing keywords essential for passing automated filters.

3. Action Orientation (15%)
Evaluates the ratio of active to passive language. Resumes are rewarded for starting bullet points with strong action verbs, which is a key requirement for modern ATS parsers.

 4. Clarity and Readability (15%)
Examines the structural integrity of the document. This includes sentence length, bullet point density, and the absence of "filler" language or weak phrases (e.g., "responsible for").

 5. Section Integrity (15%)
Verification of critical professional headers including Experience, Education, Skills, and Contact Information. Lack of these sections results in significant penalties to the overall score.

## Deployment and Setup

### Prerequisites
- Node.js (v18 or higher)
- Python (3.9 or higher)
- Google Gemini API Key

### Configuration
Environment variables must be configured in a `.env` file at the root directory:

GEMINI_API_KEY=your_api_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

### Execution
The system requires three concurrent terminal sessions:
1. **Node Gateway**: `node server.js`
2. **Resume Builder**: `python python_backend/server.py`
3. **ATS Engine**: `python python_backend/ats_server.py`

---
**Developed for UnsaidTalks Submission**

