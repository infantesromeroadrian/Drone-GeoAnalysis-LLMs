const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) return { success: false, error: `HTTP ${res.status}` };
        return res.json();
    },

    async post(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) return { success: false, error: `HTTP ${res.status}` };
        return res.json();
    },

    async postForm(url, formData) {
        const res = await fetch(url, { method: 'POST', body: formData });
        if (!res.ok) return { success: false, error: `HTTP ${res.status}` };
        return res.json();
    },

    // Drone
    connectDrone: ()    => API.post('/api/drone/connect'),
    disconnectDrone: () => API.post('/api/drone/disconnect'),
    takeoff: (alt)      => API.post('/api/drone/takeoff', { altitude: alt }),
    land: ()            => API.post('/api/drone/land'),
    getTelemetry: ()    => API.get('/api/drone/telemetry'),
    getSimPaths: ()     => API.get('/api/drone/simulate/paths'),
    startSim: (id)      => API.post('/api/drone/simulate/start', { path_id: id }),

    // Missions
    getMissions: ()      => API.get('/api/missions/'),
    getLLMMissions: ()   => API.get('/api/missions/llm/list'),
    createLLMMission: (cmd, area) => API.post('/api/missions/llm/create', { command: cmd, area_name: area }),
    startMission: (id)   => API.post('/api/missions/start', { id }),
    abortMission: ()     => API.post('/api/missions/abort'),
    executeMission: (id) => API.post('/api/missions/execute', { mission_id: id }),
    abortExecution: ()   => API.post('/api/missions/execution/abort'),
    getExecStatus: ()    => API.get('/api/missions/execution/status'),
    getLoadedAreas: ()   => API.get('/api/missions/cartography/areas'),
    uploadCartography: (form) => API.postForm('/api/missions/cartography/upload', form),

    // Analysis
    analyzeImage: (form)    => API.postForm('/analyze', form),
    analyzeYOLO: (form)     => API.postForm('/analyze_yolo', form),
    getYOLOInfo: ()         => API.get('/yolo/model_info'),

    // Chat
    askQuestion: (sessionId, question) => API.post('/chat/question', { session_id: sessionId, question }),
    getChatHistory: (sid) => API.get(`/chat/history?session_id=${sid}`),
    getSuggestions: (sid) => API.get(`/chat/suggested_questions?session_id=${sid}`),

    // Geo
    addReference: ()         => API.post('/api/geo/reference/add'),
    createTarget: ()         => API.post('/api/geo/target/create'),
    detectChanges: ()        => API.post('/api/geo/changes/detect'),
    calculatePosition: ()    => API.post('/api/geo/position/calculate'),
};

export default API;
