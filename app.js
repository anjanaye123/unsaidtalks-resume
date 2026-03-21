pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

const API_URL = 'http://localhost:3001';
let resumeText = '';
let currentAnalysisData = null;

// File Upload Handler
document.getElementById('resumeFile').addEventListener('change', handleFileSelect);

const uploadArea = document.getElementById('uploadArea');
uploadArea.addEventListener('click', () => {
    document.getElementById('resumeFile').click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--accent)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = 'var(--border-color)';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border-color)';
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) handleFile(file);
}

async function handleFile(file) {
    if (file.type !== 'application/pdf') {
        showToast('Please upload a PDF file', 'error');
        return;
    }
    if (file.size > 50 * 1024 * 1024) {
        showToast('File size must be less than 50MB', 'error');
        return;
    }
    try {
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = formatFileSize(file.size);
        document.getElementById('uploadArea').style.display = 'none';
        document.getElementById('filePreview').style.display = 'block';
        resumeText = await extractPdfText(file);
        showToast('Resume loaded successfully!', 'success');
    } catch (error) {
        showToast('Failed to read PDF: ' + error.message, 'error');
    }
}

async function extractPdfText(file) {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let text = '';
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        text += textContent.items.map(item => item.str).join(' ') + '\n';
    }
    return text;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function removeFile() {
    document.getElementById('resumeFile').value = '';
    resumeText = '';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('filePreview').style.display = 'none';
}

function scrollToUpload() {
    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

function showJDSection() {
    if (!resumeText) {
        showToast('Please upload a resume first', 'error');
        return;
    }
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('jdSection').style.display = 'block';
    document.getElementById('jdSection').scrollIntoView({ behavior: 'smooth' });
}

function showUploadSection() {
    document.getElementById('jdSection').style.display = 'none';
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

async function startAnalysis() {
    if (!resumeText) {
        showToast('Please upload a resume first', 'error');
        return;
    }

    const jobDescription = document.getElementById('jobDescription').value.trim();
    const jobTitle = document.getElementById('jobTitle').value.trim();

    document.getElementById('jdSection').style.display = 'none';
    document.getElementById('analysisSection').style.display = 'block';
    document.getElementById('analyzingOverlay').style.display = 'flex';
    document.getElementById('analysisSection').scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText,
                job_description: jobDescription,
                job_title: jobTitle
            })
        });

        if (!response.ok) throw new Error('Analysis failed: ' + response.status);

        const data = await response.json();
        currentAnalysisData = data;

        // Store whether user actually provided a JD
        currentAnalysisData._hasJD = jobDescription.length >= 10;

        setTimeout(() => {
            document.getElementById('analyzingOverlay').style.display = 'none';
            displayResults(data);
            generateRecommendations(data);
        }, 3000);

    } catch (error) {
        document.getElementById('analyzingOverlay').style.display = 'none';
        showToast('Analysis failed: ' + error.message, 'error');
    }
}

