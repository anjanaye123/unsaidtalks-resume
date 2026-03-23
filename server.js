import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { GoogleGenerativeAI } from '@google/generative-ai';
import dotenv from 'dotenv';
import { v4 as uuidv4 } from 'uuid';
import { createClient } from '@supabase/supabase-js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
if (!GEMINI_API_KEY) {
  console.error('❌ GEMINI_API_KEY is required in .env file');
  process.exit(1);
}

const SUPABASE_URL = process.env.SUPABASE_URL
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);

// ── GLOBAL CAREER ONTOLOGY (15+ ROLES) ──────────────────────────
const GLOBAL_CAREER_ONTOLOGY = {
  "Data Analyst": { must_haves: ["SQL", "Python", "Tableau", "Power BI", "Excel", "Statistics", "ETL", "VLOOKUP"], advice: "Focus on data storytelling and quantifying business impact." },
  "Business Analyst": { must_haves: ["Requirements Gathering", "User Stories", "BPMN", "Jira", "Gap Analysis", "Stakeholder Mgmt"], advice: "Highlight your ability to bridge the gap between business needs and technical solutions." },
  "Software Engineer": { must_haves: ["Data Structures", "Algorithms", "System Design", "CI/CD", "Testing", "Git", "Java", "C++"], advice: "Focus on scalability, performance optimization, and clean code." },
  "Frontend Developer": { must_haves: ["React", "Angular", "Vue", "JavaScript", "ES6", "CSS", "UI/UX", "Web Performance"], advice: "Showcase visual excellence and user experience focus." },
  "Backend Developer": { must_haves: ["Node.js", "Express", "API Design", "SQL", "NoSQL", "Microservices", "Security"], advice: "Emphasize security, database efficiency, and system architecture." },
  "DevOps Engineer": { must_haves: ["AWS", "Azure", "GCP", "Kubernetes", "Docker", "Terraform", "Jenkins", "Linux"], advice: "Highlight automation and infrastructure-as-code expertise." },
  "Product Manager": { must_haves: ["Roadmapping", "Agile", "Scrum", "Product Discovery", "KPIs", "Prioritization"], advice: "Focus on 'The Why' behind products and measurable user growth." },
  "UI/UX Designer": { must_haves: ["Figma", "Adobe XD", "Sketch", "Wireframing", "Prototyping", "User Research", "Design"], advice: "Portfolio links are critical; focus on problem-solving through design." },
  "Marketing Specialist": { must_haves: ["SEO", "SEM", "Google Analytics", "Content Strategy", "Email Marketing", "PPC"], advice: "Focus on ROI, conversion rates, and audience segmentation." },
  "HR / Recruiter": { must_haves: ["ATS Systems", "Talent Sourcing", "Interviewing", "Onboarding", "Compliance"], advice: "Highlight your ability to scale teams and improve culture." },
  "Finance Analyst": { must_haves: ["Financial Modeling", "Forecasting", "Budgeting", "Excel Macros", "SAP", "Audit"], advice: "Precision is key; focus on risk mitigation and financial accuracy." },
  "Sales / Business Dev": { must_haves: ["Lead Generation", "CRM", "Salesforce", "Negotiation", "B2B Sales", "Quota"], advice: "Numbers are everything; highlight your revenue growth percentage." },
  "Project Manager": { must_haves: ["Jira", "Risk Management", "Budget Tracking", "Resource Planning", "PMP"], advice: "Focus on on-time, on-budget delivery of complex projects." },
  "AI / ML Engineer": { must_haves: ["PyTorch", "TensorFlow", "Scikit-Learn", "Neural Networks", "Pandas", "Math"], advice: "Showcase model accuracy and real-world deployment of AI." },
  "Customer Success": { must_haves: ["Relationship Mgmt", "Retention", "NPS", "Product Training", "Churn Reduction"], advice: "Highlight empathy and your ability to drive long-term value." }
};

