import API from '../services/api.js';

let map = null;
let droneMarker = null;
let missionLayer = null;
let initialized = false;
let currentMissionId = null;
let execPollInterval = null;

export async function initControlView() {
    if (!initialized) {
        initialized = true;
        await setupMap();
        setupDroneControls();
        setupMissionTabs();
        setupCartography();
        setupLLMMission();
        setupSimulation();
        loadMissions();
    }
    if (map) setTimeout(() => map.invalidateSize(), 100);
}

export function destroyControlView() {
    // Keep map alive but don't re-init
}

async function setupMap() {
    // Get drone position before creating map
    let lat = 40.4168, lng = -3.7038;
    try {
        const t = await API.getTelemetry();
        if (t.success && t.telemetry?.position) {
            const p = t.telemetry.position;
            if (p.latitude !== 0 || p.longitude !== 0) {
                lat = p.latitude;
                lng = p.longitude;
            }
        }
    } catch { /* use defaults */ }

    map = L.map('map', { zoomControl: true }).setView([lat, lng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19,
    }).addTo(map);

    droneMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'drone-icon',
            html: '<div style="background:#3B82F6;width:24px;height:24px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.4)"></div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        }),
    }).addTo(map).bindPopup('Drone');

    missionLayer = L.layerGroup().addTo(map);
}

function setupDroneControls() {
    onClick('btn-connect', async () => {
        const r = await API.connectDrone();
        showToast(r.success ? 'Drone connected' : `Error: ${r.error}`);
    });
    onClick('btn-disconnect', async () => {
        const r = await API.disconnectDrone();
        showToast(r.success ? 'Drone disconnected' : `Error: ${r.error}`);
    });
    onClick('btn-takeoff', async () => {
        const alt = parseFloat(document.getElementById('takeoff-alt')?.value || 30);
        const r = await API.takeoff(alt);
        showToast(r.success ? `Takeoff to ${alt}m` : `Error: ${r.error}`);
    });
    onClick('btn-land', async () => {
        const r = await API.land();
        showToast(r.success ? 'Landing initiated' : `Error: ${r.error}`);
    });
}

function setupMissionTabs() {
    document.querySelectorAll('#control-tabs .tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('#control-tabs .tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('#control-panels .tab-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const panel = document.getElementById(`panel-${tab.dataset.tab}`);
            if (panel) panel.classList.add('active');
        });
    });
}

function setupCartography() {
    const fileInput = document.getElementById('carto-file');
    const uploadBtn = document.getElementById('btn-upload-carto');

    uploadBtn?.addEventListener('click', () => fileInput?.click());

    fileInput?.addEventListener('change', async () => {
        const file = fileInput.files[0];
        if (!file) return;
        const areaName = document.getElementById('carto-area-name')?.value || file.name.replace('.geojson', '');
        const form = new FormData();
        form.append('cartography_file', file);
        form.append('area_name', areaName);

        const r = await API.uploadCartography(form);
        showToast(r.success ? `Area "${areaName}" loaded` : `Error: ${r.error}`);
        if (r.success) {
            refreshAreaSelect();
            if (r.center_coordinates) {
                map.setView([r.center_coordinates.latitude, r.center_coordinates.longitude], 14);
                droneMarker.setLatLng([r.center_coordinates.latitude, r.center_coordinates.longitude]);
            }
        }
    });
}

async function refreshAreaSelect() {
    const select = document.getElementById('mission-area');
    if (!select) return;
    const data = await API.getLoadedAreas();
    const areas = data.areas || [];
    select.innerHTML = '<option value="">No area selected</option>' +
        areas.map(a => `<option value="${a.name}">${a.name} (${a.boundaries_count} boundaries, ${a.poi_count} POIs)</option>`).join('');
}

function setupLLMMission() {
    onClick('btn-create-mission', async () => {
        const cmd = document.getElementById('mission-command')?.value;
        const area = document.getElementById('mission-area')?.value;
        if (!cmd) { showToast('Enter a command first'); return; }

        const btn = document.getElementById('btn-create-mission');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Planning...';

        try {
            const r = await API.createLLMMission(cmd, area || undefined);
            if (r.success && r.mission) {
                showMissionOnMap(r.mission);
                showMissionModal(r.mission);
                loadMissions();
            } else {
                showToast(`Error: ${r.error || 'Unknown error'}`);
            }
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Create AI Mission';
        }
    });
}

function showMissionOnMap(mission) {
    missionLayer.clearLayers();
    const waypoints = mission.waypoints || [];
    if (!waypoints.length) return;

    const coords = waypoints.map(w => [w.latitude, w.longitude]);

    // Polyline
    L.polyline(coords, { color: '#3B82F6', weight: 3, opacity: 0.8, dashArray: '8,8' }).addTo(missionLayer);

    // Markers
    waypoints.forEach((w, i) => {
        L.circleMarker([w.latitude, w.longitude], {
            radius: 8, fillColor: i === 0 ? '#10B981' : i === waypoints.length - 1 ? '#EF4444' : '#3B82F6',
            color: 'white', weight: 2, fillOpacity: 0.9,
        }).bindPopup(`<b>WP ${i + 1}</b><br>Alt: ${w.altitude}m<br>${w.action || 'navigate'}<br>${w.description || ''}`).addTo(missionLayer);
    });

    map.fitBounds(L.latLngBounds(coords).pad(0.2));
}

