import API from '../services/api.js';
import { navigate } from '../app.js';

let loaded = false;

export async function initDashboardView() {
    if (loaded) return;
    loaded = true;

    // Load stats
    try {
        const [missions, yolo, areas] = await Promise.allSettled([
            API.getLLMMissions(),
            API.getYOLOInfo(),
            API.getLoadedAreas(),
        ]);

        const mCount = missions.status === 'fulfilled' ? (missions.value.missions?.length || 0) : 0;
        const yoloOk = yolo.status === 'fulfilled' && yolo.value.is_initialized;
        const areaCount = areas.status === 'fulfilled' ? (areas.value.areas?.length || 0) : 0;

        setText('stat-missions', mCount);
        setText('stat-areas', areaCount);
        setText('stat-yolo', yoloOk ? 'Online' : 'Offline');
    } catch { /* ignore */ }

    // Load recent missions
    try {
        const data = await API.getLLMMissions();
        const list = document.getElementById('recent-missions');
        if (!list) return;

        if (!data.missions || data.missions.length === 0) {
            list.innerHTML = '<div class="text-muted text-sm" style="padding:12px">No missions yet. Go to Mission Control to create one.</div>';
            return;
        }

        list.innerHTML = data.missions.slice(0, 5).map(m => `
            <div class="mission-item">
                <div>
                    <div class="mission-item-name">${m.name || 'Unnamed'}</div>
                    <div class="mission-item-meta">${m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}</div>
                </div>
                <span class="status-badge"><span class="status-dot ${m.status === 'planned' ? 'online' : ''}"></span>${m.status || 'planned'}</span>
            </div>
        `).join('');
    } catch { /* ignore */ }

    // Quick action buttons
    document.getElementById('qa-control')?.addEventListener('click', () => navigate('control'));
    document.getElementById('qa-analysis')?.addEventListener('click', () => navigate('analysis'));
    document.getElementById('qa-missions')?.addEventListener('click', () => navigate('missions'));
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}