function displayResults(data) {
    // ── ATS Score ──────────────────────────────────────────
    const score = Math.round(data.ats_score || 0);
    document.getElementById('scoreValue').textContent = score;

    const circumference = 2 * Math.PI * 85;
    const offset = circumference - (score / 100) * circumference;
    document.getElementById('scoreCircle').style.strokeDashoffset = offset;

    let scoreLabel = 'Needs Improvement';
    if (score >= 80) scoreLabel = 'Excellent';
    else if (score >= 60) scoreLabel = 'Good';
    else if (score >= 40) scoreLabel = 'Fair';
    document.getElementById('scoreLabel').textContent = scoreLabel;

    // ── Score Breakdown ────────────────────────────────────
    const breakdown = data.score_breakdown || {};
    animateScore('clarity', breakdown.clarity || 0);
    animateScore('impact', breakdown.impact || 0);
    animateScore('sections', breakdown.sections || 0);
    animateScore('action', breakdown.action_oriented || 0);

    // ── Professional Summary ───────────────────────────────
    document.getElementById('summaryContent').textContent =
        data.summary || 'Professional summary not available.';

    // ── JD Match Card ──────────────────────────────────────
    // Only show when user actually pasted a JD (length >= 10)
    const hasJD = data._hasJD;
    const jdCard = document.getElementById('jdMatchCard');

    if (!hasJD) {
        // No JD provided — hide the card entirely
        jdCard.style.display = 'none';
        return;
    }

    jdCard.style.display = 'block';

    // ── Calculate match % from the skill arrays (always accurate)
    const matchedSkills = data.matched_skills || [];
    const missingSkills = data.missing_skills || [];
    const totalJDSkills = matchedSkills.length + missingSkills.length;

    let matchPct = 0;
    if (totalJDSkills > 0) {
        matchPct = Math.round((matchedSkills.length / totalJDSkills) * 100);
    } else if (typeof data.jd_match_percentage === 'number' && data.jd_match_percentage > 0) {
        matchPct = data.jd_match_percentage;
    } else if (typeof data.match_percentage === 'number' && data.match_percentage > 0) {
        matchPct = data.match_percentage;
    }

    // ── SET percentage to DOM ──────────────────────────────
    const pctEl = document.getElementById('matchPercentage');
    pctEl.textContent = matchPct + '%';
    if (matchPct >= 70) pctEl.style.color = 'var(--success)';
    else if (matchPct >= 40) pctEl.style.color = 'var(--warning)';
    else pctEl.style.color = 'var(--danger)';

    // ── Matched Skills ─────────────────────────────────────
    if (matchedSkills.length > 0) {
        document.getElementById('matchedSkills').innerHTML = matchedSkills
            .map(s => `<span class="skill-tag" style="background:rgba(61,214,140,0.1);border-color:rgba(61,214,140,0.35);color:var(--success);">${s.toLowerCase()}</span>`)
            .join('');
    } else {
        document.getElementById('matchedSkills').innerHTML =
            '<span style="color:var(--text-secondary);font-size:0.88rem;">No skills matched yet.</span>';
    }

    // ── Missing Skills ─────────────────────────────────────
    if (missingSkills.length > 0) {
        document.getElementById('missingSkills').innerHTML = missingSkills
            .map(s => `<span class="skill-tag" style="background:rgba(255,77,109,0.08);border-color:rgba(255,77,109,0.3);color:var(--danger);">${s.toLowerCase()}</span>`)
            .join('');
    } else {
        document.getElementById('missingSkills').innerHTML =
            '<span style="color:var(--text-secondary);font-size:0.88rem;">No critical gaps found — great match!</span>';
    }
}

function animateScore(type, value) {
    document.getElementById(`${type}Score`).textContent = value;
    document.getElementById(`${type}Bar`).style.width = Math.min(100, value) + '%';
}

function generateRecommendations(data) {
    let listHTML = '';

    if (data.recommendations && Array.isArray(data.recommendations) && data.recommendations.length > 0) {
        listHTML = data.recommendations
            .map(rec => `<div class="recommendation-item">${escapeHtml(rec)}</div>`)
            .join('');
    } else {
        // Rule-based fallback
        const recommendations = [];
        const score = data.ats_score || 0;
        const breakdown = data.score_breakdown || {};

        if ((breakdown.action_oriented || 0) < 70)
            recommendations.push('Use more action verbs like "led," "managed," "developed," "achieved" to demonstrate impact.');
        if ((breakdown.impact || 0) < 70)
            recommendations.push('Quantify your achievements with numbers, percentages, or metrics to show tangible results.');
        if ((breakdown.clarity || 0) < 70)
            recommendations.push('Improve formatting with clear bullet points and consistent structure throughout your resume.');
        if ((breakdown.sections || 0) < 70)
            recommendations.push('Ensure all key sections are present: Contact Info, Summary, Experience, Education, and Skills.');
        if (score < 60)
            recommendations.push('Consider using a professional resume template with ATS-friendly formatting.');
        if (data.missing_skills && data.missing_skills.length > 0)
            recommendations.push(`Highlight these missing skills if you have them: ${data.missing_skills.slice(0, 3).join(', ')}`);

        listHTML = recommendations.length > 0
            ? recommendations.map(rec => `<div class="recommendation-item">${rec}</div>`).join('')
            : '<div class="recommendation-item">Great job! Your resume looks well structured.</div>';
    }

    document.getElementById('recommendationsList').innerHTML = listHTML;
}