// ── PRECISION SKILL BANK (80+ SKILLS) ─────────────────────────
const SKILL_BANK = [
  "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node", "Express", "MongoDB", "SQL", "PostgreSQL",
  "MySQL", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "REST", "GraphQL", "HTML", "CSS", "C++", "C#", "Swift", "Kotlin",
  "Go", "Rust", "Ruby", "PHP", "Django", "Flask", "Spring", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Tableau", "Power BI",
  "Figma", "Sketch", "Jira", "Agile", "Scrum", "SEO", "SEM", "Excel", "VLOOKUP", "Oracle", "SAP", "Salesforce", "HubSpot", "ETL",
  "Spark", "Hadoop", "Looker", "Redshift", "Snowflake", "Terraform", "Ansible", "Jenkins", "PMP", "Six Sigma",
  "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Data Analysis", "Data Visualization",
  "Data Warehousing", "Data Modeling", "Data Mining", "Project Management", "Product Management",
  "Business Analysis", "Requirements Gathering", "Financial Modeling", "Forecasting", "Budgeting",
  "AB Testing", "Google Analytics", "Linux", "Windows Server", "Networking", "Cybersecurity",
  "Penetration Testing", "CI/CD", "DevOps", "Microservices", "API Design", "System Design",
  "Database Design", "Communication", "Leadership", "Teamwork", "Problem Solving", "Critical Thinking"
];


app.use(cors({
  origin: '*',
  credentials: true
}));

app.use(express.json({ limit: '50mb' }));

const analyzeLimit = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  message: 'Too many analysis requests, please try again later'
});

const chatLimit = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 50,
  message: 'Too many chat messages, please try again later'
});

function validateInput(text, maxLength = 50000) {
  return text && typeof text === 'string' && text.length <= maxLength && text.length > 0;
}

function calculateATSScore(resumeText) {
  const text = resumeText.toLowerCase();
  const wordCount = text.split(/\s+/).length;

  let clarity = 0;
  const sentences = (text.match(/[.!?]+/g) || []).length;
  const bullets = (text.match(/[\n•\-\*]/g) || []).length;
  if (sentences >= 10) clarity += 25; else if (sentences >= 5) clarity += 15; else clarity += 5;
  if (bullets >= 10) clarity += 25; else if (bullets >= 5) clarity += 15; else clarity += 5;
  if (wordCount >= 300 && wordCount <= 1200) clarity += 30; else if (wordCount >= 150) clarity += 15; else clarity += 5;
  if (wordCount < 100) clarity = Math.max(clarity - 20, 5);
  const lineBreaks = (text.match(/\n/g) || []).length;
  if (lineBreaks >= 15) clarity += 20; else if (lineBreaks >= 8) clarity += 10;
  clarity = Math.min(100, clarity);

  let impact = 0;
  const numberMatches = (text.match(/\d+%|\d+\+|\$[\d,]+|\d+ (million|billion|thousand|team|people|clients|projects|users|customers)/gi) || []).length;
  impact += Math.min(40, numberMatches * 10);
  const impactVerbs = ['increased', 'decreased', 'reduced', 'improved', 'grew', 'saved', 'generated', 'delivered', 'scaled', 'doubled', 'tripled', 'achieved', 'exceeded', 'boosted', 'accelerated'];
  const impactVerbCount = impactVerbs.filter(v => text.includes(v)).length;
  impact += Math.min(35, impactVerbCount * 7);
  const dollarSigns = (text.match(/\$/g) || []).length;
  const percentSigns = (text.match(/%/g) || []).length;
  impact += Math.min(25, (dollarSigns + percentSigns) * 5);
  impact = Math.min(100, impact);

  let structure = 0;
  const sectionChecks = [
    { keywords: ['experience', 'work history', 'employment', 'professional experience'], weight: 20 },
    { keywords: ['education', 'academic', 'university', 'college', 'degree', 'bachelor', 'master', 'b.tech', 'b.e', 'mba'], weight: 20 },
    { keywords: ['skills', 'technical skills', 'competencies', 'proficiency', 'technologies'], weight: 20 },
    { keywords: ['summary', 'objective', 'profile', 'about me', 'professional summary'], weight: 15 },
    { keywords: ['@', 'email'], weight: 10 },
    { keywords: ['phone', 'mobile', 'contact', '+91', '+1'], weight: 10 },
    { keywords: ['project', 'portfolio'], weight: 5 }
  ];
  sectionChecks.forEach(section => {
    if (section.keywords.some(kw => text.includes(kw))) structure += section.weight;
  });
  structure = Math.min(100, structure);

  let actionScore = 0;
  const actionVerbs = ['managed', 'led', 'developed', 'designed', 'implemented', 'created', 'improved', 'achieved', 'increased', 'reduced', 'optimized', 'launched', 'coordinated', 'directed', 'spearheaded', 'orchestrated', 'built', 'engineered', 'analyzed', 'streamlined', 'executed', 'mentored', 'architected', 'collaborated', 'facilitated', 'negotiated', 'supervised', 'transformed', 'pioneered', 'established'];
  const foundActions = actionVerbs.filter(verb => text.includes(verb));
  actionScore = Math.min(100, foundActions.length * 7);

  const weights = { clarity: 0.20, impact: 0.30, structure: 0.25, action: 0.25 };
  const weightedScore = Math.round(
    clarity * weights.clarity +
    impact * weights.impact +
    structure * weights.structure +
    actionScore * weights.action
  );

  return {
    ats_score: Math.min(100, Math.max(5, weightedScore)),
    score_breakdown: {
      clarity: clarity,
      impact: impact,
      sections: structure,
      action_oriented: actionScore
    }
  };
}

