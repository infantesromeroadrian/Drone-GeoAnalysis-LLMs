import API from '../services/api.js';

let sessionId = null;
let initialized = false;

export function initAnalysisView() {
    if (initialized) return;
    initialized = true;
    setupUpload();
    setupChat();
}

function setupUpload() {
    const area = document.getElementById('upload-drop');
    const input = document.getElementById('analysis-file');
    if (!area || !input) return;

    area.addEventListener('click', () => input.click());
    area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('dragover'); });
    area.addEventListener('dragleave', () => area.classList.remove('dragover'));
    area.addEventListener('drop', e => {
        e.preventDefault();
        area.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    input.addEventListener('change', () => { if (input.files.length) handleFile(input.files[0]); });

    onClick('btn-analyze-geo', () => runAnalysis('geo'));
    onClick('btn-analyze-yolo', () => runAnalysis('yolo'));
}

let currentFile = null;

function handleFile(file) {
    currentFile = file;
    const preview = document.getElementById('analysis-preview');
    if (!preview) return;

    const reader = new FileReader();
    reader.onload = e => {
        preview.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width:100%;border-radius:8px">`;
    };
    reader.readAsDataURL(file);

    document.getElementById('analysis-buttons')?.classList.remove('hidden');
}

async function runAnalysis(type) {
    if (!currentFile) return;

    const results = document.getElementById('analysis-results');
    if (results) results.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div><p class="text-muted" style="margin-top:12px">Analyzing...</p></div>';

    const form = new FormData();
    form.append('image', currentFile);

    try {
        const data = type === 'yolo' ? await API.analyzeYOLO(form) : await API.analyzeImage(form);

        if (data.error) {
            results.innerHTML = `<div style="color:var(--danger);padding:20px"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
            return;
        }

        if (type === 'yolo') renderYOLOResults(data, results);
        else renderGeoResults(data, results);

        sessionId = data.session_id || `session_${Date.now()}`;
        document.getElementById('chat-section')?.classList.remove('hidden');
    } catch (err) {
        if (results) results.innerHTML = `<div style="color:var(--danger);padding:20px">Error: ${err.message}</div>`;
    }
}

function renderGeoResults(data, container) {
    const r = data.results || data;
    container.innerHTML = `
        <div class="card mb-12">
            <div class="card-title"><i class="fas fa-map-marker-alt"></i> Location</div>
            <div class="telemetry-item"><span class="telemetry-label">Country</span><span class="telemetry-value">${r.country || 'N/A'}</span></div>
            <div class="telemetry-item"><span class="telemetry-label">City</span><span class="telemetry-value">${r.city || 'N/A'}</span></div>
            <div class="telemetry-item"><span class="telemetry-label">District</span><span class="telemetry-value">${r.district || 'N/A'}</span></div>
            <div class="telemetry-item"><span class="telemetry-label">Confidence</span><span class="telemetry-value" style="color:var(--success)">${r.confidence || 0}%</span></div>
            ${r.coordinates ? `<div class="telemetry-item"><span class="telemetry-label">Coordinates</span><span class="telemetry-value">${r.coordinates.latitude?.toFixed(4)}, ${r.coordinates.longitude?.toFixed(4)}</span></div>` : ''}
        </div>
        ${r.supporting_evidence?.length ? `
        <div class="card">
            <div class="card-title"><i class="fas fa-search"></i> Evidence</div>
            ${r.supporting_evidence.map(e => `<div style="padding:4px 0;font-size:0.82rem;color:var(--text-secondary)"><i class="fas fa-check" style="color:var(--success);margin-right:8px"></i>${e}</div>`).join('')}
        </div>` : ''}
    `;
}

function renderYOLOResults(data, container) {
    const r = data.results || data;
    const detections = r.detections || [];
    container.innerHTML = `
        <div class="card mb-12">
            <div class="card-title"><i class="fas fa-eye"></i> YOLO Detection</div>
            <div class="telemetry-item"><span class="telemetry-label">Objects found</span><span class="telemetry-value">${r.total_objects || 0}</span></div>
            <div class="telemetry-item"><span class="telemetry-label">Model</span><span class="telemetry-value">${r.model_version || 'YOLO 11n'}</span></div>
        </div>
        ${r.annotated_image ? `<div class="image-preview"><img src="data:image/jpeg;base64,${r.annotated_image}" alt="Annotated"></div>` : ''}
        ${detections.length ? `
        <div class="card" style="margin-top:12px">
            <div class="card-title"><i class="fas fa-list"></i> Detections (${detections.length})</div>
            ${detections.slice(0, 10).map(d => `
                <div class="telemetry-item">
                    <span class="telemetry-label">${d.class_name}</span>
                    <span class="telemetry-value">${(d.confidence * 100).toFixed(1)}%</span>
                </div>
            `).join('')}
        </div>` : ''}
    `;
}

function setupChat() {
    onClick('btn-chat-send', sendChatMessage);
    document.getElementById('chat-input')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');
    if (!input || !messages || !input.value.trim()) return;

    const question = input.value.trim();
    input.value = '';

    messages.innerHTML += `<div class="chat-msg user">${question}</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        const data = await API.askQuestion(sessionId, question);
        const answer = data.response || data.error || 'No response';
        messages.innerHTML += `<div class="chat-msg assistant">${answer}</div>`;
    } catch {
        messages.innerHTML += `<div class="chat-msg assistant" style="color:var(--danger)">Error getting response</div>`;
    }
    messages.scrollTop = messages.scrollHeight;
}

function onClick(id, handler) {
    document.getElementById(id)?.addEventListener('click', handler);
}