function copySummary() {
    const text = document.getElementById('summaryContent').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Summary copied to clipboard!', 'success');
    });
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    if (!currentAnalysisData) {
        showToast('Please analyze a resume first', 'error');
        return;
    }

    input.value = '';
    const chatMessages = document.getElementById('chatMessages');

    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message user';
    userMsg.innerHTML = `<div class="message-bubble">${escapeHtml(message)}</div>`;
    chatMessages.appendChild(userMsg);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const typingMsg = document.createElement('div');
    typingMsg.className = 'chat-message assistant';
    typingMsg.innerHTML = '<div class="message-bubble" style="opacity:0.5;">...</div>';
    chatMessages.appendChild(typingMsg);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                resume_text: resumeText,
                job_description: document.getElementById('jobDescription').value,
                session_id: currentAnalysisData.session_id
            })
        });

        const data = await response.json();
        typingMsg.remove();

        const assistantMsg = document.createElement('div');
        assistantMsg.className = 'chat-message assistant';
        assistantMsg.innerHTML = `<div class="message-bubble">${escapeHtml(data.response)}</div>`;
        chatMessages.appendChild(assistantMsg);
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        typingMsg.remove();
        showToast('Chat error: ' + error.message, 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function resetAnalysis() {
    resumeText = '';
    currentAnalysisData = null;

    const fileInput = document.getElementById('resumeFile');
    fileInput.value = '';

    document.getElementById('jobDescription').value = '';
    document.getElementById('jobTitle').value = '';

    document.getElementById('analysisSection').style.display = 'none';
    document.getElementById('jdSection').style.display = 'none';
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('filePreview').style.display = 'none';

    document.getElementById('scoreValue').textContent = '0';
    document.getElementById('scoreLabel').textContent = '';
    const circumference = 2 * Math.PI * 85;
    document.getElementById('scoreCircle').style.strokeDashoffset = circumference;

    ['clarity', 'impact', 'sections', 'action'].forEach(type => {
        const scoreEl = document.getElementById(`${type}Score`);
        const barEl = document.getElementById(`${type}Bar`);
        if (scoreEl) scoreEl.textContent = '0';
        if (barEl) barEl.style.width = '0%';
    });

    const summaryEl = document.getElementById('summaryContent');
    if (summaryEl) summaryEl.textContent = '';

    const recEl = document.getElementById('recommendationsList');
    if (recEl) recEl.innerHTML = '';

    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-bubble">Hi! I've analyzed your resume. Ask me anything to improve it!</div>
        </div>`;

    const matchEl = document.getElementById('matchPercentage');
    if (matchEl) { matchEl.textContent = '0%'; matchEl.style.color = ''; }

    const matchedEl = document.getElementById('matchedSkills');
    if (matchedEl) matchedEl.innerHTML = '';

    const missingEl = document.getElementById('missingSkills');
    if (missingEl) missingEl.innerHTML = '';

    document.getElementById('jdMatchCard').style.display = 'none';

    document.getElementById('heroSection').scrollIntoView({ behavior: 'smooth' });
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: var(--card-bg);
        color: ${type === 'success' ? 'var(--success)' : 'var(--danger)'};
        padding: 0.9rem 1.4rem;
        border-radius: 8px;
        border: 1.5px solid ${type === 'success' ? 'var(--success)' : 'var(--danger)'};
        z-index: 10000;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}