async function generateJDMatch(resumeText, jobDescription) {
  if (!jobDescription || jobDescription.trim().length < 10) return null;

  const prompt = `You are an expert recruiter. Compare the following Resume against the Job Description.
  
  RESUME:
  ${resumeText.substring(0, 4000)}
  
  JOB DESCRIPTION:
  ${jobDescription.substring(0, 2000)}
  
  INSTRUCTIONS:
  1. Identify "matched_skills": skills present in both (semantic matching allowed, e.g., "React.js" matches "React").
  2. Identify "missing_skills": critical skills in the JD that are absent from the resume.
  3. Calculate "match_percentage": a realistic 0-100 score based on how well the candidate fits the requirements.
  
  Respond ONLY with a JSON object in this format:
  {
    "match_percentage": 85,
    "matched_skills": ["Skill A", "Skill B"],
    "missing_skills": ["Skill C", "Skill D"]
  }`;

  try {
    const responseText = await generateWithGemini(prompt, 500);
    const jsonMatch = responseText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const data = JSON.parse(jsonMatch[0]);
      return {
        match_percentage: Math.min(100, data.match_percentage || 0),
        matched_skills: (data.matched_skills || []).slice(0, 10),
        missing_skills: (data.missing_skills || []).slice(0, 10)
      };
    }
  } catch (e) {
    console.error("JD Match AI Error:", e);
  }
  return { match_percentage: 0, matched_skills: [], missing_skills: [] };
}

async function generateWithGemini(prompt, maxTokens = 1000) {
  try {
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: maxTokens, temperature: 0.7 }
    });

    const response = await result.response;
    const text = response.text().trim();
    return text || 'Analysis in progress.';
  } catch (error) {
    console.error('Gemini API error:', error.message);
    return '';
  }
}

async function generateProfessionalSummary(resumeText) {
  const prompt = `You are a world-class Executive Resume Writer.
Write a professional summary paragraph for this candidate based on their resume below.
RULES:
- Write exactly 4 to 5 COMPLETE sentences. Each sentence MUST end with a period.
- DO NOT stop mid-sentence or cut off abruptly under any circumstances.
- Mention the candidate's actual job titles, companies, years of experience, and key skills from the resume.
- Include at least one quantifiable achievement if present in the resume.
- Respond ONLY with the summary text. No labels, no markdown, no introductory text like "Here is...".

Resume:
${resumeText.substring(0, 4000)}`;

  const result = await generateWithGemini(prompt, 1200);  // raised from 800

  if (!result) {
    return 'Experienced professional with a strong track record of delivering results across multiple domains.';
  }

  // Only trim to last period if the response is genuinely cut mid-sentence
  // (i.e. ends with a word character, not punctuation)
  if (result && /\w$/.test(result.trim())) {
    const lastPeriod = result.lastIndexOf('.');
    if (lastPeriod > result.length * 0.5) {   // only trim if we keep >50% of the text
      return result.substring(0, lastPeriod + 1).trim();
    }
  }

  return result.trim();
}

