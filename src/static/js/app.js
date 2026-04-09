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

function navigate(viewName) {
    if (currentView === viewName) return;
    if (currentView && VIEWS[currentView]?.destroy) VIEWS[currentView].destroy();

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const el = document.getElementById(`view-${viewName}`);
    if (el) el.classList.add('active');

    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${viewName}"]`)?.classList.add('active');

    const titleEl = document.getElementById('topbar-title');
    if (titleEl) titleEl.textContent = VIEWS[viewName]?.title || viewName;

    if (VIEWS[viewName]?.init) VIEWS[viewName].init();
    currentView = viewName;
}

async function updateTelemetry() {
    try {
        const data = await API.getTelemetry();
        if (!data.success || !data.telemetry) return;
        const t = data.telemetry;
        const $ = (id) => document.getElementById(id);

        const bat = t.battery?.level ?? 0;
        const alt = t.position?.altitude ?? 0;
        const lat = t.position?.latitude ?? 0;
        const lng = t.position?.longitude ?? 0;
        const spd = Math.sqrt((t.speed?.vx||0)**2 + (t.speed?.vy||0)**2);
        const sig = t.signal_strength ?? 0;
        const sats = t.gps?.satellites ?? 0;
        const hdg = t.attitude?.yaw ?? 0;

        // Top bar
        if ($('tb-battery')) $('tb-battery').textContent = `${bat}%`;
        if ($('tb-altitude')) $('tb-altitude').textContent = `${alt.toFixed(1)}m`;
        if ($('tb-gps')) $('tb-gps').textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

        // Control view telemetry panel
        if (currentView === 'control') {
            if ($('tel-battery')) $('tel-battery').textContent = `${bat}%`;
            if ($('tel-altitude')) $('tel-altitude').textContent = `${alt.toFixed(1)}m`;
            if ($('tel-speed')) $('tel-speed').textContent = `${spd.toFixed(1)} m/s`;
            if ($('tel-gps')) $('tel-gps').textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            if ($('tel-signal')) $('tel-signal').textContent = `${sig}dBm`;
            if ($('tel-satellites')) $('tel-satellites').textContent = `${sats}`;
            if ($('tel-heading')) $('tel-heading').textContent = `${hdg.toFixed(0)}deg`;
        }
    } catch { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => {
            window.location.hash = item.dataset.view;
        });
    });

    const hash = window.location.hash.replace('#', '');
    navigate(VIEWS[hash] ? hash : 'dashboard');

    updateTelemetry();
    setInterval(updateTelemetry, 2000);
});

window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '');
    if (VIEWS[hash]) navigate(hash);
});
