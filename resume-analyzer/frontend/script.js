// API Configuration
const API_PORT = 5000;
const API_URL = window.location.hostname
    ? `http://${window.location.hostname}:${API_PORT}`
    : `http://127.0.0.1:${API_PORT}`;
console.log('[DEBUG] API_URL set to', API_URL);

// Check if running from file:// protocol
if (window.location.protocol === 'file:') {
    alert('Please run the frontend from a web server. Use "python run.py" or serve from http://localhost:8000');
}

let selectedFile = null;
let isAnalyzing = false;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const fileInfo = document.getElementById('fileInfo');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');
const backendStatus = document.getElementById('backendStatus');
const analysisStatus = document.getElementById('analysisStatus');
const logoutBtn = document.getElementById('logoutBtn');

// Initialize app
async function initApp() {
    resetUI();
    const isAuthenticated = await checkAuthentication();
    if (isAuthenticated) {
        await checkBackend();
        await loadStoredResumes();
    }
}

function setBackendStatus(message, healthy) {
    if (!backendStatus) return;
    backendStatus.textContent = message;
    backendStatus.style.color = healthy ? '#00ff88' : '#ff6b9d';
}

function setAnalysisStatus(message, type = 'info') {
    if (!analysisStatus) return;
    analysisStatus.textContent = message;
    analysisStatus.style.color = type === 'error' ? '#ff6b9d' : '#00d4ff';
}

// Check authentication on page load
async function checkAuthentication() {
    try {
        // Check authentication status
        const response = await fetch(`${API_URL}/auth/status`, {
            method: 'GET',
            credentials: 'include'  // Include cookies for session
        });

        const data = await response.json();

        if (response.ok && data.authenticated) {
            // User is authenticated
            logoutBtn.style.display = 'block';
            return true;
        } else {
            // User is not authenticated, redirect to login
            window.location.href = `${API_URL}/login`;
            return false;
        }
    } catch (error) {
        console.log('[DEBUG] Auth check failed, redirecting to login:', error);
        window.location.href = `${API_URL}/login`;
        return false;
    }
}

async function checkBackend() {
    try {
        const response = await fetch(`${API_URL}/health`, { method: 'GET', mode: 'cors' });
        if (!response.ok) {
            throw new Error(`Backend health check failed: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        if (!data || data.status !== 'healthy') {
            throw new Error('Backend health response invalid');
        }
        setBackendStatus('Backend available', true);
        setAnalysisStatus('Ready for upload');
        return true;
    } catch (error) {
        setBackendStatus('Backend unavailable', false);
        setAnalysisStatus('Backend unavailable', 'error');
        showError(`Backend unavailable: ${error.message}`);
        analyzeBtn.disabled = true;
        analyzeBtn.classList.add('disabled');
        return false;
    }
}

// Logout function
async function logout() {
    try {
        const response = await fetch(`${API_URL}/logout`, {
            method: 'GET',
            credentials: 'include'
        });
        // Redirect to login regardless of response
        window.location.href = `${API_URL}/login`;
    } catch (error) {
        console.log('[DEBUG] Logout error:', error);
        window.location.href = `${API_URL}/login`;
    }
}

window.addEventListener('unhandledrejection', (event) => {
    showError(`Unhandled promise error: ${event.reason}`);
});

// Drag and drop functionality
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// File input change event
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

// Analyze button click event
analyzeBtn.addEventListener('click', analyzeResume);

window.addEventListener('error', (e) => {
    showError(`Client error: ${e.message}`);
});

// Handle file selection
function handleFileSelect(file) {
    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    if (!isPdf) {
        showError('Please select a PDF file');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showError('File size must be less than 10MB');
        return;
    }

    selectedFile = file;
    
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = 
        `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    
    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove('disabled');
    setBackendStatus('Ready to analyze', true);
    setAnalysisStatus('File selected. Click Analyze to start.');
    hideError();
    console.log('[DEBUG] File selected:', file.name, file.size, 'bytes');
}

// Clear file selection
function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    resultsSection.style.display = 'none';
    hideError();
    fileInfo.innerHTML = `
        <div class="file-details">
            <span class="file-icon">📄</span>
            <div>
                <p class="file-name" id="fileName"></p>
                <p class="file-size" id="fileSize"></p>
            </div>
        </div>
        <button class="btn-clear" type="button" onclick="clearFile()">✕</button>
    `;
    analyzeBtn.disabled = true;
    analyzeBtn.classList.add('disabled');
}

// Analyze resume
async function analyzeResume(event) {
    console.log('[DEBUG] analyzeResume called', { event, selectedFile });
    if (event && event.preventDefault) {
        event.preventDefault();
    }

    if (isAnalyzing) {
        console.log('[DEBUG] Analysis already in progress, skipping duplicate call');
        return;
    }
    isAnalyzing = true;

    if (!selectedFile) {
        showError('Please select a file first');
        isAnalyzing = false;
        return;
    }

    // Show loading state
    uploadArea.parentElement.style.display = 'none';
    fileInfo.style.display = 'none';
    analyzeBtn.style.display = 'none';
    loadingSpinner.style.display = 'flex';
    resultsSection.style.display = 'none';
    hideError();

    try {
        setAnalysisStatus('Uploading resume and analyzing...');

        // Prepare form data
        const formData = new FormData();
        formData.append('file', selectedFile);

        // Send request to backend
        console.log('[DEBUG] Sending resume to backend', { url: `${API_URL}/analyze`, fileName: selectedFile.name });
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            mode: 'cors',
            credentials: 'include',
            body: formData
        });

        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            throw new Error('Unable to parse server response.');
        }

        if (!response.ok) {
            const message = data?.error || response.statusText || 'An error occurred';
            const details = data?.details ? ` ${data.details}` : '';
            setBackendStatus('Backend error', false);
            setAnalysisStatus('Analysis failed', 'error');
            throw new Error(`${message}${details}`);
        }

        console.log('[DEBUG] Backend response OK', data);
        setBackendStatus('Backend available', true);
        setAnalysisStatus('Resume analyzed successfully');
        displayResults(data.data);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to analyze resume. Make sure the backend server is running.');
        setAnalysisStatus('Analysis failed', 'error');
        resetUI();
    } finally {
        isAnalyzing = false;
    }
}