// ══════════════════════════════════════════════════════════════
//  AI RECOMMENDATIONS — Gemini powered, resume-specific
//  Called directly in /analyze route (was missing before!)
// ══════════════════════════════════════════════════════════════
async function generateAIRecommendations(resumeText, atsScore, scoreBreakdown, missingSkills, jobDescription) {
  // Build rich context so Gemini gives resume-specific, not generic advice
  const weakAreas = [];
  if (scoreBreakdown.impact < 50) weakAreas.push('lacks quantified achievements (numbers, %, $)');
  if (scoreBreakdown.clarity < 50) weakAreas.push('formatting or bullet structure needs improvement');
  if (scoreBreakdown.action_oriented < 50) weakAreas.push('needs stronger action verbs');
  if (scoreBreakdown.sections < 60) weakAreas.push('missing key resume sections');

  const jdContext = jobDescription
    ? `\nTarget Job Description (first 800 chars):\n${jobDescription.substring(0, 800)}`
    : '';

  const missingContext = missingSkills && missingSkills.length > 0
    ? `\nCritical JD keywords MISSING from resume: ${missingSkills.slice(0, 6).join(', ')}`
    : '';

  const prompt = `You are a senior ATS resume consultant reviewing a REAL candidate's resume.
The automated ATS scan gave this resume a score of ${atsScore}/100.

Weak areas detected by the scanner: ${weakAreas.length > 0 ? weakAreas.join('; ') : 'overall score needs improvement'}
${missingContext}
${jdContext}

RESUME TEXT:
${resumeText.substring(0, 4000)}

YOUR TASK:
Give exactly 5 highly specific, actionable recommendations to improve THIS resume's ATS score.

STRICT RULES:
- Every recommendation MUST reference actual content from this specific resume — mention real job titles, company names, specific bullet points, or skills you see in the resume text above.
- NO generic advice like "add more keywords" or "use bullet points". Instead say EXACTLY what to change and WHERE.
- If the resume is missing quantified results, pick a specific bullet and show how to rewrite it with a number.
- If a JD is provided, map missing keywords to specific resume sections where they should be added.
- Each recommendation: 1–2 sentences max.
- Start each with a bold label like **Quantify This Bullet:**, **Weak Verb Fix:**, **Add Missing Keyword:**, **Missing Section:**, **Rewrite Suggestion:**, etc.

Format: Return ONLY a numbered list 1–5. Start your response directly with "1." — no introduction, no preamble, no closing remarks.
Each item must fit on a SINGLE LINE. Do not break a recommendation across multiple lines.`;

  try {
    const raw = await generateWithGemini(prompt, 1500);  // raised from 800 — each tip can be 2 sentences
    if (!raw || raw.length < 30) throw new Error('Empty Gemini response');

    console.log('Gemini raw recommendations:\n', raw.substring(0, 600));

    // Strip markdown fences
    let text = raw.replace(/```[\w]*\n?/g, '').replace(/```/g, '').trim();

    // Remove preamble lines ("Here are 5...", "Sure!", etc.)
    text = text.replace(/^[^\n]*(?:here are|following are|below are|recommendations?|sure[!,]?|certainly)[^\n]*\n+/im, '');

    // ── PRIMARY: split on "NUMBER. " or "NUMBER) " at start of line ──────
    // This regex splits BETWEEN numbered items correctly
    const chunks = text.split(/\n(?=\s*\d+[\.\)]\s)/);

    let tips = chunks
      .map(chunk => {
        // Collapse all internal newlines — Gemini often wraps long tips
        return chunk
          .replace(/^\s*\d+[\.\)]\s*/, '')  // remove leading "1. "
          .replace(/\n/g, ' ')              // collapse line breaks into spaces
          .replace(/\s{2,}/g, ' ')          // collapse multiple spaces
          .trim();
      })
      .filter(t => t.length > 20)
      .slice(0, 5);

    // ── FALLBACK A: bullet points (-, *, •) ──────────────────────────────
    if (tips.length < 3) {
      tips = text
        .split(/\n(?=\s*[\-\*\•])/)
        .map(chunk => chunk.replace(/^\s*[\-\*\•]\s*/, '').replace(/\n/g, ' ').replace(/\s{2,}/g, ' ').trim())
        .filter(t => t.length > 20)
        .slice(0, 5);
    }

    // ── FALLBACK B: double-newline paragraphs ────────────────────────────
    if (tips.length < 3) {
      tips = text
        .split(/\n\n+/)
        .map(p => p.replace(/^\s*\d+[\.\)]\s*/, '').replace(/\n/g, ' ').replace(/\s{2,}/g, ' ').trim())
        .filter(p => p.length > 20)
        .slice(0, 5);
    }

    // ── FALLBACK C: single newlines (last resort) ─────────────────────────
    if (tips.length < 3) {
      tips = text
        .split(/\n/)
        .map(l => l.replace(/^\s*\d+[\.\)]\s*/, '').replace(/^\s*[\-\*\•]\s*/, '').trim())
        .filter(l => l.length > 30)
        .slice(0, 5);
    }

    if (tips.length >= 3) {
      console.log(`✓ Gemini AI Recommendations generated (${tips.length} tips)`);
      return tips;
    }

    if (tips.length >= 1) {
      console.log(`⚠ Partial Gemini result (${tips.length} tips) — supplementing with fallback`);
      // Supplement with rule-based tips to always return 5
      const fallback = buildFallbackRecommendations(resumeText, atsScore, scoreBreakdown, missingSkills);
      const combined = [...tips, ...fallback].slice(0, 5);
      return combined;
    }

    throw new Error(`Could not parse any tips from Gemini response`);
  } catch (e) {
    console.warn('AI Recommendations fallback triggered:', e.message);
    return buildFallbackRecommendations(resumeText, atsScore, scoreBreakdown, missingSkills);
  }
}