function showMissionModal(mission) {
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    if (!overlay || !body) return;

    const wps = mission.waypoints || [];
    body.innerHTML = `
        <div class="mb-12"><strong>Mission:</strong> ${mission.mission_name || 'Unnamed'}</div>
        <div class="mb-12"><strong>Command:</strong> ${mission.original_command || ''}</div>
        <div class="mb-12"><strong>Waypoints:</strong> ${wps.length}</div>
        <div style="max-height:200px;overflow-y:auto">
            ${wps.map((w, i) => `<div class="telemetry-item"><span class="telemetry-label">${i + 1}. ${w.action || 'navigate'}</span><span class="telemetry-value">${w.latitude.toFixed(4)}, ${w.longitude.toFixed(4)} @ ${w.altitude}m</span></div>`).join('')}
        </div>
        ${mission.safety_warnings?.length ? `<div style="margin-top:12px;color:var(--warning)"><i class="fas fa-exclamation-triangle"></i> ${mission.safety_warnings.join(', ')}</div>` : ''}
    `;
    overlay.classList.add('active');

    currentMissionId = mission.id;

    document.getElementById('btn-modal-close')?.addEventListener('click', () => overlay.classList.remove('active'), { once: true });
    document.getElementById('btn-modal-accept')?.addEventListener('click', () => {
        overlay.classList.remove('active');
        showToast('Mission accepted');
    }, { once: true });
    document.getElementById('btn-modal-execute')?.addEventListener('click', () => {
        overlay.classList.remove('active');
        executeMission(mission.id);
    }, { once: true });
}

async function loadMissions() {
    const list = document.getElementById('mission-list');
    if (!list) return;
    try {
        const data = await API.getLLMMissions();
        const missions = data.missions || [];
        if (!missions.length) {
            list.innerHTML = '<div class="text-muted text-sm">No missions created yet</div>';
            return;
        }
        list.innerHTML = missions.slice(0, 8).map(m => `
            <div class="mission-item" data-id="${m.id}">
                <div>
                    <div class="mission-item-name">${m.name}</div>
                    <div class="mission-item-meta">${m.status} - ${m.created_at ? new Date(m.created_at).toLocaleString() : ''}</div>
                </div>
            </div>
        `).join('');
    } catch { list.innerHTML = '<div class="text-muted text-sm">Error loading missions</div>'; }
}

function setupSimulation() {
    onClick('btn-load-sims', async () => {
        const data = await API.getSimPaths();
        const list = document.getElementById('sim-list');
        if (!list) return;
        const paths = data.paths || [];
        list.innerHTML = paths.map(p => `
            <div class="mission-item" data-sim-id="${p.id}">
                <div>
                    <div class="mission-item-name">${p.name}</div>
                    <div class="mission-item-meta">${p.waypoints.length} waypoints</div>
                </div>
                <button class="btn btn-sm btn-primary" onclick="window._startSim('${p.id}')">Start</button>
            </div>
        `).join('');
    });

    window._startSim = async (id) => {
        const r = await API.startSim(id);
        showToast(r.success ? 'Simulation started' : `Error: ${r.error}`);
    };
}

// Helpers
function onClick(id, handler) {
    document.getElementById(id)?.addEventListener('click', handler);
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('active');
    setTimeout(() => toast.classList.remove('active'), 3000);
}

// ---- Mission Execution ----

async function executeMission(missionId) {
    const r = await API.executeMission(missionId);
    if (!r.success) {
        showToast(`Error: ${r.error}`);
        return;
    }
    showToast(`Mission executing: ${r.waypoints} waypoints`);
    document.getElementById('exec-bar')?.classList.remove('hidden');
    startExecPolling();

    onClick('btn-abort-exec', async () => {
        const a = await API.abortExecution();
        showToast(a.success ? 'Mission aborted' : a.error);
    });
}

function startExecPolling() {
    if (execPollInterval) clearInterval(execPollInterval);
    execPollInterval = setInterval(pollExecStatus, 500);
}

function stopExecPolling() {
    if (execPollInterval) { clearInterval(execPollInterval); execPollInterval = null; }
    document.getElementById('exec-bar')?.classList.add('hidden');
}

async function pollExecStatus() {
    try {
        const s = await API.getExecStatus();

        // Update progress bar
        const bar = document.getElementById('exec-progress');
        const label = document.getElementById('exec-label');
        const wp = document.getElementById('exec-wp');
        const eta = document.getElementById('exec-eta');

        if (bar) bar.style.width = `${s.progress_pct || 0}%`;
        if (wp) wp.textContent = `WP ${s.current_waypoint || 0}/${s.total_waypoints || 0}`;
        if (eta) eta.textContent = `ETA ${Math.round(s.eta_seconds || 0)}s`;

        // Move drone marker
        if (s.position && droneMarker) {
            droneMarker.setLatLng([s.position.latitude, s.position.longitude]);
        }

        // Status label
        if (label) {
            if (s.status === 'flying') label.textContent = 'Flying...';
            else if (s.status === 'completed') label.textContent = 'Mission completed!';
            else if (s.status === 'aborted') label.textContent = 'Mission aborted';
            else if (s.status === 'error') label.textContent = 'Execution error';
        }

        // Stop polling on terminal states
        if (s.status === 'completed' || s.status === 'aborted' || s.status === 'error') {
            showToast(s.status === 'completed' ? 'Mission completed!' : `Mission ${s.status}`);
            setTimeout(stopExecPolling, 2000);
        }
    } catch { /* ignore polling errors */ }
}