// Display results
function displayResults(data) {
    console.log('[DEBUG] displayResults data', data);
    // Hide loading
    loadingSpinner.style.display = 'none';
    
    // Show results
    resultsSection.style.display = 'block';

    // Populate score
    const score = data.score || 0;
    document.getElementById('scoreValue').textContent = score;
    updateScoreRing(score);

    // Populate contact info
    const contact = data.contact_info || {};
    document.getElementById('emailValue').textContent = contact.email || 'Not found';
    document.getElementById('phoneValue').textContent = contact.phone || 'Not found';
    document.getElementById('linkedinValue').textContent = contact.linkedin || 'Not found';

    // Populate stats
    document.getElementById('pageCount').textContent = data.page_count || 0;
    document.getElementById('wordCount').textContent = data.word_count || 0;
    document.getElementById('expCount').textContent = data.experience_count || 0;

    // Populate skills
    const skillsList = document.getElementById('skillsList');
    skillsList.innerHTML = '';
    if (data.skills && data.skills.length > 0) {
        data.skills.forEach(skill => {
            const badge = document.createElement('span');
            badge.className = 'skill-badge';
            badge.textContent = skill;
            skillsList.appendChild(badge);
        });
    } else {
        skillsList.innerHTML = '<p style="color: rgba(255,255,255,0.6);">No specific skills detected</p>';
    }

    // Populate suggestions
    const suggestionsList = document.getElementById('suggestionsList');
    suggestionsList.innerHTML = '';
    if (data.suggestions && data.suggestions.length > 0) {
        data.suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.textContent = suggestion;
            suggestionsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'Your resume looks great!';
        suggestionsList.appendChild(li);
    }

    // Smooth scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

// Update score ring animation
function updateScoreRing(score) {
    const scoreRing = document.getElementById('scoreRing');
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (score / 100) * circumference;
    
    scoreRing.style.strokeDasharray = circumference;
    scoreRing.style.strokeDashoffset = circumference;
    
    setTimeout(() => {
        scoreRing.style.transition = 'stroke-dashoffset 1s ease';
        scoreRing.style.strokeDashoffset = offset;
    }, 100);
}

// Reset analyzer
function resetAnalyzer() {
    selectedFile = null;
    fileInput.value = '';
    resetUI();
    
    // Scroll to top
    document.documentElement.scrollTop = 0;
}

// Reset UI to initial state
function resetUI() {
    uploadArea.parentElement.style.display = 'block';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    analyzeBtn.style.display = 'block';
    analyzeBtn.disabled = true;
    analyzeBtn.classList.add('disabled');
    loadingSpinner.style.display = 'none';
    resultsSection.style.display = 'none';
    setAnalysisStatus('Upload a PDF to start');
    hideError();
}

// Show error message
function showError(message) {
    console.error('[ERROR]', message);
    if (!errorMessage) return;
    errorMessage.textContent = `⚠️ ${message}`;
    errorMessage.style.display = 'block';
}

// Hide error message
function hideError() {
    errorMessage.style.display = 'none';
}

// Download results as JSON
function downloadResults() {
    const score = document.getElementById('scoreValue').textContent;
    const email = document.getElementById('emailValue').textContent;
    const phone = document.getElementById('phoneValue').textContent;
    const skills = Array.from(document.querySelectorAll('.skill-badge'))
        .map(el => el.textContent);
    const suggestions = Array.from(document.querySelectorAll('.suggestions-list li'))
        .map(el => el.textContent);

    const results = {
        timestamp: new Date().toISOString(),
        score,
        contact: { email, phone },
        skills,
        suggestions,
        fileName: selectedFile ? selectedFile.name : 'unknown'
    };

    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `resume-analysis-${new Date().getTime()}.json`;
    link.click();
}

// Stored Resumes Functions
async function loadStoredResumes() {
    const storedResumesList = document.getElementById('storedResumesList');
    if (!storedResumesList) return;

    try {
        storedResumesList.innerHTML = '<p class="loading-text">Loading stored resumes...</p>';

        const response = await fetch(`${API_URL}/resumes`, { 
            method: 'GET', 
            mode: 'cors',
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error(`Failed to load resumes: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to load resumes');
        }

        displayStoredResumes(data.data);

    } catch (error) {
        console.error('[ERROR] Failed to load stored resumes:', error);
        storedResumesList.innerHTML = `<p class="error-message">Failed to load resumes: ${error.message}</p>`;
    }
}

function displayStoredResumes(resumes) {
    const storedResumesList = document.getElementById('storedResumesList');
    if (!storedResumesList) return;

    if (!resumes || resumes.length === 0) {
        storedResumesList.innerHTML = '<p class="no-resumes">No stored resumes found. Upload and analyze a resume to get started.</p>';
        return;
    }

    const resumeItems = resumes.map(resume => {
        const uploadDate = new Date(resume.upload_date).toLocaleDateString();
        const score = resume.score || 0;

        return `
            <div class="resume-item" onclick="viewStoredResume(${resume.id})">
                <div class="resume-header">
                    <div class="resume-title">${resume.original_filename}</div>
                    <div class="resume-date">${uploadDate}</div>
                </div>
                <div class="resume-meta">
                    <span>Pages: ${resume.page_count || 0}</span>
                    <span>Words: ${resume.word_count || 0}</span>
                    <span class="resume-score">Score: ${score}/100</span>
                    <button class="btn-view-resume" onclick="event.stopPropagation(); viewStoredResume(${resume.id})">View</button>
                    <button class="btn-delete-resume" onclick="event.stopPropagation(); deleteStoredResume(${resume.id})">Delete</button>
                </div>
            </div>
        `;
    }).join('');

    storedResumesList.innerHTML = resumeItems;
}

async function viewStoredResume(resumeId) {
    try {
        const response = await fetch(`${API_URL}/resumes/${resumeId}`, { 
            method: 'GET', 
            mode: 'cors',
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error(`Failed to load resume: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to load resume');
        }

        // Display the stored resume data in the results section
        displayResults(data.data);
        setAnalysisStatus(`Viewing stored resume: ${data.data.original_filename}`);

    } catch (error) {
        console.error('[ERROR] Failed to view stored resume:', error);
        setAnalysisStatus(`Error loading resume: ${error.message}`, 'error');
    }
}

async function deleteStoredResume(resumeId) {
    if (!confirm('Are you sure you want to delete this resume? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/resumes/${resumeId}`, { 
            method: 'DELETE', 
            mode: 'cors',
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error(`Failed to delete resume: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to delete resume');
        }

        // Reload the stored resumes list
        await loadStoredResumes();
        setAnalysisStatus('Resume deleted successfully');

    } catch (error) {
        console.error('[ERROR] Failed to delete stored resume:', error);
        setAnalysisStatus(`Error deleting resume: ${error.message}`, 'error');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', initApp);