// ── FALLBACK: rule-based when Gemini fails ───────────────────
function buildFallbackRecommendations(resumeText, atsScore, scoreBreakdown, missingSkills) {
  const tips = [];
  const lower = resumeText.toLowerCase();

  if (scoreBreakdown.impact < 50) {
    tips.push('**Quantify Results:** Your experience bullets lack measurable outcomes. Add specific numbers, percentages, or dollar values — e.g., "Reduced page load time by 35%" or "Managed a team of 6 engineers."');
  }

  if (missingSkills && missingSkills.length > 0) {
    tips.push(`**Add Missing Keywords:** Your resume is missing JD keywords: ${missingSkills.slice(0, 3).join(', ')}. Add these to your Skills section or weave them into your experience bullets naturally.`);
  }

  if (scoreBreakdown.action_oriented < 50) {
    tips.push('**Strengthen Action Verbs:** Replace weak openers like "Responsible for" or "Worked on" with power verbs — "Architected", "Spearheaded", "Orchestrated", "Delivered" — to pass ATS action-verb filters.');
  }

  if (!lower.includes('summary') && !lower.includes('objective') && !lower.includes('profile')) {
    tips.push('**Add Professional Summary:** Your resume is missing a Summary section — one of the first things both ATS systems and recruiters read. Write 3–4 lines highlighting your role, years of experience, and top 2 skills.');
  }

  if (scoreBreakdown.clarity < 50) {
    tips.push('**Improve Formatting:** Use consistent bullet points (•) for every experience item. ATS parsers score higher when each bullet begins with a verb and follows a clear "Action → Result" pattern.');
  }

  if (tips.length < 5) {
    tips.push('**Keyword Density:** Review the job description and ensure your most relevant skills appear at least 2–3 times across your resume sections (Skills, Summary, and Experience) for maximum ATS keyword matching.');
  }

  return tips.slice(0, 5);
}

