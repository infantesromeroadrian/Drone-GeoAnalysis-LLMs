import API from '../services/api.js';

let map = null;
let droneMarker = null;
let missionLayer = null;
let trailLayer = null;
let trailPoints = [];
let initialized = false;
let currentMissionId = null;
let execPollInterval = null;
let currentHeading = 0;

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
    let lat = 40.4168, lng = -3.7038;
    try {
        const t = await API.getTelemetry();
        if (t.success && t.telemetry?.position) {
            const p = t.telemetry.position;
            if (p.latitude !== 0 || p.longitude !== 0) { lat = p.latitude; lng = p.longitude; }
        }
    } catch { /* defaults */ }

    map = L.map('map', { zoomControl: true }).setView([lat, lng], 14);

    // Tile layers
    const token = window.MAPBOX_TOKEN;
    const satellite = token
        ? L.tileLayer(`https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{z}/{x}/{y}?access_token=${token}`, {
            tileSize: 512, zoomOffset: -1, maxZoom: 20,
            attribution: '&copy; Mapbox &copy; OpenStreetMap',
          })
        : null;
    const streets = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '&copy; OpenStreetMap',
    });
    const dark = token
        ? L.tileLayer(`https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{z}/{x}/{y}?access_token=${token}`, {
            tileSize: 512, zoomOffset: -1, maxZoom: 20,
            attribution: '&copy; Mapbox',
          })
        : null;

    // Default to satellite if available
    (satellite || streets).addTo(map);

    // Layer toggle buttons
    const toggleDiv = document.createElement('div');
    toggleDiv.className = 'map-layer-toggle';
    const layers = [];
    if (satellite) layers.push(['Satellite', satellite]);
    layers.push(['Streets', streets]);
    if (dark) layers.push(['Dark', dark]);

    layers.forEach(([name, layer], i) => {
        const btn = document.createElement('button');
        btn.className = 'map-layer-btn' + (i === 0 ? ' active' : '');
        btn.textContent = name;
        btn.addEventListener('click', () => {
            layers.forEach(([, l]) => map.removeLayer(l));
            layer.addTo(map);
            toggleDiv.querySelectorAll('.map-layer-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
        toggleDiv.appendChild(btn);
    });
    document.querySelector('.control-center').appendChild(toggleDiv);

    // Drone marker with rotation
    droneMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'drone-marker',
            html: `<div class="drone-pulse" style="width:44px;height:44px;display:flex;align-items:center;justify-content:center">
                <svg viewBox="0 0 100 100" width="36" height="36" class="drone-svg">
                    <circle cx="50" cy="50" r="16" fill="#3B82F6" stroke="white" stroke-width="3"/>
                    <line x1="50" y1="34" x2="22" y2="16" stroke="white" stroke-width="3.5" stroke-linecap="round"/>
                    <line x1="50" y1="34" x2="78" y2="16" stroke="white" stroke-width="3.5" stroke-linecap="round"/>
                    <line x1="50" y1="66" x2="22" y2="84" stroke="white" stroke-width="3.5" stroke-linecap="round"/>
                    <line x1="50" y1="66" x2="78" y2="84" stroke="white" stroke-width="3.5" stroke-linecap="round"/>
                    <circle cx="22" cy="16" r="9" fill="rgba(59,130,246,0.3)" stroke="#60A5FA" stroke-width="2"/>
                    <circle cx="78" cy="16" r="9" fill="rgba(59,130,246,0.3)" stroke="#60A5FA" stroke-width="2"/>
                    <circle cx="22" cy="84" r="9" fill="rgba(59,130,246,0.3)" stroke="#60A5FA" stroke-width="2"/>
                    <circle cx="78" cy="84" r="9" fill="rgba(59,130,246,0.3)" stroke="#60A5FA" stroke-width="2"/>
                    <polygon points="50,38 46,50 50,48 54,50" fill="white" opacity="0.9"/>
                </svg>
            </div>`,
            iconSize: [44, 44],
            iconAnchor: [22, 22],
        }),
    }).addTo(map);

    missionLayer = L.layerGroup().addTo(map);
    trailLayer = L.layerGroup().addTo(map);
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
                <button class="btn btn-sm btn-primary" data-sim-id="${p.id}">Start</button>
            </div>
        `).join('');

        list.querySelectorAll('[data-sim-id]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const r = await API.startSim(btn.dataset.simId);
                showToast(r.success ? 'Simulation started' : `Error: ${r.error}`);
            });
        });
    });
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
    trailPoints = [];
    if (trailLayer) trailLayer.clearLayers();
    startExecPolling();

    const abortBtn = document.getElementById('btn-abort-exec');
    if (abortBtn) {
        const newBtn = abortBtn.cloneNode(true);
        abortBtn.parentNode.replaceChild(newBtn, abortBtn);
        newBtn.addEventListener('click', async () => {
            const a = await API.abortExecution();
            showToast(a.success ? 'Mission aborted' : a.error);
        });
    }
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

        // Move drone marker + trail
        if (s.position && droneMarker) {
            const pos = [s.position.latitude, s.position.longitude];
            droneMarker.setLatLng(pos);

            // Add trail point
            trailPoints.push(pos);
            if (trailPoints.length > 1 && trailLayer) {
                trailLayer.clearLayers();
                L.polyline(trailPoints, {
                    color: '#10B981', weight: 3, opacity: 0.7,
                    dashArray: null,
                }).addTo(trailLayer);
            }

            // Rotate drone icon toward movement direction
            if (trailPoints.length >= 2) {
                const prev = trailPoints[trailPoints.length - 2];
                const dx = pos[1] - prev[1];
                const dy = pos[0] - prev[0];
                const angle = Math.atan2(dx, dy) * (180 / Math.PI);
                const svgEl = document.querySelector('.drone-svg');
                if (svgEl) svgEl.style.transform = `rotate(${-angle}deg)`;
            }
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
