import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import os

# ─────────────────────────────────────────────
# Database setup
# ─────────────────────────────────────────────
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client["resume_builder"]


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────
class PersonalInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


class EducationItem(BaseModel):
    school: str = ""
    degree: str = ""
    field: str = ""
    year: str = ""
    gpa: str = ""


class ProjectItem(BaseModel):
    title: str = ""
    description: str = ""
    technologies: str = ""
    link: str = ""


class ResumeCreate(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: str = ""
    skills: List[str] = []
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    projects: List[ProjectItem] = []
    template: Optional[str] = "modern"
    job_description: Optional[str] = ""


class ResumeData(ResumeCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StatusCheckCreate(BaseModel):
    client_name: str


class StatusCheck(StatusCheckCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# ATS Engine
# ─────────────────────────────────────────────
class ATSEngine:

    # ── Action Verbs ──────────────────────────────────────────────────
    ACTION_VERBS = [
        "managed", "led", "developed", "designed", "implemented", "created",
        "improved", "achieved", "increased", "reduced", "optimized", "launched",
        "coordinated", "directed", "spearheaded", "orchestrated", "built",
        "engineered", "analyzed", "streamlined", "executed", "mentored",
        "architected", "collaborated", "facilitated", "negotiated", "supervised",
        "transformed", "pioneered", "established", "delivered", "automated",
        "resolved", "initiated", "maintained", "configured", "deployed",
        "integrated", "researched", "trained", "presented", "published",
        "drove", "scaled", "accelerated", "enhanced", "revamped", "overhauled",
        "standardized", "evaluated", "partnered", "championed", "consolidated",
        "generated", "influenced", "identified", "simplified", "migrated",
        "enabled", "expanded", "decreased", "eliminated", "restructured",
    ]

    # ── Skill Definitions: (display_name, regex_pattern)
    # Every pattern uses word boundaries (\b) so single-letter skills like "R"
    # and short words like "Go", "SQL" will NOT falsely match inside other words.
    SKILL_DEFINITIONS: List[tuple] = [
        # ── Languages ──
        ("Python",             r"\bpython\b"),
        ("Java",               r"\bjava\b(?!script)"),
        ("JavaScript",         r"\bjavascript\b|\bjs\b"),
        ("TypeScript",         r"\btypescript\b|\bts\b"),
        ("C++",                r"\bc\+\+\b|\bcpp\b"),
        ("C#",                 r"\bc#\b|\bcsharp\b"),
        ("Go/Golang",          r"\bgolang\b|\bgo\s+(?:developer|engineer|programming|language)\b"),
        ("Rust",               r"\brust\b(?!\s*(?:free|proof|belt|ed|y\b))"),
        ("Ruby",               r"\bruby\b(?!\s+on\s+rails\b)|\bruby\s+on\s+rails\b"),
        ("PHP",                r"\bphp\b"),
        ("Swift",              r"\bswift\b(?!\s*(?:ly|er|est|ness|UI)\b)|\bswiftui\b"),
        ("Kotlin",             r"\bkotlin\b"),
        ("Scala",              r"\bscala\b"),
        ("R Programming",      r"\bR\s+programming\b|\bRStudio\b|\bR\s+language\b|\bstatistical\s+computing\s+in\s+R\b"),
        ("MATLAB",             r"\bmatlab\b"),
        ("Bash/Shell",         r"\bbash\b|\bshell\s+scripting\b|\bshell\s+script\b"),
        # ── Frontend ──
        ("React",              r"\breact(?:\.js|js)?\b"),
        ("Angular",            r"\bangular(?:js|\s*\d+)?\b"),
        ("Vue.js",             r"\bvue(?:\.js|js)?\b"),
        ("Next.js",            r"\bnext\.js\b|\bnextjs\b"),
        ("Nuxt.js",            r"\bnuxt(?:\.js|js)?\b"),
        ("Svelte",             r"\bsvelte(?:kit)?\b"),
        ("HTML5",              r"\bhtml(?:\s*5)?\b"),
        ("CSS3",               r"\bcss(?:\s*3)?\b"),
        ("Sass/SCSS",          r"\bsass\b|\bscss\b"),
        ("Tailwind CSS",       r"\btailwind(?:\s*css)?\b"),
        ("Bootstrap",          r"\bbootstrap\b"),
        ("Webpack",            r"\bwebpack\b"),
        ("Vite",               r"\bvite\b(?!\s*(?:l|nam|al|min))"),
        ("jQuery",             r"\bjquery\b"),
        # ── Backend ──
        ("Node.js",            r"\bnode(?:\.js|js)?\b"),
        ("Express.js",         r"\bexpress(?:\.js|js)?\b"),
        ("Django",             r"\bdjango\b"),
        ("Flask",              r"\bflask\b"),
        ("FastAPI",            r"\bfastapi\b"),
        ("Spring Boot",        r"\bspring\s*(?:boot|framework|mvc)?\b"),
        ("Laravel",            r"\blaravel\b"),
        ("Ruby on Rails",      r"\bruby\s+on\s+rails\b|\brails\b"),
        ("GraphQL",            r"\bgraphql\b"),
        ("REST API",           r"\brest(?:\s+api|\s+apis|\ful\s+api)?\b"),
        ("Microservices",      r"\bmicroservice[s]?\b"),
        ("gRPC",               r"\bgrpc\b"),
        # ── Databases ──
        ("MongoDB",            r"\bmongodb\b|\bmongo\b"),
        ("SQL",                r"\bsql\b"),
        ("PostgreSQL",         r"\bpostgresql\b|\bpostgres\b"),
        ("MySQL",              r"\bmysql\b"),
        ("Redis",              r"\bredis\b"),
        ("Elasticsearch",      r"\belasticsearch\b|\belastic\s+search\b"),
        ("Cassandra",          r"\bcassandra\b"),
        ("Oracle DB",          r"\boracle\s+(?:db|database|sql)?\b"),
        ("SQLite",             r"\bsqlite\b"),
        ("DynamoDB",           r"\bdynamodb\b"),
        ("Firebase",           r"\bfirebase\b"),
        ("Supabase",           r"\bsupabase\b"),
        # ── Cloud & DevOps ──
        ("AWS",                r"\baws\b|\bamazon\s+web\s+services\b"),
        ("Azure",              r"\bazure\b|\bmicrosoft\s+azure\b"),
        ("GCP",                r"\bgcp\b|\bgoogle\s+cloud\b"),
        ("Docker",             r"\bdocker\b"),
        ("Kubernetes",         r"\bkubernetes\b|\bk8s\b"),
        ("Terraform",          r"\bterraform\b"),
        ("Ansible",            r"\bansible\b"),
        ("Jenkins",            r"\bjenkins\b"),
        ("GitHub Actions",     r"\bgithub\s+actions\b"),
        ("CircleCI",           r"\bcircleci\b"),
        ("Linux",              r"\blinux\b|\bubuntu\b|\bcentos\b|\bdebian\b"),
        ("Nginx",              r"\bnginx\b"),
        ("CI/CD",              r"\bci/cd\b|\bcontinuous\s+integration\b|\bcontinuous\s+(?:deployment|delivery)\b"),
        ("DevOps",             r"\bdevops\b"),
        ("Helm",               r"\bhelm\b(?=\s+(?:chart|release|deploy|upgrade|\d))"),
        ("Prometheus",         r"\bprometheus\b"),
        ("Grafana",            r"\bgrafana\b"),
        # ── Data & ML ──
        ("TensorFlow",         r"\btensorflow\b"),
        ("PyTorch",            r"\bpytorch\b|\btorch\b"),
        ("Scikit-Learn",       r"\bscikit[-\s]?learn\b|\bsklearn\b"),
        ("Pandas",             r"\bpandas\b"),
        ("NumPy",              r"\bnumpy\b"),
        ("Apache Spark",       r"\bapache\s+spark\b|\bpyspark\b|\bspark\s+(?:cluster|streaming|sql|dataframe|job)\b"),
        ("Hadoop",             r"\bhadoop\b|\bhdfs\b"),
        ("Kafka",              r"\bkafka\b|\bapache\s+kafka\b"),
        ("Airflow",            r"\bairflow\b|\bapache\s+airflow\b"),
        ("MLflow",             r"\bmlflow\b"),
        ("Machine Learning",   r"\bmachine\s+learning\b"),
        ("Deep Learning",      r"\bdeep\s+learning\b"),
        ("NLP",                r"\bnlp\b|\bnatural\s+language\s+processing\b"),
        ("Computer Vision",    r"\bcomputer\s+vision\b"),
        ("Data Analysis",      r"\bdata\s+anal(?:ysis|ytics)\b"),
        ("Data Visualization", r"\bdata\s+visuali[sz]ation\b"),
        ("ETL",                r"\betl\b|\bextract[\s,]+transform[\s,]+load\b"),
        ("Tableau",            r"\btableau\b"),
        ("Power BI",           r"\bpower\s+bi\b"),
        ("Looker",             r"\blooker\b(?!\s+studio)|\blooker\s+studio\b"),
        ("Redshift",           r"\bredshift\b|\bamazon\s+redshift\b"),
        ("Snowflake",          r"\bsnowflake\b"),
        ("Databricks",         r"\bdatabricks\b"),
        # ── Tools & Practices ──
        ("Git",                r"\bgit\b"),
        ("GitHub",             r"\bgithub\b"),
        ("GitLab",             r"\bgitlab\b"),
        ("Jira",               r"\bjira\b"),
        ("Confluence",         r"\bconfluence\b"),
        ("Figma",              r"\bfigma\b"),
        ("Adobe XD",           r"\badobe\s+xd\b"),
        ("Agile",              r"\bagile\b"),
        ("Scrum",              r"\bscrum\b"),
        ("Kanban",             r"\bkanban\b"),
        ("TDD",                r"\btdd\b|\btest[\s-]?driven\s+development\b"),
        ("System Design",      r"\bsystem\s+design\b|\bsystems\s+design\b"),
        ("API Design",         r"\bapi\s+design\b|\bapi\s+development\b"),
        # ── Business ──
        ("Microsoft Excel",    r"\bmicrosoft\s+excel\b|\bexcel\s+(?:advanced|vba|macros|pivot|skills)\b|\badvanced\s+excel\b"),
        ("Salesforce",         r"\bsalesforce\b|\bsfdc\b"),
        ("HubSpot",            r"\bhubspot\b"),
        ("SAP",                r"\bsap\b(?:\s+(?:hana|erp|s4|bw|mm|fi|sd|pm))?\b"),
        ("Google Analytics",   r"\bgoogle\s+analytics\b|\bga4\b"),
        ("SEO",                r"\bseo\b|\bsearch\s+engine\s+optimi[sz]ation\b"),
        ("SEM",                r"\bsem\b|\bsearch\s+engine\s+marketing\b"),
        ("Project Management", r"\bproject\s+management\b|\bpmp\b|\bprince2\b"),
        ("Product Management", r"\bproduct\s+management\b|\bproduct\s+manager\b"),
        ("Financial Modeling", r"\bfinancial\s+model(?:ing|s)?\b"),
        ("Forecasting",        r"\bforecasting\b|\bfinancial\s+forecast(?:ing)?\b"),
        ("Budgeting",          r"\bbudget(?:ing|ary)\b"),
        ("A/B Testing",        r"\ba[/\-]?b\s+test(?:ing)?\b|\bsplit\s+test(?:ing)?\b"),
    ]

    # Pre-compile all patterns once at class load time
    _SKILL_PATTERNS: Dict[str, re.Pattern] = {
        name: re.compile(pattern, re.IGNORECASE)
        for name, pattern in SKILL_DEFINITIONS
    }

    # Category maps (used for grouping in JD compare)
    _LANG_SKILLS    = {"Python","Java","JavaScript","TypeScript","C++","C#","Go/Golang","Rust","Ruby","PHP","Swift","Kotlin","Scala","R Programming","MATLAB","Bash/Shell"}
    _FE_SKILLS      = {"React","Angular","Vue.js","Next.js","Nuxt.js","Svelte","HTML5","CSS3","Sass/SCSS","Tailwind CSS","Bootstrap","Webpack","Vite","jQuery"}
    _BE_SKILLS      = {"Node.js","Express.js","Django","Flask","FastAPI","Spring Boot","Laravel","Ruby on Rails","GraphQL","REST API","Microservices","gRPC"}
    _DB_SKILLS      = {"MongoDB","SQL","PostgreSQL","MySQL","Redis","Elasticsearch","Cassandra","Oracle DB","SQLite","DynamoDB","Firebase","Supabase"}
    _CLOUD_SKILLS   = {"AWS","Azure","GCP","Docker","Kubernetes","Terraform","Ansible","Jenkins","GitHub Actions","CircleCI","Linux","Nginx","CI/CD","DevOps","Helm","Prometheus","Grafana"}
    _DATA_SKILLS    = {"TensorFlow","PyTorch","Scikit-Learn","Pandas","NumPy","Apache Spark","Hadoop","Kafka","Airflow","MLflow","Machine Learning","Deep Learning","NLP","Computer Vision","Data Analysis","Data Visualization","ETL","Tableau","Power BI","Looker","Redshift","Snowflake","Databricks"}

    # ── Role Ontology ─────────────────────────────────────────────────
    ROLE_ONTOLOGY: Dict[str, Dict[str, List[str]]] = {
        "software engineer":        {"must_have": ["Git","REST API","System Design"],         "nice_to_have": ["Docker","CI/CD","Microservices","TDD"]},
        "frontend developer":       {"must_have": ["React","JavaScript","CSS3","HTML5"],      "nice_to_have": ["TypeScript","Next.js","Tailwind CSS","Webpack"]},
        "backend developer":        {"must_have": ["SQL","REST API","Git"],                   "nice_to_have": ["Docker","Redis","Microservices","PostgreSQL"]},
        "devops engineer":          {"must_have": ["Docker","Kubernetes","CI/CD","Linux","AWS"], "nice_to_have": ["Terraform","Ansible","Prometheus","Grafana"]},
        "data analyst":             {"must_have": ["SQL","Microsoft Excel","Data Analysis","Python"], "nice_to_have": ["Tableau","Power BI","ETL","Data Visualization"]},
        "data scientist":           {"must_have": ["Python","Machine Learning","Pandas","NumPy"], "nice_to_have": ["TensorFlow","PyTorch","Deep Learning","Apache Spark"]},
        "machine learning engineer":{"must_have": ["Python","Machine Learning","TensorFlow","PyTorch"], "nice_to_have": ["Docker","Kubernetes","MLflow","Apache Spark"]},
        "product manager":          {"must_have": ["Agile","Jira","A/B Testing"],             "nice_to_have": ["Scrum","Google Analytics","Figma"]},
        "ui/ux designer":           {"must_have": ["Figma","Adobe XD"],                       "nice_to_have": ["Tailwind CSS","Agile"]},
        "project manager":          {"must_have": ["Project Management","Agile","Jira"],      "nice_to_have": ["Scrum","Kanban","Budgeting"]},
        "marketing specialist":     {"must_have": ["SEO","Google Analytics"],                 "nice_to_have": ["SEM","A/B Testing","HubSpot"]},
        "finance analyst":          {"must_have": ["Microsoft Excel","Financial Modeling","Forecasting","Budgeting"], "nice_to_have": ["SAP","Power BI"]},
        "business analyst":         {"must_have": ["SQL","Jira","Agile"],                     "nice_to_have": ["Confluence","Tableau","Power BI"]},
    }

    # ─────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _skill_in_text(skill_name: str, text: str) -> bool:
        """Word-boundary regex match — never a plain substring check."""
        pat = ATSEngine._SKILL_PATTERNS.get(skill_name)
        return bool(pat and pat.search(text))

    @staticmethod
    def _all_skills_in_text(text: str) -> List[str]:
        return [name for name in ATSEngine._SKILL_PATTERNS if ATSEngine._skill_in_text(name, text)]

    @staticmethod
    def _extract_resume_text(data: dict) -> str:
        """Concatenate every readable field into one string (original case preserved for regex)."""
        parts: List[str] = []
        for v in data.get("personal", {}).values():
            if v:
                parts.append(str(v))
        if data.get("summary"):
            parts.append(data["summary"])
        for exp in data.get("experience", []):
            parts.append(f"{exp.get('title','')} {exp.get('company','')} {exp.get('description','')}")
        for edu in data.get("education", []):
            parts.append(f"{edu.get('school','')} {edu.get('degree','')} {edu.get('field','')}")
        parts.append(" ".join(data.get("skills", [])))
        for proj in data.get("projects", []):
            parts.append(f"{proj.get('title','')} {proj.get('description','')} {proj.get('technologies','')}")
        return " ".join(p for p in parts if p)

    @staticmethod
    def _detect_role(text: str) -> Optional[str]:
        text_lower = text.lower()
        for role in ATSEngine.ROLE_ONTOLOGY:
            if re.search(r'\b' + re.escape(role) + r'\b', text_lower):
                return role
        return None

    @staticmethod
    def _category_of(skill: str) -> str:
        if skill in ATSEngine._LANG_SKILLS:    return "Programming Languages"
        if skill in ATSEngine._FE_SKILLS:      return "Frontend"
        if skill in ATSEngine._BE_SKILLS:      return "Backend / APIs"
        if skill in ATSEngine._DB_SKILLS:      return "Databases"
        if skill in ATSEngine._CLOUD_SKILLS:   return "Cloud & DevOps"
        if skill in ATSEngine._DATA_SKILLS:    return "Data & ML"
        return "Tools & Practices"

    @staticmethod
    def _group_by_category(skills: List[str]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for s in skills:
            out.setdefault(ATSEngine._category_of(s), []).append(s)
        return out

    # ─────────────────────────────────────────────────────────────────
    # CORE ATS SCORE
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_ats_score(resume_data: dict, job_description: str = "") -> dict:
        resume_text  = ATSEngine._extract_resume_text(resume_data)
        strengths:       List[str]  = []
        actionable_tips: List[Dict] = []

        # ── 1. CONTACT (max 10) ───────────────────────────────────────
        personal       = resume_data.get("personal", {})
        contact_fields = ["name", "email", "phone", "location", "linkedin"]
        filled         = [f for f in contact_fields if personal.get(f, "").strip()]
        missing_c      = [f for f in contact_fields if not personal.get(f, "").strip()]
        contact_score  = round(len(filled) / len(contact_fields) * 10)

        if missing_c:
            actionable_tips.append({
                "category":     "Contact Info",
                "priority":     "high",
                "issue":        f"Missing: {', '.join(missing_c)}.",
                "fix":          f"Add your {missing_c[0]}. ATS parsers index these fields directly.",
                "score_impact": f"+{10 - contact_score} pts",
            })
        else:
            strengths.append("Contact info is complete — all key fields present.")

        # ── 2. SUMMARY (max 15) ───────────────────────────────────────
        summary       = resume_data.get("summary", "").strip()
        summary_score = 0

        if not summary:
            actionable_tips.append({
                "category":     "Summary",
                "priority":     "high",
                "issue":        "No professional summary found.",
                "fix":          "Add 3–4 sentences: [Title] with X years in [domain]. [Achievement with number]. Seeking [role].",
                "score_impact": "+15 pts",
            })
        else:
            words      = len(summary.split())
            has_num    = bool(re.search(r'\d', summary))
            has_role   = bool(ATSEngine._detect_role(summary))

            if words >= 40:
                summary_score += 5
                strengths.append(f"Summary length is solid ({words} words).")
            elif words >= 20:
                summary_score += 3
                actionable_tips.append({
                    "category": "Summary", "priority": "medium",
                    "issue":    f"Summary is only {words} words — aim for 40–60.",
                    "fix":      "Add years of experience, a quantified win, and what role you target.",
                    "score_impact": "+2 pts",
                })
            else:
                actionable_tips.append({
                    "category": "Summary", "priority": "high",
                    "issue":    f"Summary is too short ({words} words).",
                    "fix":      "Write a proper 3–4 sentence summary with title, top achievement, and target role.",
                    "score_impact": "+5 pts",
                })

            if has_num:
                summary_score += 5
                strengths.append("Summary includes a quantified achievement — strong recruiter signal.")
            else:
                actionable_tips.append({
                    "category": "Summary", "priority": "medium",
                    "issue":    "No numbers or percentages in your summary.",
                    "fix":      "Add one metric: 'Reduced load time by 40%', '5+ years of experience', 'Led a team of 8'.",
                    "score_impact": "+5 pts",
                })

            if has_role:
                summary_score += 5
            else:
                actionable_tips.append({
                    "category": "Summary", "priority": "low",
                    "issue":    "Your target job title is not clearly stated in the summary.",
                    "fix":      "Open with your title, e.g., 'Senior Software Engineer with 6 years...'",
                    "score_impact": "+5 pts",
                })

        # ── 3. EXPERIENCE (max 25) ────────────────────────────────────
        experience       = resume_data.get("experience", [])
        experience_score = 0

        if not experience:
            actionable_tips.append({
                "category": "Experience", "priority": "high",
                "issue":    "No work experience found.",
                "fix":      "Add at least 2 roles — full-time, internship, freelance, or contract all qualify.",
                "score_impact": "+25 pts",
            })
        else:
            # 3a. Bullet depth (8 pts)
            total_bullets = sum(
                len([ln for ln in exp.get("description", "").split("\n") if ln.strip()])
                for exp in experience
            )
            avg_bullets = total_bullets / len(experience)
            if avg_bullets >= 4:
                experience_score += 8
                strengths.append("Good bullet depth — roles have detailed descriptions.")
            elif avg_bullets >= 2:
                experience_score += 4
                actionable_tips.append({
                    "category": "Experience", "priority": "medium",
                    "issue":    f"Average {avg_bullets:.1f} bullets per role — aim for 4–5.",
                    "fix":      "Each bullet should be one specific achievement or contribution with a result.",
                    "score_impact": "+4 pts",
                })
            else:
                actionable_tips.append({
                    "category": "Experience", "priority": "high",
                    "issue":    "Experience descriptions are very thin.",
                    "fix":      "Add 4–5 bullet points per role: [Action Verb] + [What you did] + [Result].",
                    "score_impact": "+8 pts",
                })

            # 3b. Action verbs (8 pts)
            exp_combined = " ".join(exp.get("description", "").lower() for exp in experience)
            found_verbs  = [v for v in ATSEngine.ACTION_VERBS if re.search(r'\b' + v + r'\b', exp_combined)]
            verb_ratio   = len(found_verbs) / len(experience)
            if verb_ratio >= 4:
                experience_score += 8
                strengths.append("Strong action verbs used throughout experience.")
            elif verb_ratio >= 2:
                experience_score += 5
                actionable_tips.append({
                    "category": "Experience", "priority": "medium",
                    "issue":    "Some experience bullets are missing action verbs.",
                    "fix":      "Start every bullet with: Built, Led, Reduced, Shipped, Scaled, Designed, Automated.",
                    "score_impact": "+3 pts",
                })
            else:
                actionable_tips.append({
                    "category": "Experience", "priority": "high",
                    "issue":    "Experience reads like a duty list, not an achievement list.",
                    "fix":      "Replace 'responsible for' with verbs like Engineered, Delivered, Spearheaded.",
                    "score_impact": "+8 pts",
                })

            # 3c. Quantified results (9 pts)
            metric_re = re.compile(
                r'\b\d+\s*(?:%|percent|x\b|k\b|m\b|bn\b|million|billion|'
                r'hours?|days?|weeks?|months?|years?|users?|customers?|'
                r'engineers?|employees?|teams?|projects?|releases?)\b'
                r'|\$[\d,]+(?:\s*(?:k|m|bn|million|billion))?'
                r'|\b\d{2,}\+',
                re.IGNORECASE,
            )
            metrics = metric_re.findall(exp_combined)
            if len(metrics) >= 5:
                experience_score += 9
                strengths.append(f"Excellent — {len(metrics)} quantified results found in experience.")
            elif len(metrics) >= 2:
                experience_score += 5
                actionable_tips.append({
                    "category": "Experience", "priority": "medium",
                    "issue":    f"Only {len(metrics)} quantified results — aim for 5+.",
                    "fix":      "'Improved performance' → 'Improved page load by 45%, reducing bounce by 20%'.",
                    "score_impact": "+4 pts",
                })
            else:
                actionable_tips.append({
                    "category": "Experience", "priority": "high",
                    "issue":    "No measurable achievements in experience.",
                    "fix":      "Every role needs numbers: % improvement, $ saved, users impacted, team size, time reduced.",
                    "score_impact": "+9 pts",
                })

        # ── 4. SKILLS (max 15) ────────────────────────────────────────
        skills_list  = resume_data.get("skills", [])
        skills_score = 0
        n_skills     = len(skills_list)
        skills_text  = " ".join(skills_list)

        if n_skills >= 12:
            skills_score += 8
            strengths.append(f"Good skills coverage — {n_skills} skills listed.")
        elif n_skills >= 7:
            skills_score += 5
            actionable_tips.append({
                "category": "Skills", "priority": "medium",
                "issue":    f"Only {n_skills} skills listed — aim for 12–16.",
                "fix":      "Group by category: Languages, Frameworks, Cloud, Tools, Databases.",
                "score_impact": "+3 pts",
            })
        else:
            actionable_tips.append({
                "category": "Skills", "priority": "high",
                "issue":    f"Skills section is sparse ({n_skills} skills).",
                "fix":      "Add 12–16 domain-specific technical skills relevant to your target role.",
                "score_impact": "+8 pts",
            })

        SOFT_FILLER = ["hardworking","passionate","motivated","team player","detail oriented","detail-oriented","fast learner","go-getter","self-starter","results-driven"]
        found_filler = [s for s in SOFT_FILLER if s.lower() in skills_text.lower()]
        if found_filler:
            actionable_tips.append({
                "category": "Skills", "priority": "low",
                "issue":    f"Vague filler detected: {', '.join(found_filler)}.",
                "fix":      "Remove these — ATS ignores them. Replace with specific tools or certifications.",
                "score_impact": "+2 pts",
            })
        else:
            skills_score += 7

        # ── 5. EDUCATION (max 10) ─────────────────────────────────────
        education       = resume_data.get("education", [])
        education_score = 0

        if not education:
            actionable_tips.append({
                "category": "Education", "priority": "medium",
                "issue":    "No education entries found.",
                "fix":      "Add your highest degree. Even incomplete education should be listed with expected year.",
                "score_impact": "+8 pts",
            })
        else:
            full = [e for e in education if e.get("school","").strip() and e.get("degree","").strip()]
            if len(full) == len(education):
                education_score = 10
                strengths.append("Education section is complete.")
            else:
                education_score = 5
                actionable_tips.append({
                    "category": "Education", "priority": "low",
                    "issue":    "Some education entries are missing school or degree.",
                    "fix":      "Complete every entry: school name, degree, field, and graduation year.",
                    "score_impact": "+5 pts",
                })

        # ── 6. PROJECTS (max 10) ──────────────────────────────────────
        projects       = resume_data.get("projects", [])
        projects_score = 0

        if projects:
            projects_score += min(6, len(projects) * 2)
            has_tech  = any(p.get("technologies","").strip() for p in projects)
            has_links = any(p.get("link","").strip() for p in projects)
            if has_tech:
                projects_score += 2
            else:
                actionable_tips.append({
                    "category": "Projects", "priority": "medium",
                    "issue":    "Projects are missing technology stack details.",
                    "fix":      "List every tech used: 'React, Node.js, MongoDB, AWS S3'. These are ATS keywords.",
                    "score_impact": "+2 pts",
                })
            if has_links:
                projects_score += 2
                strengths.append("Projects include GitHub/demo links — great credibility signal.")
            else:
                actionable_tips.append({
                    "category": "Projects", "priority": "low",
                    "issue":    "No GitHub or demo links in projects.",
                    "fix":      "Add a public GitHub repo or live demo URL to each project.",
                    "score_impact": "+2 pts",
                })
        else:
            actionable_tips.append({
                "category": "Projects", "priority": "low",
                "issue":    "No projects listed.",
                "fix":      "Add 2–3 projects — especially important for freshers and career-changers.",
                "score_impact": "+6 pts",
            })

        # ── 7. ROLE ALIGNMENT (max 15) ────────────────────────────────
        detected_role = ATSEngine._detect_role(resume_text)
        role_score    = 0

        if detected_role:
            onto      = ATSEngine.ROLE_ONTOLOGY[detected_role]
            must      = onto["must_have"]
            nice      = onto["nice_to_have"]
            found_m   = [s for s in must if ATSEngine._skill_in_text(s, resume_text)]
            missing_m = [s for s in must if not ATSEngine._skill_in_text(s, resume_text)]
            found_n   = [s for s in nice if ATSEngine._skill_in_text(s, resume_text)]
            coverage  = len(found_m) / max(len(must), 1)
            role_score = round(coverage * 15)

            if found_m:
                strengths.append(f"Core {detected_role.title()} skills confirmed: {', '.join(found_m[:4])}.")
            if missing_m:
                actionable_tips.append({
                    "category": "Role Alignment", "priority": "high",
                    "issue":    f"Missing must-have skills for {detected_role.title()}: {', '.join(missing_m[:4])}.",
                    "fix":      f"Add {', '.join(missing_m[:3])} to Skills and mention them in experience bullets. Non-negotiable for this role.",
                    "score_impact": f"+{15 - role_score} pts",
                })
            if found_n:
                strengths.append(f"Bonus differentiators: {', '.join(found_n[:3])}.")

        # ── 8. JD MATCH (bonus, proportional) ────────────────────────
        jd_score     = 0
        jd_matched:  List[str] = []
        jd_missing:  List[str] = []
        jd_analysis: Dict      = {}

        if (job_description or "").strip():
            jd_skills_present = [
                name for name in ATSEngine._SKILL_PATTERNS
                if ATSEngine._skill_in_text(name, job_description)
            ]
            jd_matched = [s for s in jd_skills_present if ATSEngine._skill_in_text(s, resume_text)]
            jd_missing = [s for s in jd_skills_present if not ATSEngine._skill_in_text(s, resume_text)]

            total_jd  = len(jd_skills_present)
            match_pct = round(len(jd_matched) / total_jd * 100) if total_jd else 0
            jd_score  = round(match_pct / 100 * 25)

            jd_analysis = {
                "match_percentage":  match_pct,
                "total_jd_keywords": total_jd,
                "matched_count":     len(jd_matched),
                "missing_count":     len(jd_missing),
            }

            if jd_missing:
                actionable_tips.append({
                    "category": "JD Match", "priority": "high",
                    "issue":    f"{len(jd_missing)} JD skills absent from your resume.",
                    "fix":      f"Add to Skills (or mention in bullets): {', '.join(jd_missing[:5])}. Mirror JD's exact terms.",
                    "score_impact": f"+{min(15, len(jd_missing) * 2)} pts",
                })
            if match_pct >= 70:
                strengths.append(f"Strong JD match — {match_pct}% of JD skills found in your resume.")
            elif match_pct >= 40:
                strengths.append(f"Moderate JD match ({match_pct}%). Closing the gap will improve your ranking.")

        # ── FINAL SCORE ───────────────────────────────────────────────
        # Base max = 10+15+25+15+10+10+15 = 100. JD is a bonus (up to 10 extra pts).
        base    = contact_score + summary_score + experience_score + skills_score + education_score + projects_score + role_score
        bonus   = round(jd_score * 0.4)
        overall = min(100, max(5, base + bonus))

        priority_order = {"high": 0, "medium": 1, "low": 2}
        actionable_tips.sort(key=lambda t: priority_order.get(t.get("priority","low"), 3))

        return {
            "overall_score": overall,
            "breakdown": {
                "contact":        contact_score,
                "summary":        summary_score,
                "experience":     experience_score,
                "skills":         skills_score,
                "education":      education_score,
                "projects":       projects_score,
                "role_alignment": role_score,
                "jd_match":       jd_score,
            },
            "actionable_tips":   actionable_tips,
            "strengths":         strengths,
            "detected_role":     detected_role,
            "jd_matched_skills": jd_matched[:15],
            "jd_missing_skills": jd_missing[:15],
            "jd_analysis":       jd_analysis,
        }

    # ─────────────────────────────────────────────────────────────────
    # SECTION TIPS  — context-aware, per-role, per-entry
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def get_section_tips(resume_data: dict) -> Dict[str, List[Dict]]:
        tips: Dict[str, List[Dict]] = {
            "summary": [], "experience": [], "skills": [], "education": [], "projects": []
        }
        resume_text = ATSEngine._extract_resume_text(resume_data)

        # ── Summary ──────────────────────────────────────────────────
        summary = resume_data.get("summary", "").strip()
        if not summary:
            tips["summary"].append({
                "tip":     "Add a professional summary",
                "why":     "Recruiters read the summary first. Without it your profile has no hook.",
                "how":     "3–4 sentences: [Title] with X years in [domain]. Known for [achievement with number]. Seeking [role].",
                "example": "Full-Stack Engineer with 4+ years in SaaS. Reduced cloud costs by 30% at XYZ Corp. Seeking senior backend roles.",
            })
        else:
            if len(summary.split()) < 30:
                tips["summary"].append({
                    "tip":     "Expand your summary",
                    "why":     f"At {len(summary.split())} words it won't hold a recruiter's attention.",
                    "how":     "Add years of experience, a key win with a number, and your target role.",
                    "example": "Before: 'Experienced developer looking for opportunities.'\nAfter: 'Software Engineer with 5 years in fintech. Architected a payment service handling $2M/day. Seeking senior backend roles.'",
                })
            if not re.search(r'\d', summary):
                tips["summary"].append({
                    "tip":     "Add at least one number to your summary",
                    "why":     "Quantified summaries are 40% more likely to pass recruiter screening.",
                    "how":     "Use years of experience, team size, revenue impact, or a % improvement.",
                    "example": "'8 years of experience', 'led a team of 12', 'grew ARR by $1.4M'",
                })

        # ── Experience ───────────────────────────────────────────────
        experience = resume_data.get("experience", [])
        if not experience:
            tips["experience"].append({
                "tip":     "Add work experience",
                "why":     "Experience is the most heavily weighted section for recruiters and ATS.",
                "how":     "Include full-time, part-time, internship, freelance, or contract roles.",
                "example": "Junior Backend Dev @ Startup | Jun 2022 – Dec 2022\n• Built Node.js REST APIs handling 50k req/day.\n• Reduced DB query time 60% via index optimisation.",
            })
        else:
            for exp in experience:
                label         = f"'{exp.get('title','Role')} @ {exp.get('company','Company')}'"
                desc          = exp.get("description", "")
                bullets       = [ln.strip() for ln in desc.split("\n") if ln.strip()]
                found_actions = [v for v in ATSEngine.ACTION_VERBS if re.search(r'\b' + v + r'\b', desc.lower())]
                metrics       = re.findall(r'\b\d+\s*(?:%|x\b|k\b|\$)|\$[\d,]+', desc, re.IGNORECASE)

                if len(bullets) < 3:
                    tips["experience"].append({
                        "tip":     f"Expand bullets for {label}",
                        "why":     "Fewer than 3 bullets signals a low-impact role.",
                        "how":     "Write 4–5 bullets: what you owned, tools you used, measurable result.",
                        "example": "• Redesigned CI/CD pipeline (Jenkins → GitHub Actions), cutting deploy time from 40 min to 8 min.",
                    })
                if not found_actions:
                    tips["experience"].append({
                        "tip":     f"Add action verbs to {label}",
                        "why":     "Duty-list bullets score far lower than achievement bullets.",
                        "how":     "Start each bullet: Built, Owned, Drove, Scaled, Reduced, Shipped, Mentored, Automated.",
                        "example": "Before: 'Worked on backend APIs.'\nAfter: 'Engineered RESTful APIs serving 80k daily users with 99.9% uptime.'",
                    })
                if not metrics:
                    tips["experience"].append({
                        "tip":     f"Quantify results in {label}",
                        "why":     "Resumes with 3+ numbers get significantly more interview callbacks.",
                        "how":     "How many users? How much faster? What % improvement? How much money saved?",
                        "example": "'Cut infra costs $12k/month' or 'Grew test coverage from 30% to 85%'",
                    })

        tips["experience"] = tips["experience"][:6]

        # ── Skills ───────────────────────────────────────────────────
        skills    = resume_data.get("skills", [])
        n_skills  = len(skills)
        if n_skills < 8:
            tips["skills"].append({
                "tip":     "Add more technical skills",
                "why":     "ATS systems rank resumes by keyword density vs. the job description.",
                "how":     "List 12–16 skills split by: Languages, Frameworks, Cloud, Databases, Tools.",
                "example": "Python, TypeScript, React, Node.js, PostgreSQL, Redis, AWS, Docker, Git, REST API, Agile, CI/CD",
            })
        if n_skills > 20:
            tips["skills"].append({
                "tip":     "Trim your skills list",
                "why":     "20+ skills looks unfocused and dilutes your core expertise.",
                "how":     "Keep the 12–16 most relevant. Remove outdated or generic ones.",
                "example": "Remove: 'MS Word', 'Windows XP'. Keep: 'Python', 'AWS', 'Kubernetes'.",
            })

        # Suggest moving implied skills into the skills list
        listed_lower        = {s.lower() for s in skills}
        found_in_resume     = ATSEngine._all_skills_in_text(resume_text)
        unlisted_but_used   = [
            s for s in found_in_resume
            if s.lower() not in listed_lower and len(s) > 2
        ][:5]
        if unlisted_but_used:
            tips["skills"].append({
                "tip":     f"Promote implied skills to your Skills section: {', '.join(unlisted_but_used[:3])}",
                "why":     "ATS weights the Skills section more than mentions buried in experience text.",
                "how":     "Explicitly list every technology you used in experience or projects.",
                "example": f"Add '{unlisted_but_used[0]}' directly to the Skills list.",
            })

        # ── Education ────────────────────────────────────────────────
        for edu in resume_data.get("education", []):
            if not edu.get("year","").strip():
                tips["education"].append({
                    "tip":     f"Add graduation year for {edu.get('school','your school')}",
                    "why":     "Missing years cause ATS parsing errors and reduce score.",
                    "how":     "Add the actual or expected graduation year.",
                    "example": "Bachelor of Technology in Computer Science | 2022",
                })

        # ── Projects ─────────────────────────────────────────────────
        projects = resume_data.get("projects", [])
        if not projects:
            tips["projects"].append({
                "tip":     "Add 2–3 projects",
                "why":     "Projects prove hands-on skills — critical for freshers and career-changers.",
                "how":     "Personal, freelance, or open-source projects all count. Include a 2-line description + tech stack + link.",
                "example": "Task Manager | React, Node.js, MongoDB | github.com/you/task-app\n• Supports 500+ concurrent users, deployed on AWS with automated CI/CD.",
            })
        for proj in projects:
            label = f"'{proj.get('title','Project')}'"
            if not proj.get("technologies","").strip():
                tips["projects"].append({
                    "tip":     f"Add tech stack to {label}",
                    "why":     "Tech names inside projects are ATS keywords — they boost matching.",
                    "how":     "List every library, framework, cloud service, and database used.",
                    "example": "Technologies: React, FastAPI, PostgreSQL, Docker, AWS S3, Redis",
                })
            if not proj.get("link","").strip():
                tips["projects"].append({
                    "tip":     f"Add a GitHub/demo link to {label}",
                    "why":     "Engineers reviewing your resume will look for live proof.",
                    "how":     "Push to a public GitHub repo and paste the URL.",
                    "example": "https://github.com/yourhandle/project-name",
                })

        tips["projects"] = tips["projects"][:4]
        return tips

    # ─────────────────────────────────────────────────────────────────
    # JD COMPARISON  — grouped, word-boundary safe, no false positives
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def compare_jd(resume_data: dict, job_description: str) -> Dict:
        if not job_description.strip():
            return {"error": "No job description provided."}

        resume_text = ATSEngine._extract_resume_text(resume_data)

        # Extract skills present in JD using word-boundary regex
        jd_skills = [
            name for name in ATSEngine._SKILL_PATTERNS
            if ATSEngine._skill_in_text(name, job_description)
        ]
        matched = [s for s in jd_skills if ATSEngine._skill_in_text(s, resume_text)]
        missing = [s for s in jd_skills if not ATSEngine._skill_in_text(s, resume_text)]

        total     = len(jd_skills)
        # Match % = matched / total JD skills  (e.g. 3 of 5 JD skills = 60%)
        match_pct = round(len(matched) / total * 100) if total else 0

        matched_grouped = ATSEngine._group_by_category(matched)
        missing_grouped = ATSEngine._group_by_category(missing)

        # Tailored suggestions per missing category
        jd_suggestions: List[Dict] = []
        for area, gap in missing_grouped.items():
            jd_suggestions.append({
                "area":       area,
                "gap":        gap,
                "suggestion": (
                    f"The JD requires {', '.join(gap[:3])} under {area}. "
                    f"If you have this experience, add it explicitly to your Skills section "
                    f"and reference it in a relevant experience bullet or project."
                ),
            })

        # Extract hard requirement phrases from JD
        req_patterns = [
            r'(?:require[sd]?|must\s+have|essential|expected|minimum)[^\n.?]{5,120}',
            r'\b\d\+?\s+years?\s+(?:of\s+)?experience[^\n.?]{0,80}',
            r'proficiency\s+in[^\n.?]{5,80}',
            r'experience\s+(?:with|in)[^\n.?]{5,80}',
        ]
        requirements: List[str] = []
        for pat in req_patterns:
            requirements.extend(re.findall(pat, job_description, re.IGNORECASE))
        requirements = list(dict.fromkeys(r.strip() for r in requirements))[:8]

        # Verdict
        if match_pct >= 75:
            verdict = "Strong Match — Your resume aligns well with this job."
        elif match_pct >= 50:
            verdict = "Moderate Match — A few keyword gaps. Address them to boost your ranking."
        elif match_pct >= 25:
            verdict = "Weak Match — Significant gaps. Tailor your resume carefully before applying."
        else:
            verdict = "Poor Match — Most required skills are absent. Review if this role fits your current profile."

        return {
            "match_percentage":       match_pct,
            "verdict":                verdict,
            "jd_total_keywords":      total,
            "matched_count":          len(matched),
            "missing_count":          len(missing),
            "matched_skills":         matched,
            "missing_skills":         missing,
            "matched_by_category":    matched_grouped,
            "missing_by_category":    missing_grouped,
            "extracted_requirements": requirements,
            "jd_suggestions":         jd_suggestions,
            "quick_wins":             [f"Add '{s}' to your Skills section" for s in missing[:3]],
        }


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    client.close()


app = FastAPI(title="Resume Builder API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import APIRouter
api_router = APIRouter(prefix="/api")


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "Resume Builder API is running"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    obj = StatusCheck(**input.model_dump())
    doc = obj.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.status_checks.insert_one(doc)
    return obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for c in checks:
        if isinstance(c["timestamp"], str):
            c["timestamp"] = datetime.fromisoformat(c["timestamp"])
    return checks


@api_router.post("/resume/calculate-ats")
async def calculate_ats_score(resume: ResumeCreate):
    """Detailed ATS score with actionable tips, strengths, and optional JD breakdown."""
    return ATSEngine.calculate_ats_score(resume.model_dump(), resume.job_description or "")


@api_router.post("/resume/section-tips")
async def get_section_tips(resume: ResumeCreate):
    """
    Context-aware per-section tips — each tip has WHY, HOW, and an EXAMPLE
    derived from the actual resume content, not generic advice.
    """
    return ATSEngine.get_section_tips(resume.model_dump())


@api_router.post("/resume/jd-compare")
async def compare_with_jd(resume: ResumeCreate):
    """
    Deep JD gap analysis: skill match %, grouped matched/missing skills by category,
    extracted JD requirements, and tailored fix suggestions.
    """
    if not (resume.job_description or "").strip():
        raise HTTPException(status_code=400, detail="job_description is required for JD comparison.")
    return ATSEngine.compare_jd(resume.model_dump(), resume.job_description)


@api_router.post("/resume/suggestions")
async def get_all_suggestions(resume: ResumeCreate):
    """
    Single endpoint for the suggestions panel:
    ATS score · breakdown · actionable tips · section tips · JD analysis.
    """
    data = resume.model_dump()
    jd   = resume.job_description or ""
    ats  = ATSEngine.calculate_ats_score(data, jd)
    sec  = ATSEngine.get_section_tips(data)
    jdc  = ATSEngine.compare_jd(data, jd) if jd.strip() else {}

    return {
        "ats_score":       ats["overall_score"],
        "breakdown":       ats["breakdown"],
        "strengths":       ats["strengths"],
        "actionable_tips": ats["actionable_tips"],
        "section_tips":    sec,
        "detected_role":   ats.get("detected_role"),
        "jd_analysis":     jdc,
    }


@api_router.post("/resume/save", response_model=ResumeData)
async def save_resume(resume: ResumeCreate):
    obj = ResumeData(**resume.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.resumes.insert_one(doc)
    return obj


@api_router.get("/resume/{resume_id}", response_model=ResumeData)
async def get_resume(resume_id: str):
    r = await db.resumes.find_one({"id": resume_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    for f in ["created_at", "updated_at"]:
        if isinstance(r[f], str):
            r[f] = datetime.fromisoformat(r[f])
    return r


@api_router.get("/resume", response_model=List[ResumeData])
async def get_all_resumes():
    resumes = await db.resumes.find({}, {"_id": 0}).to_list(100)
    for r in resumes:
        for f in ["created_at", "updated_at"]:
            if isinstance(r[f], str):
                r[f] = datetime.fromisoformat(r[f])
    return resumes


app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)