async function chatWithAI(message, resumeText, jobDescription) {
  // Summarise the ontology as compact text instead of full JSON (~800 tokens saved)
  const ontologySummary = Object.entries(GLOBAL_CAREER_ONTOLOGY)
    .map(([role, data]) => `${role}: must-haves = ${data.must_haves.join(', ')}`)
    .join('\n');

  const prompt = `You are "The UnsaidTalks Career Master" — a world-class AI Career Coach with expertise across 15+ major global roles.
Your mission: Provide authoritative, role-specific, and deeply analytical advice.

USER QUESTION: "${message}"

CANDIDATE RESUME:
${resumeText.substring(0, 3500) || "No resume uploaded yet. Advice should be general but professional."}

TARGET JOB DESCRIPTION:
${jobDescription ? jobDescription.substring(0, 1000) : 'General career growth.'}

ROLE SKILL REQUIREMENTS:
${ontologySummary}

INSTRUCTIONS:
1. ROLE FOCUS: Identify the candidate's target role and highlight what skills are missing based on the role requirements above.
2. NO GENERIC TIPS: Do not say "be confident" or "work hard." Give specific, actionable advice like "Add SQL Window Functions to your Skills section" or "Rewrite your DocOnline bullet to highlight the 100+ leads metric."
3. RESUME-AWARE: Reference specific job titles, companies, or bullet points from their resume.
4. COMPLETE YOUR RESPONSE: Never stop mid-sentence. Write full, complete paragraphs.
5. TONE: Professional, encouraging, direct.`;

  return await generateWithGemini(prompt, 3000);  // raised from 2000
}

// ══════════════════════════════════════════════════════════════
//  /analyze — MAIN ROUTE (now calls Gemini for recommendations)
// ══════════════════════════════════════════════════════════════
app.post('/analyze', analyzeLimit, async (req, res) => {
  try {
    const { resume_text, job_description, job_title } = req.body;

    if (!validateInput(resume_text, 50000)) {
      return res.status(400).json({ error: 'Invalid resume text' });
    }

    const sessionId = uuidv4();

    // ── Step 1: JD Match via Gemini ──────────────────────────
    const jdMatch = await generateJDMatch(resume_text, job_description);

    // ── Step 2: ATS Score from Python engine (port 8001) ────
    let atsResult = { ats_score: 50, score_breakdown: { clarity: 50, impact: 50, sections: 50, action_oriented: 50 } };
    let pythonMissingSkills = [];

    try {
      const pyRes = await fetch('http://localhost:8001/api/analyze-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text, job_description: job_description || '' })
      });
      if (pyRes.ok) {
        const pyData = await pyRes.json();
        atsResult = { ats_score: pyData.ats_score, score_breakdown: pyData.score_breakdown };
        pythonMissingSkills = pyData.missing_skills || [];

        // Prefer Python engine skill lists when available
        if (pyData.matched_skills?.length) jdMatch && (jdMatch.matched_skills = pyData.matched_skills);
        if (pyData.missing_skills?.length) jdMatch && (jdMatch.missing_skills = pyData.missing_skills);

        console.log('✓ ATS Engine (8001) score:', pyData.ats_score);
      } else {
        console.warn('⚠ Python ATS returned non-OK, using JS fallback');
        atsResult = calculateATSScore(resume_text);
      }
    } catch (pyErr) {
      console.warn('⚠ Python ATS Engine unreachable, using JS fallback');
      atsResult = calculateATSScore(resume_text);
    }

    // ── Step 3: Summary via Gemini ───────────────────────────
    const summary = await generateProfessionalSummary(resume_text);

    // ── Step 4: AI Recommendations via Gemini ───────────────
    // Pass ATS score + breakdown + missing skills so Gemini gives SPECIFIC advice
    const missingForRecs = pythonMissingSkills.length > 0
      ? pythonMissingSkills
      : (jdMatch?.missing_skills || []);

    const recommendations = await generateAIRecommendations(
      resume_text,
      atsResult.ats_score,
      atsResult.score_breakdown,
      missingForRecs,
      job_description || ''
    );

    console.log('✓ Gemini Recommendations ready:', recommendations.length, 'tips');

    // ── Step 5: Save to Supabase ─────────────────────────────
    try {
      const { error } = await supabase
        .from('resume_sessions')
        .insert([{
          session_id: sessionId,
          resume_text: resume_text.substring(0, 10000),
          job_description: job_description || null,
          job_title: job_title || null,
          ats_score: atsResult.ats_score,
          score_breakdown: atsResult.score_breakdown,
          summary: summary,
          jd_match: jdMatch,
          created_at: new Date().toISOString()
        }]);

      if (error) {
        console.error('Supabase insert error:', error.message, error.details || '', error.hint || '');
      } else {
        console.log('✓ Saved to Supabase');
      }
    } catch (dbError) {
      console.error('Database error:', dbError);
    }

    // ── Step 6: Return full response ─────────────────────────
    res.json({
      session_id: sessionId,
      ats_score: atsResult.ats_score,
      score_breakdown: atsResult.score_breakdown,
      summary,
      recommendations,                              // ← Now always Gemini-powered ✓
      jd_match_percentage: jdMatch?.match_percentage || 0,
      matched_skills: jdMatch?.matched_skills || [],
      missing_skills: jdMatch?.missing_skills || []
    });

  } catch (error) {
    console.error('Analyze error:', error);
    res.status(500).json({ error: 'Analysis failed: ' + error.message });
  }
});

