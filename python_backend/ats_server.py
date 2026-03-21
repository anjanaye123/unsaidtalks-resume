"""
UnsaidTalks ATS Scoring Engine (Raw Text) — v2 IMPROVED
Port: 8001
Purpose: Accepts raw resume text from index.html via server.js
         Returns ATS score breakdown + AI-powered resume-specific recommendations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
import httpx
import uvicorn
import os

app = FastAPI(title="UnsaidTalks ATS Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── CONFIG ─────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"


class ResumeTextInput(BaseModel):
    resume_text: str
    job_description: str = ""


# ── ACTION & IMPACT VERBS ───────────────────────────────────
ACTION_VERBS = [
    # Core
    "managed", "led", "developed", "designed", "implemented", "created",
    "improved", "achieved", "increased", "reduced", "optimized", "launched",
    "coordinated", "directed", "spearheaded", "orchestrated", "built",
    "engineered", "analyzed", "streamlined", "executed", "mentored",
    "architected", "collaborated", "facilitated", "negotiated", "supervised",
    "transformed", "pioneered", "established", "delivered", "automated",
    "resolved", "initiated", "maintained", "configured", "deployed",
    "integrated", "researched", "trained", "presented", "published",
    "conceptualized", "restructured", "revamped", "oversaw", "validated",
    "standardized", "monitored", "formulated", "identified", "accelerated",
    # Marketing / Business / Events (non-tech roles)
    "interviewed", "shortlisted", "converted", "contributed", "organized",
    "engaged", "recruited", "onboarded", "promoted", "curated", "drafted",
    "wrote", "authored", "pitched", "secured", "generated", "represented",
    "hosted", "scaled", "sourced", "planned", "executed", "partnered",
    "influenced", "advocated", "communicated", "prepared", "reviewed",
    "evaluated", "assessed", "reported", "tracked", "measured", "drove",
    "expanded", "grew", "acquired", "retained", "supported", "assisted",
    "administered", "allocated", "budgeted", "filed", "documented",
    "scheduled", "liaised", "mobilized", "fundraised", "volunteered"
]

IMPACT_VERBS = [
    "increased", "decreased", "reduced", "improved", "grew", "saved",
    "generated", "delivered", "scaled", "doubled", "tripled", "achieved",
    "exceeded", "boosted", "accelerated", "expanded", "maximized", "minimized",
    "elevated", "amplified", "drove", "multiplied", "surpassed"
]

WEAK_VERBS = [
    "responsible for", "worked on", "helped with", "assisted in",
    "was involved in", "participated in", "contributed to", "did",
    "handled", "dealt with", "took care of"
]

# ── SECTION DETECTION ───────────────────────────────────────
SECTION_PATTERNS = {
    "experience": {
        "keywords": ["experience", "work history", "employment", "professional experience", "work experience"],
        "weight": 25
    },
    "education": {
        "keywords": ["education", "academic", "university", "college", "degree", "bachelor",
                     "master", "b.tech", "b.e", "mba", "ph.d", "diploma", "certification"],
        "weight": 20
    },
    "skills": {
        "keywords": ["skills", "technical skills", "competencies", "proficiency",
                     "technologies", "tools", "frameworks", "programming"],
        "weight": 20
    },
    "summary": {
        "keywords": ["summary", "objective", "profile", "about me",
                     "professional summary", "career objective"],
        "weight": 15
    },
    "contact_email": {
        "keywords": ["@"],
        "weight": 10
    },
    "contact_phone": {
        "keywords": ["phone", "mobile", "contact", "+91", "+1", "+44"],
        "weight": 10
    },
    "projects": {
        "keywords": ["project", "portfolio", "personal project", "academic project"],
        "weight": 8
    },
    "achievements": {
        "keywords": ["achievement", "award", "honor", "recognition", "certified", "certification"],
        "weight": 7
    },
}

# ── SKILL BANK ──────────────────────────────────────────────
SKILL_BANK = [
    # Tech
    "python", "java", "javascript", "typescript", "react", "angular", "vue", "node", "express",
    "mongodb", "sql", "postgresql", "mysql", "aws", "azure", "gcp", "docker", "kubernetes",
    "git", "rest", "graphql", "html", "css", "c++", "c#", "swift", "kotlin", "go", "rust",
    "ruby", "php", "django", "flask", "spring", "tensorflow", "pytorch", "pandas", "numpy",
    "tableau", "power bi", "figma", "sketch", "jira", "agile", "scrum", "seo", "sem",
    "excel", "vlookup", "oracle", "sap", "salesforce", "hubspot", "etl", "spark", "hadoop",
    "looker", "redshift", "snowflake", "terraform", "ansible", "jenkins", "pmp", "six sigma",
    "machine learning", "deep learning", "nlp", "computer vision", "data analysis",
    "data visualization", "data warehousing", "data modeling", "data mining",
    "project management", "product management", "business analysis", "requirements gathering",
    "financial modeling", "forecasting", "budgeting", "ab testing", "google analytics",
    "linux", "windows server", "networking", "cybersecurity", "penetration testing",
    "ci/cd", "devops", "microservices", "api design", "system design", "database design",
    # Marketing & Business
    "digital marketing", "content marketing", "social media", "email marketing",
    "brand management", "market research", "competitor analysis", "campaign management",
    "lead generation", "b2b marketing", "b2c marketing", "copywriting", "content creation",
    "marketing strategy", "growth hacking", "paid advertising", "ppc", "influencer marketing",
    "public relations", "pr", "event management", "event planning", "event coordination",
    "community management", "stakeholder management", "client management", "account management",
    "business development", "partnership management", "vendor management",
    "crm", "customer relationship", "customer success", "customer experience",
    "strategic communication", "corporate communication", "internal communication",
    # Soft & transferable
    "communication", "leadership", "teamwork", "problem solving", "critical thinking",
    "public speaking", "presentation", "negotiation", "time management", "adaptability",
    "analytical thinking", "data driven", "cross functional", "collaboration",
    "program management", "operations", "logistics", "recruitment", "talent acquisition",
    "outreach", "ambassador", "volunteer", "mentoring", "coaching"
]

# ── ROLE ONTOLOGY ───────────────────────────────────────────
ROLE_ONTOLOGY = {
    "Data Analyst": ["sql", "python", "tableau", "power bi", "excel", "statistics", "etl", "vlookup", "data analysis"],
    "Business Analyst": ["requirements gathering", "user stories", "jira", "gap analysis", "business analysis"],
    "Software Engineer": ["data structures", "algorithms", "system design", "ci/cd", "git", "java", "c++", "python"],
    "Frontend Developer": ["react", "angular", "vue", "javascript", "typescript", "css", "html", "ui/ux"],
    "Backend Developer": ["node", "express", "api design", "sql", "mongodb", "microservices", "postgresql"],
    "DevOps Engineer": ["aws", "azure", "gcp", "kubernetes", "docker", "terraform", "jenkins", "linux", "ansible"],
    "Product Manager": ["roadmapping", "agile", "scrum", "product management", "kpis", "jira", "prioritization"],
    "UI/UX Designer": ["figma", "sketch", "wireframing", "prototyping", "user research", "design"],
    "Marketing Specialist": ["seo", "sem", "google analytics", "content strategy", "email marketing", "ppc"],
    "HR / Recruiter": ["ats", "talent sourcing", "interviewing", "onboarding", "hris"],
    "Finance Analyst": ["financial modeling", "forecasting", "budgeting", "excel", "sap", "audit"],
    "Sales / Business Dev": ["lead generation", "salesforce", "negotiation", "b2b", "hubspot", "crm"],
    "Project Manager": ["jira", "risk management", "resource planning", "pmp", "project management"],
    "AI / ML Engineer": ["pytorch", "tensorflow", "machine learning", "deep learning", "nlp", "pandas", "numpy"],
    "Customer Success": ["relationship", "retention", "nps", "churn", "zendesk"],
}


# ══════════════════════════════════════════════════════════════
#  IMPROVED ATS SCORING LOGIC
# ══════════════════════════════════════════════════════════════

def calculate_ats(text: str, job_description: str = "") -> dict:
    lower = text.lower()
    words = lower.split()
    word_count = len(words)

    # ── 1. CLARITY (0–20) ────────────────────────────────────
    clarity = 0

    # Robust bullet detection - includes more symbols and handles multiline start accurately
    bullet_pattern = r'(?m)^\s*[\-\•\*\u2022\u2023\u25e6\u2043\u25cf\u25a0>]\s+\w'
    explicit_bullets = len(re.findall(bullet_pattern, text))
    numbered_bullets = len(re.findall(r'(?m)^\s*\d+[\.\)]\s+[A-Za-z]', text))
    # PDF-extracted: standalone lines that look like bullets but lost symbols
    implicit_bullets = len(re.findall(r'\n[A-Z][^A-Z\n]{15,100}(?:\.|\!|\?|\n|$)', text))
    
    bullets = explicit_bullets + numbered_bullets
    if bullets < 3:
        bullets = max(bullets, implicit_bullets // 3)

    # Improved sentence detection (excluding dates and decimals)
    sentences = len(re.findall(r'(?<![0-9])[.!?](?!\d)(?:\s|$)', text))
    weak_hits = sum(1 for w in WEAK_VERBS if w in lower)

    # Bullet Points (max 10) - More gradual scaling
    if bullets >= 10: clarity += 10
    elif bullets >= 7: clarity += 8
    elif bullets >= 4: clarity += 6
    elif bullets >= 2: clarity += 4
    elif bullets >= 1: clarity += 2

    # Sentence Structure (max 10) - More gradual scaling
    if sentences >= 12: clarity += 10
    elif sentences >= 8:  clarity += 8
    elif sentences >= 5:  clarity += 6
    elif sentences >= 2:  clarity += 4
    
    # Word count penalty: If extremely short (< 100 words), cap the score
    if word_count < 100:
        clarity = min(5, clarity)
    elif word_count < 150:
        clarity = min(15, clarity)

    # Weak language deduction
    clarity -= min(6, weak_hits * 2)
    clarity = max(0, min(20, clarity))

    # ── 2. IMPACT / QUANTIFICATION (0–30) ────────────────────
    impact = 0
    metrics = re.findall(
        r'\b\d+\s*%|\b\d+\+|\$[\d,]+[kKmMbB]?'
        r'|\b\d+\s*(?:million|billion|thousand|hundred|x)\b'
        r'|\b\d+\s*(?:team members?|employees?|clients?|projects?|users?|customers?|people)\b'
        r'|\b(?:revenue|cost|time|efficiency|performance)\s+(?:by\s+)?\d+',
        text, re.IGNORECASE
    )
    # Deduplicate — same number appearing twice shouldn't double-score
    unique_metrics = len(set(m.strip().lower() for m in metrics))
    impact += min(20, unique_metrics * 4)

    found_impact_verbs = [v for v in IMPACT_VERBS if re.search(r'\b' + v + r'\b', lower)]
    impact += min(10, len(found_impact_verbs) * 2)
    impact = min(30, impact)

    # ── ANTI-STUFFING: penalise resumes that spam metrics/verbs without
    #    a real Experience section (keyword-stuffed or fake resumes)
    has_experience = any(kw in lower for kw in ["experience", "work history", "employment", "intern", "engineer", "manager", "analyst", "developer", "coordinator", "specialist"])
    if not has_experience:
        impact = round(impact * 0.4)   # Heavy penalty — numbers without context

    # ── 3. STRUCTURE (0–25) ───────────────────────────────────
    structure_score = 0
    sections_found = []
    for section_name, config in SECTION_PATTERNS.items():
        if any(kw in lower for kw in config["keywords"]):
            structure_score += config["weight"]
            sections_found.append(section_name)

    if re.search(r'[\w.\-]+@[\w.\-]+\.\w+', text):
        structure_score += 5
    if re.search(r'[\+\(]?\d[\d\s\-\(\)]{7,}\d', text):
        structure_score += 5

    structure = min(25, (structure_score / 120) * 25)

    # ── 4. ACTION ORIENTATION (0–25) ─────────────────────────
    found_actions = [v for v in ACTION_VERBS if re.search(r'\b' + v + r'\b', lower)]
    unique_actions = list(set(found_actions))
    action_oriented = min(25, len(unique_actions) * 2 + (5 if len(unique_actions) >= 8 else 0))

    # Anti-stuffing: if no real experience section, penalise action score too
    if not has_experience:
        action_oriented = round(action_oriented * 0.5)

    # ── 5. JD MATCH (0–25, only when JD provided) ────────────
    jd_score = 0
    matched_skills = []
    missing_skills = []

    if job_description:
        jd_lower = job_description.lower()
        jd_skills = [s for s in SKILL_BANK if s in jd_lower]
        total_jd_skills = max(1, len(jd_skills))
        for skill in jd_skills:
            if skill in lower:
                matched_skills.append(skill.upper())
            else:
                missing_skills.append(skill.upper())
        match_ratio = len(matched_skills) / total_jd_skills
        jd_score = round(match_ratio * 25)

    # ── TOTAL ─────────────────────────────────────────────────
    if job_description:
        # With JD: redistribute weights to include JD match
        raw = clarity + impact + structure + action_oriented
        # Scale existing 100-pt score to 75 pts and add jd_score (0–25)
        total = round((raw / 100) * 75 + jd_score)
    else:
        total = round(clarity + impact + structure + action_oriented)

    total = max(5, min(100, total))

    return {
        "ats_score": total,
        "score_breakdown": {
            "clarity": round(clarity * 5),            # scale to 100 for UI
            "impact": round(impact * 3.33),
            "sections": round(structure * 4),
            "action_oriented": round(action_oriented * 4),
            "jd_match": round(jd_score * 4),
        },
        "matched_skills": list(set(matched_skills))[:12],
        "missing_skills": list(set(missing_skills))[:12],
        "word_count": word_count,
        "metrics_found": len(metrics),
        "sections_found": sections_found,
        "weak_verb_hits": weak_hits,
        "unique_action_verbs": len(unique_actions),
    }


# ══════════════════════════════════════════════════════════════
#  AI RECOMMENDATIONS — powered by Claude
# ══════════════════════════════════════════════════════════════

async def generate_ai_recommendations(
    resume_text: str,
    ats_data: dict,
    job_description: str = ""
) -> list[str]:
    """
    Call Claude claude-sonnet-4-20250514 to produce personalised, resume-specific
    recommendations. Falls back to rule-based tips if the API key is absent
    or the request fails.
    """
    if not ANTHROPIC_API_KEY:
        return _rule_based_recommendations(resume_text, ats_data, job_description)

    score = ats_data["ats_score"]
    missing_skills = ats_data.get("missing_skills", [])
    metrics_found = ats_data.get("metrics_found", 0)
    weak_verb_hits = ats_data.get("weak_verb_hits", 0)
    sections_found = ats_data.get("sections_found", [])

    jd_section = f"\nJob Description:\n{job_description[:1500]}" if job_description else ""

    prompt = f"""You are an expert ATS (Applicant Tracking System) resume coach. 
