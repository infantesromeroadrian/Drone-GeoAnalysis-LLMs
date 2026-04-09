import API from '../services/api.js';

export async function initMissionsView() {
    await loadAllMissions();
}

async function loadAllMissions() {
    const container = document.getElementById('missions-grid');
    if (!container) return;

    container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';

    try {
        const data = await API.getLLMMissions();
        const missions = data.missions || [];

        if (!missions.length) {
            container.innerHTML = `
                <div style="text-align:center;padding:60px;color:var(--text-muted)">
                    <i class="fas fa-folder-open" style="font-size:2.5rem;margin-bottom:12px;display:block"></i>
                    <p>No missions found</p>
                    <p class="text-sm" style="margin-top:8px">Go to Mission Control to create your first AI mission</p>
                </div>
            `;
            return;
        }

        container.innerHTML = missions.map(m => `
            <div class="card mission-card" data-id="${m.id}">
                <div class="card-header">
                    <span class="card-title"><i class="fas fa-route"></i> ${m.name || 'Unnamed'}</span>
                    <span class="status-badge"><span class="status-dot ${m.status === 'planned' ? 'online' : ''}"></span>${m.status || 'planned'}</span>
                </div>
                <p class="text-sm text-muted">${m.description || 'No description'}</p>
                <div style="margin-top:12px;font-size:0.75rem;color:var(--text-muted)">
                    ${m.created_at ? new Date(m.created_at).toLocaleString() : ''}
                </div>
            </div>
        `).join('');

        document.getElementById('missions-count').textContent = `${missions.length} mission${missions.length !== 1 ? 's' : ''}`;
    } catch {
        container.innerHTML = '<div style="color:var(--danger);padding:20px">Error loading missions</div>';
    }
}