app.post('/chat', chatLimit, async (req, res) => {
  try {
    const { message, resume_text, job_description, session_id } = req.body;

    if (!message || !validateInput(message, 1000)) {
      return res.status(400).json({ error: 'Invalid message' });
    }

    const response = await chatWithAI(message, resume_text || '', job_description || '');

    try {
      const { error } = await supabase
        .from('chat_messages')
        .insert([{
          session_id: session_id || uuidv4(),
          user_message: message,
          assistant_response: response,
          created_at: new Date().toISOString()
        }]);

      if (error) {
        console.error('Supabase insert error [chat_messages]:', error.message, error.details || '', error.hint || '');
      }
    } catch (dbError) {
      console.error('Chat save error:', dbError);
    }

    res.json({ response, session_id });
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({ error: 'Chat failed: ' + error.message });
  }
});

app.post('/ai/complete', async (req, res) => {
  try {
    const { current_text, context, job_description } = req.body;

    if (!current_text || current_text.length < 5) {
      return res.status(400).json({ error: 'Context too short for completion' });
    }

    const prompt = `You are a professional resume writer. 
Complete the following sentence or bullet point for a resume ${context ? `in the ${context} section` : ''}.
${job_description ? `Target Job: ${job_description.substring(0, 500)}` : ''}

CURRENT TEXT: "${current_text}"

INSTRUCTIONS:
- Provide ONLY the completion (the words that follow the current text).
- Keep it impactful, using strong action verbs and professional metrics.
- Do NOT repeat the current text.
- Do NOT provide multiple options.
- Respond with exactly 10 to 15 words that logically finish the thought.

COMPLETION:`;

    const completion = await generateWithGemini(prompt, 100);
    res.json({ completion });
  } catch (error) {
    console.error('AI Complete error:', error);
    res.status(500).json({ error: 'Auto-complete failed' });
  }
});

app.get('/health', (req, res) => {
  res.json({
    status: 'running',
    gemini: !!GEMINI_API_KEY,
    supabase: !!SUPABASE_URL
  });
});

app.listen(PORT, () => {
  console.log(`\n✅ UnsaidTalks Resume Analyzer`);
  console.log(`🚀 Server: http://localhost:${PORT}`);
  console.log(`🤖 Gemini: Connected`);
  console.log(`💾 Supabase: ${SUPABASE_URL ? 'Connected' : 'Not configured'}\n`);
});