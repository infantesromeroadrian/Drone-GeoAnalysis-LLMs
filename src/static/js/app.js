import { initDashboardView } from './views/dashboard-view.js';
import { initControlView, destroyControlView } from './views/control-view.js';
import { initAnalysisView } from './views/analysis-view.js';
import { initMissionsView } from './views/missions-view.js';
import API from './services/api.js';

const VIEWS = {
    dashboard: { init: initDashboardView, title: 'Dashboard' },
    control:   { init: initControlView, destroy: destroyControlView, title: 'Mission Control' },
    analysis:  { init: initAnalysisView, title: 'Image Analysis' },
    missions:  { init: initMissionsView, title: 'Missions Library' },
};

let currentView = null;
let telemetryInterval = null;

function navigate(viewName) {
    if (currentView === viewName) return;

    // Destroy previous view if needed
    if (currentView && VIEWS[currentView]?.destroy) VIEWS[currentView].destroy();

    // Hide all views, show target
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const el = document.getElementById(`view-${viewName}`);
    if (el) el.classList.add('active');

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navEl = document.querySelector(`.nav-item[data-view="${viewName}"]`);
    if (navEl) navEl.classList.add('active');

    // Update topbar title
    const titleEl = document.getElementById('topbar-title');
    if (titleEl) titleEl.textContent = VIEWS[viewName]?.title || viewName;

    // Init view
    if (VIEWS[viewName]?.init) VIEWS[viewName].init();

    currentView = viewName;
    window.location.hash = viewName;
}

function startTelemetryPolling() {
    updateTelemetry();
    telemetryInterval = setInterval(updateTelemetry, 2000);
}

async function updateTelemetry() {
    try {
        const data = await API.getTelemetry();
        if (!data.success) return;
        const t = data.telemetry;
        const el = (id) => document.getElementById(id);

        if (el('tb-battery')) el('tb-battery').textContent = `${t.battery || 0}%`;
        if (el('tb-altitude')) el('tb-altitude').textContent = `${(t.altitude || 0).toFixed(1)}m`;
        if (el('tb-gps')) el('tb-gps').textContent = `${(t.gps?.latitude || 0).toFixed(4)}, ${(t.gps?.longitude || 0).toFixed(4)}`;

        // Update control view telemetry if visible
        if (currentView === 'control') {
            const tItems = {
                'tel-battery': `${t.battery || 0}%`,
                'tel-altitude': `${(t.altitude || 0).toFixed(1)}m`,
                'tel-speed': `${(t.speed || 0).toFixed(1)} m/s`,
                'tel-gps': `${(t.gps?.latitude || 0).toFixed(4)}, ${(t.gps?.longitude || 0).toFixed(4)}`,
                'tel-signal': `${t.signal_strength || 0}%`,
                'tel-satellites': `${t.satellites || 0}`,
                'tel-heading': `${(t.heading || 0).toFixed(0)}deg`,
            };
            for (const [id, val] of Object.entries(tItems)) {
                const e = el(id);
                if (e) e.textContent = val;
            }
        }
    } catch { /* silently ignore telemetry errors */ }
}

document.addEventListener('DOMContentLoaded', () => {
    // Nav click handlers
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => navigate(item.dataset.view));
    });

    // Route from hash or default
    const hash = window.location.hash.replace('#', '');
    navigate(VIEWS[hash] ? hash : 'dashboard');

    // Start telemetry
    startTelemetryPolling();
});

window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '');
    if (VIEWS[hash]) navigate(hash);
});

export { navigate };