Analyse the resume below and give exactly 5 highly specific, actionable recommendations 
to improve the ATS score (currently {score}/100).

Each recommendation must:
- Reference SPECIFIC content from the resume (actual job titles, skills, phrases found)
- Be concrete and actionable — not generic advice
- Be 1–2 sentences max
- Start with a bold label like **Quantify Results:**, **Weak Verb Fix:**, **Missing Section:**, etc.

Context from automated analysis:
- Metrics / numbers found: {metrics_found} (target ≥ 6)
- Weak phrases detected: {weak_verb_hits}
- Sections present: {', '.join(sections_found) if sections_found else 'unclear'}
- Missing JD keywords: {', '.join(missing_skills[:6]) if missing_skills else 'N/A'}
{jd_section}

Resume Text:
{resume_text[:3000]}

Return ONLY a numbered list 1–5. No preamble, no explanation after the list."""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            # Parse numbered list
            lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
            recs = []
            for line in lines:
                # Strip leading "1. " / "1) " patterns
                clean = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                if clean:
                    recs.append(clean)
            return recs[:5] if recs else _rule_based_recommendations(resume_text, ats_data, job_description)
    except Exception:
        return _rule_based_recommendations(resume_text, ats_data, job_description)


def _rule_based_recommendations(text: str, ats_data: dict, job_description: str = "") -> list[str]:
    """Fallback rule-based recommendations (no API key needed)."""
    lower = text.lower()
    recs = []
    score = ats_data["ats_score"]
    metrics_found = ats_data.get("metrics_found", 0)
    missing_jd = ats_data.get("missing_skills", [])
    sections_found = ats_data.get("sections_found", [])
    weak_hits = ats_data.get("weak_verb_hits", 0)

    if job_description and missing_jd:
        top = missing_jd[:3]
        recs.append(
            f"**Keyword Gap:** Add missing JD keywords — {', '.join(top)} — "
            "to your Skills section so ATS parsers recognise your fit."
        )

    if metrics_found < 4:
        recs.append(
            "**Quantify Results:** You have fewer than 4 measurable achievements. "
            'Replace vague phrases with numbers, e.g. "Reduced load time by 40%" or "Managed team of 8 engineers."'
        )

    if weak_hits > 0:
        recs.append(
            f"**Weak Language:** {weak_hits} weak phrases detected (e.g. 'responsible for', 'worked on'). "
            "Swap these for strong action verbs like Architected, Spearheaded, or Delivered."
        )

    if "summary" not in sections_found:
        recs.append(
            "**Missing Summary:** Add a 3-line Professional Summary at the top of your resume. "
            "It is one of the first sections ATS systems parse and recruiters read."
        )

    if "projects" not in sections_found and score < 75:
        recs.append(
            "**Add Projects:** A Projects section with 2–3 relevant items significantly boosts "
            "keyword density and demonstrates hands-on experience."
        )

    if score < 70:
        recs.append(
            "**Stronger Verbs:** Start every bullet with a power verb — "
            '"Architected," "Spearheaded," "Orchestrated" — to pass action-verb ATS filters.'
        )

    # Detect role and give targeted tip
    for role, skills in ROLE_ONTOLOGY.items():
        if any(s in lower for s in skills):
            missing_ont = [s for s in skills if s not in lower]
            if missing_ont:
                recs.append(
                    f"**Role Tip ({role}):** Add '{missing_ont[0]}' — a standard skill "
                    f"for {role} roles — to pass role-specific ATS keyword filters."
                )
            break

    return recs[:5]


# ══════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.post("/api/analyze-text")
async def analyze_resume_text(data: ResumeTextInput):
    text = data.resume_text
    if not text or len(text.strip()) < 50:
        return {
            "ats_score": 0,
            "score_breakdown": {"clarity": 0, "impact": 0, "sections": 0, "action_oriented": 0, "jd_match": 0},
            "recommendations": ["Please upload a valid resume with sufficient content."],
            "matched_skills": [],
            "missing_skills": [],
        }

    ats_data = calculate_ats(text, data.job_description)
    recommendations = await generate_ai_recommendations(text, ats_data, data.job_description)

    return {
        "ats_score": ats_data["ats_score"],
        "score_breakdown": ats_data["score_breakdown"],
        "recommendations": recommendations,
        "matched_skills": ats_data["matched_skills"],
        "missing_skills": ats_data["missing_skills"],
    }


@app.get("/health")
async def health():
    return {
        "status": "running",
        "service": "UnsaidTalks ATS Engine",
        "port": 8001,
        "ai_recommendations": bool(ANTHROPIC_API_KEY),
    }


if __name__ == "__main__":
    uvicorn.run("ats_server:app", host="0.0.0.0", port=8001, reload=True)