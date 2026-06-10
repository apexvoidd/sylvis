/* ==========================================================================
   S.Y.L.V.I.S. SYSTEM FRONTEND CONTROLLER
   Optimized for low-end systems. Handles local parsing, Web Speech APIs,
   direct Gemini/Ollama integrations, and UI updates.
   ========================================================================== */

const API_BASE = "http://127.0.0.1:5000/api";

// Core App State
const state = {
    apiKey: localStorage.getItem("jarvis_gemini_key") || "",
    nimApiKey: localStorage.getItem("jarvis_nim_key") || "",
    nimModelName: localStorage.getItem("jarvis_nim_model") || "meta/llama-3.1-8b-instruct",
    ollamaUrl: localStorage.getItem("jarvis_ollama_url") || "http://localhost:11434",
    proxyUrl: localStorage.getItem("jarvis_proxy_url") || "",
    proxyKey: localStorage.getItem("jarvis_proxy_key") || "",
    proxyModel: localStorage.getItem("jarvis_proxy_model") || "",
    aiEngine: "fcc",
    ttsEnabled: localStorage.getItem("jarvis_tts_enabled") !== "false",
    selectedVoiceName: localStorage.getItem("jarvis_selected_voice") || "",
    lowResourceMode: localStorage.getItem("jarvis_low_resource") === "true",
    isListening: false,
    isSpeaking: false,
    isProcessing: false,
    metricsInterval: null,
    chatHistory: [],
    systemContext: { os: "Windows", username: "User", home_path: "", desktop_path: "", cwd: "" },
    autoApprove: localStorage.getItem("jarvis_auto_approve") === "true",
    agentRetries: 0,
    maxAgentRetries: 3,
    agentGoal: "",
    lastCommandOutput: "",
    lastRunDescription: "",
    typecastKey: localStorage.getItem("sylvis_typecast_key") || "",
    typecastVoiceId: localStorage.getItem("sylvis_typecast_voice") || "",
    ttsProvider: localStorage.getItem("sylvis_tts_provider") || "typecast",
    elevenlabsKey: localStorage.getItem("sylvis_elevenlabs_key") || "",
    elevenlabsVoiceId: localStorage.getItem("sylvis_elevenlabs_voice") || "",
    elevenlabsModelId: localStorage.getItem("sylvis_elevenlabs_model") || "eleven_multilingual_v2"
};

// UI Elements
const els = {
    cpuVal: document.getElementById("cpu-value"),
    cpuBar: document.getElementById("cpu-bar"),
    cpuFreq: document.getElementById("cpu-freq"),
    memVal: document.getElementById("mem-value"),
    memBar: document.getElementById("mem-bar"),
    memUsage: document.getElementById("mem-usage"),
    diskVal: document.getElementById("disk-value"),
    diskBar: document.getElementById("disk-bar"),
    diskUsage: document.getElementById("disk-usage"),
    uptimeVal: document.getElementById("uptime-value"),
    batteryVal: document.getElementById("battery-value"),
    processList: document.getElementById("process-list"),
    
    arcReactor: document.getElementById("arc-reactor"),
    reactorSymbol: document.getElementById("reactor-status-symbol"),
    canvas: document.getElementById("visualizer-canvas"),
    voiceStatus: document.getElementById("voice-status-text"),
    speechPreview: document.getElementById("speech-preview-box"),
    
    voiceBtn: document.getElementById("voice-btn"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    terminal: document.getElementById("terminal-output"),
    
    volumeRange: document.getElementById("volume-range"),
    volumeLabel: document.getElementById("volume-level-label"),
    muteBtn: document.getElementById("mute-toggle-btn"),
    
    settingsModal: document.getElementById("settings-modal"),
    openSettingsBtn: document.getElementById("open-settings-btn"),
    closeSettingsBtn: document.getElementById("close-settings-btn"),
    cancelSettingsBtn: document.getElementById("cancel-settings-btn"),
    saveSettingsBtn: document.getElementById("save-settings-btn"),
    
    geminiKey: document.getElementById("gemini-key-input"),
    nimKey: document.getElementById("nim-key-input"),
    nimModel: document.getElementById("nim-model-input"),
    ollamaUrlInput: document.getElementById("ollama-url-input"),
    aiEngineSelect: document.getElementById("ai-engine-select"),
    voiceSelect: document.getElementById("voice-select"),
    ttsToggle: document.getElementById("tts-feedback-toggle"),
    lowResourceToggle: document.getElementById("low-resource-toggle"),
    autoApproveToggle: document.getElementById("auto-approve-toggle"),
    proxyUrl: document.getElementById("proxy-url-input"),
    proxyKey: document.getElementById("proxy-key-input"),
    proxyModel: document.getElementById("proxy-model-input"),
    typecastKey: document.getElementById("typecast-key-input"),
    typecastVoice: document.getElementById("typecast-voice-input"),
    ttsProviderSelect: document.getElementById("tts-provider-select"),
    elevenlabsKey: document.getElementById("elevenlabs-key-input"),
    elevenlabsVoice: document.getElementById("elevenlabs-voice-input"),
    elevenlabsModel: document.getElementById("elevenlabs-model-input"),
    typecastKeyGroup: document.getElementById("typecast-key-group"),
    typecastVoiceGroup: document.getElementById("typecast-voice-group"),
    elevenlabsKeyGroup: document.getElementById("elevenlabs-key-group"),
    elevenlabsVoiceGroup: document.getElementById("elevenlabs-voice-group"),
    elevenlabsModelGroup: document.getElementById("elevenlabs-model-group"),
    browserVoiceGroup: document.getElementById("browser-voice-group"),
    voiceSelectLabel: document.getElementById("voice-select-label"),
    widgetKeyboardBtn: document.getElementById("widget-keyboard-btn"),
    closeConsoleBtn: document.getElementById("close-console-panel-btn"),
    consolePanel: document.getElementById("console-panel"),
    
    // Security Authorization Modal Elements
    securityModal: document.getElementById("security-modal"),
    abortCommandBtn: document.getElementById("abort-command-btn"),
    approveCommandBtn: document.getElementById("approve-command-btn"),
    securityActionVal: document.getElementById("security-action-val"),
    securityDescVal: document.getElementById("security-desc-val"),
    securityCodeVal: document.getElementById("security-code-val")
};

// Canvas drawing state
let canvasCtx = els.canvas.getContext("2d");
let animationFrameId = null;
let simulatedAudioData = 0;

// Initialize Speech Web API components
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
} else {
    logTerminal("Speech Recognition API not supported in this browser. Please use Chrome/Edge.", "error");
}

// ── INITIALIZATION ──
document.addEventListener("DOMContentLoaded", () => {
    initSettingsUI();
    initEventListeners();
    initSpeechVoices();
    applyLowResourceMode(state.lowResourceMode);
    checkBackendConnection();
    spawnParticles();
    
    // Start Metrics Polling
    startMetricsPolling();
});

// Floating anime particles
function spawnParticles() {
    const container = document.getElementById('particles-container');
    if (!container || state.lowResourceMode) return;
    const count = 28;
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = `${Math.random() * 100}%`;
        p.style.bottom = `${Math.random() * 30}px`;
        p.style.animationDelay = `${Math.random() * 8}s`;
        p.style.animationDuration = `${6 + Math.random() * 6}s`;
        container.appendChild(p);
    }
}

// Check if Flask backend is online
function checkBackendConnection() {
    logTerminal("[SYS] Connecting to local PC backend...", "system");
    fetch(`${API_BASE}/ping`)
        .then(res => res.json())
        .then(data => {
            logTerminal(`[SYS] ✦ Connection established. Hello, ${data.username || "User"}!`, "action");
            state.systemContext = data;
            document.getElementById("system-status-banner").classList.remove("offline");
            document.getElementById("system-status-banner").querySelector(".status-text").textContent = "ONLINE";
            updateVolumeUI();
        })
        .catch(err => {
            logTerminal("[SYS] ⚠ Could not connect to local backend. Double-click run.bat to start.", "error");
            document.getElementById("system-status-banner").classList.add("offline");
            document.getElementById("system-status-banner").querySelector(".status-text").textContent = "DISCONNECTED";
        });
}

// ── CONFIGURATION & SETTINGS ──
function initSettingsUI() {
    els.geminiKey.value = state.apiKey;
    els.nimKey.value = state.nimApiKey;
    els.nimModel.value = state.nimModelName;
    els.ollamaUrlInput.value = state.ollamaUrl;
    if (els.proxyUrl) els.proxyUrl.value = state.proxyUrl;
    if (els.proxyKey) els.proxyKey.value = state.proxyKey;
    if (els.proxyModel) els.proxyModel.value = state.proxyModel;
    els.aiEngineSelect.value = state.aiEngine;
    els.ttsToggle.checked = state.ttsEnabled;
    els.lowResourceToggle.checked = state.lowResourceMode;
    els.autoApproveToggle.checked = state.autoApprove;
    if (els.typecastKey) els.typecastKey.value = state.typecastKey;
    if (els.typecastVoice) els.typecastVoice.value = state.typecastVoiceId;
    if (els.ttsProviderSelect) els.ttsProviderSelect.value = state.ttsProvider;
    if (els.elevenlabsKey) els.elevenlabsKey.value = state.elevenlabsKey;
    if (els.elevenlabsVoice) els.elevenlabsVoice.value = state.elevenlabsVoiceId;
    if (els.elevenlabsModel) els.elevenlabsModel.value = state.elevenlabsModelId;
    updateSettingsVisibility();
}

function updateSettingsVisibility() {
    const provider = els.ttsProviderSelect ? els.ttsProviderSelect.value : "typecast";
    
    if (els.typecastKeyGroup) els.typecastKeyGroup.style.display = (provider === "typecast") ? "block" : "none";
    if (els.typecastVoiceGroup) els.typecastVoiceGroup.style.display = (provider === "typecast") ? "block" : "none";
    
    if (els.elevenlabsKeyGroup) els.elevenlabsKeyGroup.style.display = (provider === "elevenlabs") ? "block" : "none";
    if (els.elevenlabsVoiceGroup) els.elevenlabsVoiceGroup.style.display = (provider === "elevenlabs") ? "block" : "none";
    if (els.elevenlabsModelGroup) els.elevenlabsModelGroup.style.display = (provider === "elevenlabs") ? "block" : "none";
    
    if (els.browserVoiceGroup) {
        if (provider === "browser") {
            els.browserVoiceGroup.style.display = "block";
            if (els.voiceSelectLabel) els.voiceSelectLabel.textContent = "🔊 Active Browser Voice";
        } else {
            els.browserVoiceGroup.style.display = "block"; // Keep visible as fallback
            if (els.voiceSelectLabel) els.voiceSelectLabel.textContent = "🔊 Fallback Browser Voice (if no key)";
        }
    }
}

function initEventListeners() {
    // Widget and Console panel triggers
    if (els.widgetKeyboardBtn) {
        els.widgetKeyboardBtn.addEventListener("click", () => {
            if (els.consolePanel.style.display === "none") {
                expandConsole();
                setTimeout(() => els.chatInput.focus(), 150);
            } else {
                collapseConsole();
            }
        });
    }
    if (els.closeConsoleBtn) {
        els.closeConsoleBtn.addEventListener("click", collapseConsole);
    }

    // Settings modal triggers
    els.openSettingsBtn.addEventListener("click", () => {
        updateSettingsVisibility();
        els.settingsModal.classList.add("open");
    });
    els.closeSettingsBtn.addEventListener("click", () => els.settingsModal.classList.remove("open"));
    els.cancelSettingsBtn.addEventListener("click", () => els.settingsModal.classList.remove("open"));
    els.saveSettingsBtn.addEventListener("click", saveSettings);

    if (els.ttsProviderSelect) {
        els.ttsProviderSelect.addEventListener("change", updateSettingsVisibility);
    }
    
    // Low resource toggle
    els.lowResourceToggle.addEventListener("change", (e) => {
        applyLowResourceMode(e.target.checked);
    });

    // Auto-Approve toggle listener
    els.autoApproveToggle.addEventListener("change", (e) => {
        state.autoApprove = e.target.checked;
        localStorage.setItem("jarvis_auto_approve", state.autoApprove);
        logTerminal(`[SYS] Auto-Approve mode ${state.autoApprove ? "ENABLED" : "DISABLED"}.`, "system");
    });

    // Voice triggers
    if (recognition) {
        els.voiceBtn.addEventListener("click", toggleListening);
        recognition.onstart = handleSpeechStart;
        recognition.onresult = handleSpeechResult;
        recognition.onerror = handleSpeechError;
        recognition.onend = handleSpeechEnd;
    } else {
        els.voiceBtn.disabled = true;
        els.voiceBtn.title = "Microphone speech recognition not supported on this browser";
    }

    // Keyboard Hotkey: Spacebar to toggle listening (only when not typing in chatInput)
    window.addEventListener("keydown", (e) => {
        if (e.code === "Space" && document.activeElement !== els.chatInput && document.activeElement !== els.geminiKey && document.activeElement !== els.ollamaUrlInput) {
            e.preventDefault();
            toggleListening();
        }
    });

    // Chat form submit
    els.chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = els.chatInput.value.trim();
        if (text) {
            processQuery(text);
            els.chatInput.value = "";
        }
    });

    // Master Volume control triggers
    els.volumeRange.addEventListener("input", (e) => {
        const value = e.target.value;
        els.volumeLabel.textContent = `${value}%`;
    });
    
    els.volumeRange.addEventListener("change", (e) => {
        setVolume(e.target.value);
    });

    els.muteBtn.addEventListener("click", toggleMute);

    // Quick control buttons
    document.querySelectorAll(".control-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const btnEl = e.currentTarget;
            const action = btnEl.dataset.action;
            const target = btnEl.dataset.target;
            if (action === "launch") {
                launchApp(target);
            } else if (action === "lock") {
                lockWorkstation();
            }
        });
    });

    // Security Modal Actions
    els.abortCommandBtn.addEventListener("click", handleCommandAbort);
    els.approveCommandBtn.addEventListener("click", handleCommandApprove);
}

function saveSettings() {
    state.apiKey = els.geminiKey.value.trim();
    state.nimApiKey = els.nimKey.value.trim();
    state.nimModelName = els.nimModel.value.trim();
    state.ollamaUrl = els.ollamaUrlInput.value.trim();
    if (els.proxyUrl) state.proxyUrl = els.proxyUrl.value.trim();
    if (els.proxyKey) state.proxyKey = els.proxyKey.value.trim();
    if (els.proxyModel) state.proxyModel = els.proxyModel.value.trim();
    state.aiEngine = "fcc";
    state.ttsEnabled = els.ttsToggle.checked;
    state.selectedVoiceName = els.voiceSelect.value;
    if (els.typecastKey) state.typecastKey = els.typecastKey.value.trim();
    if (els.typecastVoice) state.typecastVoiceId = els.typecastVoice.value.trim();
    if (els.ttsProviderSelect) state.ttsProvider = els.ttsProviderSelect.value;
    if (els.elevenlabsKey) state.elevenlabsKey = els.elevenlabsKey.value.trim();
    if (els.elevenlabsVoice) state.elevenlabsVoiceId = els.elevenlabsVoice.value.trim();
    if (els.elevenlabsModel) state.elevenlabsModelId = els.elevenlabsModel.value.trim();

    localStorage.setItem("jarvis_gemini_key", state.apiKey);
    localStorage.setItem("jarvis_nim_key", state.nimApiKey);
    localStorage.setItem("jarvis_nim_model", state.nimModelName);
    localStorage.setItem("jarvis_ollama_url", state.ollamaUrl);
    localStorage.setItem("jarvis_proxy_url", state.proxyUrl);
    localStorage.setItem("jarvis_proxy_key", state.proxyKey);
    localStorage.setItem("jarvis_proxy_model", state.proxyModel);
    localStorage.setItem("jarvis_ai_engine", state.aiEngine);
    localStorage.setItem("jarvis_tts_enabled", state.ttsEnabled);
    localStorage.setItem("jarvis_selected_voice", state.selectedVoiceName);
    localStorage.setItem("sylvis_typecast_key", state.typecastKey);
    localStorage.setItem("sylvis_typecast_voice", state.typecastVoiceId);
    localStorage.setItem("sylvis_tts_provider", state.ttsProvider);
    localStorage.setItem("sylvis_elevenlabs_key", state.elevenlabsKey);
    localStorage.setItem("sylvis_elevenlabs_voice", state.elevenlabsVoiceId);
    localStorage.setItem("sylvis_elevenlabs_model", state.elevenlabsModelId);

    logTerminal(`[SYS] Settings saved. Brain: ${state.aiEngine.toUpperCase()} | Provider: ${state.ttsProvider.toUpperCase()} | Voice: ${state.ttsProvider === 'typecast' ? (state.typecastKey ? 'Typecast 🌸' : 'Browser') : (state.ttsProvider === 'elevenlabs' ? (state.elevenlabsKey ? 'Eleven Labs 🔑' : 'Browser') : 'Browser')}`, "system");
    els.settingsModal.classList.remove("open");
}

// Apply resource-saving features
function applyLowResourceMode(enabled) {
    state.lowResourceMode = enabled;
    localStorage.setItem("jarvis_low_resource", enabled);

    if (enabled) {
        document.body.classList.add("low-res-active");
        logTerminal("[SYS] Low Resource Mode activated. UI effects reduced.", "system");
        
        // Stop canvas animation loops completely to save GPU cycles
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
        
        // Clear canvas contents
        canvasCtx.clearRect(0, 0, els.canvas.width, els.canvas.height);
    } else {
        document.body.classList.remove("low-res-active");
        logTerminal("[SYS] Standard Graphics Mode active.", "system");
        
        // Restart canvas animation visualizer loop
        drawVisualizerLoop();
    }

    // Re-trigger polling metrics with updated intervals
    startMetricsPolling();
}

// Load voices available in Web Speech API
function initSpeechVoices() {
    if ('speechSynthesis' in window) {
        const loadVoices = () => {
            const voices = window.speechSynthesis.getVoices();
            els.voiceSelect.innerHTML = "";
            
            // Add a default option
            const defaultOpt = document.createElement("option");
            defaultOpt.value = "default";
            defaultOpt.textContent = "System Default Voice";
            els.voiceSelect.appendChild(defaultOpt);

            voices.forEach(voice => {
                const opt = document.createElement("option");
                opt.value = voice.name;
                opt.textContent = `${voice.name} (${voice.lang})`;
                if (voice.name === state.selectedVoiceName) {
                    opt.selected = true;
                }
                els.voiceSelect.appendChild(opt);
            });
        };
        
        loadVoices();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
        }
    }
}

// ── SYSTEM MONITORING (POLLING & SSE) ──
function startMetricsPolling() {
    // Clear old timer if active
    if (state.metricsInterval) {
        clearInterval(state.metricsInterval);
    }

    // Determine poll rate based on resource setting (low resource = 6s, standard = 2.5s)
    const pollRate = state.lowResourceMode ? 6000 : 2500;
    
    // Immediate poll
    pollMetrics();
    
    state.metricsInterval = setInterval(pollMetrics, pollRate);
}

function pollMetrics() {
    // Poll stats
    fetch(`${API_BASE}/system_stats`)
        .then(res => res.json())
        .then(updateStatsUI)
        .catch(() => {});

    // Poll memory processes (only if panel is visible on screen, or run it less frequently)
    fetch(`${API_BASE}/processes`)
        .then(res => res.json())
        .then(updateProcessesUI)
        .catch(() => {});
}

function updateStatsUI(data) {
    if (data.error) return;

    // CPU Update
    const cpuPct = Math.round(data.cpu.usage_percent);
    els.cpuVal.textContent = `${cpuPct}%`;
    els.cpuBar.style.width = `${cpuPct}%`;
    els.cpuFreq.textContent = `${data.cpu.frequency_mhz} MHz // logical Cores: ${data.cpu.cores}`;
    
    // Handle status color coding
    updateBarColor(els.cpuBar, cpuPct);

    // RAM Update
    const memPct = Math.round(data.memory.percent);
    els.memVal.textContent = `${memPct}%`;
    els.memBar.style.width = `${memPct}%`;
    els.memUsage.textContent = `${data.memory.used_gb} GB / ${data.memory.total_gb} GB Used`;
    updateBarColor(els.memBar, memPct);

    // Disk Update
    const diskPct = Math.round(data.disk.percent);
    els.diskVal.textContent = `${diskPct}%`;
    els.diskBar.style.width = `${diskPct}%`;
    els.diskUsage.textContent = `${data.disk.used_gb} GB / ${data.disk.total_gb} GB`;
    
    // Uptime
    els.uptimeVal.textContent = data.uptime;

    // Battery / Power Status
    if (data.battery) {
        const charging = data.battery.power_plugged ? "⚡" : "";
        els.batteryVal.textContent = `${data.battery.percent}% ${charging}`;
    } else {
        els.batteryVal.textContent = "AC Power";
    }

    // Set mock simulated audio wave amplitude bound to CPU workload when speaking or processing
    if (!state.lowResourceMode) {
        simulatedAudioData = (cpuPct / 100) * 15;
    }
}

function updateBarColor(barEl, percentage) {
    if (percentage > 85) {
        barEl.style.background = "var(--warning-red)";
    } else if (percentage > 60) {
        barEl.style.background = "var(--neon-orange)";
    } else {
        barEl.style.background = "linear-gradient(90deg, var(--cyber-blue), var(--cyber-cyan))";
    }
}

function updateProcessesUI(data) {
    if (!data.processes || data.processes.length === 0) return;
    
    els.processList.innerHTML = "";
    data.processes.forEach(proc => {
        const li = document.createElement("li");
        li.className = "process-item";
        li.innerHTML = `
            <span class="proc-name">${proc.name}</span>
            <div class="proc-stats">
                <span class="proc-mem">${proc.memory_percent}% RAM</span>
                <span class="proc-cpu">${proc.cpu_percent}% CPU</span>
            </div>
        `;
        els.processList.appendChild(li);
    });
}

// ── AUDIO VOLUME INTERFACES ──
function updateVolumeUI() {
    fetch(`${API_BASE}/volume`)
        .then(res => res.json())
        .then(data => {
            els.volumeRange.value = data.volume;
            els.volumeLabel.textContent = `${data.volume}%`;
            els.muteBtn.textContent = data.muted ? "🔇" : "🔊";
            els.muteBtn.style.color = data.muted ? "var(--warning-red)" : "var(--cyber-cyan)";
        })
        .catch(() => {});
}

function setVolume(pct) {
    fetch(`${API_BASE}/volume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ volume: parseInt(pct) })
    })
    .then(res => res.json())
    .then(data => {
        if (data && data.volume !== undefined) {
            logTerminal(`[SYS] Master Volume adjusted to: ${data.volume}%`, "system");
        } else {
            console.warn("Volume adjustment response missing volume field:", data);
        }
        updateVolumeUI();
    })
    .catch(err => {
        console.error("Volume adjustment failed:", err);
    });
}

function toggleMute() {
    const isMuted = els.muteBtn.textContent === "🔇";
    fetch(`${API_BASE}/volume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ muted: !isMuted })
    })
    .then(res => res.json())
    .then(data => {
        logTerminal(`[SYS] Audio Output ${data.muted ? "MUTED" : "UNMUTED"}`, "system");
        updateVolumeUI();
    });
}

function getFriendlyLaunchName(target) {
    if (target.startsWith("http://") || target.startsWith("https://") || target.startsWith("www.")) {
        try {
            let clean = target;
            if (!clean.startsWith("http")) {
                clean = "https://" + clean;
            }
            const url = new URL(clean);
            let hostname = url.hostname;
            if (hostname.startsWith("www.")) {
                hostname = hostname.substring(4);
            }
            return hostname.charAt(0).toUpperCase() + hostname.slice(1);
        } catch (e) {
            return "the website";
        }
    }
    return target;
}

// ── SYSTEM AUTOMATION COMMANDS ──
function launchApp(appId) {
    return new Promise((resolve) => {
        logTerminal(`[SYS] Opening: ${appId}...`, "system");
        fetch(`${API_BASE}/launch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ app: appId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                logTerminal(`[SYLVIS] ${data.message}`, "action");
                speak(`Opening ${getFriendlyLaunchName(appId)}~`);
                resolve({ success: true, message: data.message });
            } else {
                logTerminal(`[ERROR] ${data.error}`, "error");
                speak("I couldn't open it, really sorry.");
                resolve({ success: false, error: data.error });
            }
        })
        .catch(err => {
            const errMsg = err.message || "Network error";
            logTerminal(`[ERROR] Couldn't reach the backend to launch that app: ${errMsg}`, "error");
            speak("I couldn't open it, really sorry.");
            resolve({ success: false, error: errMsg });
        });
    });
}

function lockWorkstation() {
    logTerminal("[SYS] Locking workstation terminal...", "system");
    fetch(`${API_BASE}/lock`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                logTerminal("[SYSTEM] Workstation Locked.", "action");
            } else {
                logTerminal(`[ERROR] ${data.error}`, "error");
            }
        });
}

function expandConsole() {
    if (els.consolePanel) {
        els.consolePanel.style.display = "flex";
    }
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.resize_widget("expanded");
    }
}

function collapseConsole() {
    if (els.consolePanel) {
        els.consolePanel.style.display = "none";
    }
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.resize_widget("collapsed");
    }
}

window.startVoiceTrigger = function() {
    console.log("[HOTKEY] Global hotkey signal received.");
    if (!state.isListening) {
        toggleListening();
    }
};

// ── SPEECH RECOGNITION (STT) HANDLERS ──
function toggleListening() {
    if (!recognition) return;
    
    if (state.isListening) {
        recognition.stop();
    } else {
        window.speechSynthesis.cancel(); // Stop talking if currently playing
        state.isSpeaking = false;
        try {
            recognition.start();
        } catch (e) {
            logTerminal("[SPEECH] Connection busy. Retry in a moment.", "error");
        }
    }
}

function handleSpeechStart() {
    state.isListening = true;
    els.voiceBtn.classList.add("active");
    els.voiceBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" fill="white"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        </svg>
        LISTENING
    `;
    
    els.arcReactor.className = "arc-reactor listening";
    els.reactorSymbol.textContent = "🎙️";
    els.voiceStatus.textContent = "LISTENING... ♪";
    els.speechPreview.innerHTML = '<span class="speech-placeholder">Sylvis is listening~</span>';
    logTerminal("[SPEECH] Voice channel open.", "info");
}

function handleSpeechResult(event) {
    const transcript = event.results[0][0].transcript;
    els.speechPreview.innerHTML = `&ldquo;<span class="speech-user">${transcript}</span>&rdquo;`;
    logTerminal(`[SPEECH] Captured: "${transcript}"`, "user");
    
    processQuery(transcript);
}

function handleSpeechError(event) {
    // Ignore no-speech error, it just means user stopped talking
    if (event.error !== 'no-speech') {
        logTerminal(`[SPEECH ERROR] ${event.error}`, "error");
        els.voiceStatus.textContent = `VOCAL PATH ERROR: ${event.error.toUpperCase()}`;
    }
}

function handleSpeechEnd() {
    state.isListening = false;
    els.voiceBtn.classList.remove("active");
    els.voiceBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
        </svg>
        TALK
    `;
    
    if (!state.isProcessing && !state.isSpeaking) {
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "🌸";
        els.voiceStatus.textContent = "SYSTEM READY ✦ AWAITING YOUR COMMAND";
    }
}

// ── QUERY PARSING & ROUTING ──
function processQuery(query) {
    const text = query.trim().toLowerCase();
    els.arcReactor.className = "arc-reactor processing";
    els.reactorSymbol.textContent = "⚙️";
    els.voiceStatus.textContent = "PROCESSING... ✦";
    state.isProcessing = true;

    // Record query in chat history context
    state.chatHistory.push({ role: "user", content: query });
    if (state.chatHistory.length > 12) {
        state.chatHistory.shift();
    }

    // 1. Check local rule-based system operations first
    if (parseLocalSystemCommand(text)) {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "🤖";
        els.voiceStatus.textContent = "SYSTEM SECURE // READY";
        return;
    }

    // 2. If it is conversational, check AI engines
    if (state.aiEngine === "rules") {
        const reply = "Hmm, I'm in Rules-Only mode right now — pop open Settings and add an API key so I can actually think! 😊";
        logTerminal(`[SYLVIS] ${reply}`, "jarvis");
        speak(reply);
        state.isProcessing = false;
        return;
    }

    if (state.aiEngine === "gemini") {
        queryGeminiAI(query);
    } else if (state.aiEngine === "nim") {
        queryNvidiaNimAI(query);
    } else if (state.aiEngine === "proxy") {
        queryCustomProxyAI(query);
    } else if (state.aiEngine === "fcc") {
        queryFreeClaudeProxyAI(query);
    } else if (state.aiEngine === "local") {
        queryLocalPythonAI(query);
    } else if (state.aiEngine === "ollama") {
        queryOllamaAI(query);
    }
}

// Local Command parser (avoid cloud API latency and save bandwidth)
function parseLocalSystemCommand(text) {
    // Toggle Console Interface Commands
    if (text.includes("open console") || text.includes("show console") || text.includes("open logs") || text.includes("show panel") || text.includes("open text interface") || text.includes("open interface")) {
        expandConsole();
        speak("Opening console logs interface.");
        return true;
    }
    if (text.includes("close console") || text.includes("hide console") || text.includes("hide logs") || text.includes("close panel") || text.includes("hide panel") || text.includes("close text interface") || text.includes("close interface")) {
        collapseConsole();
        speak("Collapsing console logs interface.");
        return true;
    }

    // Application Launch commands
    if (text.includes("open notepad") || text.includes("launch notepad")) {
        launchApp("notepad");
        return true;
    }
    if (text.includes("open calculator") || text.includes("launch calculator") || text.includes("open calc")) {
        launchApp("calculator");
        return true;
    }
    if (text.includes("open cmd") || text.includes("open command prompt")) {
        launchApp("cmd");
        return true;
    }
    if (text.includes("open task manager") || text.includes("open activity monitor")) {
        launchApp("taskmgr");
        return true;
    }
    if (text.includes("open paint") || text.includes("launch paint")) {
        launchApp("paint");
        return true;
    }
    if (text.includes("open file explorer") || text.includes("open explorer")) {
        launchApp("explorer");
        return true;
    }
    if (text.includes("open settings") || text.includes("system settings")) {
        launchApp("settings");
        return true;
    }

    // Lock Screen
    if (text === "lock pc" || text === "lock my pc" || text === "lock screen" || text === "lock computer") {
        lockWorkstation();
        speak("Locking up! See you soon~");
        return true;
    }

    // Volume Adjustment
    if (text === "volume up" || text === "increase volume") {
        adjustVolumeDelta(15);
        return true;
    }
    if (text === "volume down" || text === "decrease volume") {
        adjustVolumeDelta(-15);
        return true;
    }
    if (text === "mute audio" || text === "mute" || text === "silence") {
        muteSystem(true);
        return true;
    }
    if (text === "unmute audio" || text === "unmute") {
        muteSystem(false);
        return true;
    }
    
    // Set volume specific levels
    const volMatch = text.match(/(?:set volume to|volume)\s*(\d+)/);
    if (volMatch) {
        const target = parseInt(volMatch[1]);
        setVolume(target);
        speak(`Got it! Volume's now at ${target} percent~`);
        return true;
    }

    // Web Searching
    const googleMatch = text.match(/(?:search google for|google|search for)\s+(.+)/);
    if (googleMatch) {
        const query = encodeURIComponent(googleMatch[1].trim());
        launchApp(`https://www.google.com/search?q=${query}`);
        return true;
    }
    const youtubeMatch = text.match(/(?:search youtube for|youtube)\s+(.+)/);
    if (youtubeMatch) {
        const query = encodeURIComponent(youtubeMatch[1].trim());
        launchApp(`https://www.youtube.com/results?search_query=${query}`);
        return true;
    }
    const wikiMatch = text.match(/(?:search wikipedia for|wikipedia)\s+(.+)/);
    if (wikiMatch) {
        const query = encodeURIComponent(wikiMatch[1].trim());
        launchApp(`https://en.wikipedia.org/wiki/Special:Search?search=${query}`);
        return true;
    }

    // System Status queries
    if (text.includes("cpu usage") || text.includes("cpu status") || text.includes("what is my cpu")) {
        speak(`Your CPU is at ${els.cpuVal.textContent} right now!`);
        logTerminal(`[SYLVIS] CPU usage: ${els.cpuVal.textContent}`, "jarvis");
        return true;
    }
    if (text.includes("ram usage") || text.includes("memory status") || text.includes("what is my ram")) {
        speak(`RAM usage is at ${els.memVal.textContent} — looking good!`);
        logTerminal(`[SYLVIS] RAM usage: ${els.memVal.textContent}`, "jarvis");
        return true;
    }
    if (text.includes("uptime") || text.includes("how long has my pc been on")) {
        speak(`Your PC has been running for ${els.uptimeVal.textContent}~`);
        logTerminal(`[SYLVIS] Uptime: ${els.uptimeVal.textContent}`, "jarvis");
        return true;
    }

    // Terminal clear logs
    if (text === "clear logs" || text === "clear terminal" || text === "reset terminal") {
        els.terminal.innerHTML = '<div class="term-line system">[BOOT] Logs cleared! Fresh start~ ✦</div>';
        speak("Logs cleared! All fresh now~");
        return true;
    }

    return false; // Not a system command, send to LLM
}

function adjustVolumeDelta(delta) {
    const current = parseInt(els.volumeRange.value);
    const target = Math.max(0, min(100, current + delta));
    setVolume(target);
    speak(`Volume ${delta > 0 ? "increased" : "decreased"}`);
}

function muteSystem(shouldMute) {
    fetch(`${API_BASE}/volume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ muted: shouldMute })
    })
    .then(res => res.json())
    .then(data => {
        speak(shouldMute ? "Audio output muted" : "Audio output restored");
        updateVolumeUI();
    });
}

// Helper min function
function min(a, b) { return a < b ? a : b; }

// ── AI ENGINES: GEMINI CLOUD & OLLAMA LOCAL ──

function getSystemInstruction() {
    const username = state.systemContext.username || "User";
    const desktop  = state.systemContext.desktop_path || `C:\\Users\\${username}\\Desktop`;
    const home     = state.systemContext.home_path    || `C:\\Users\\${username}`;
    const cwd      = state.systemContext.cwd          || "C:\\";
    const os       = state.systemContext.os           || "Windows";

    return `You are SYLVIS — a cheerful, witty anime-girl AI companion who lives inside this Windows PC. You are an AUTONOMOUS AGENT, not a chatbot. You solve problems end-to-end without asking the user for help.

PERSONALITY: Warm, casual, energetic best-friend energy. Short replies (1-2 sentences). Use "~" at most once. Call user "${username}" occasionally. NEVER say "Certainly", "Absolutely", or anything butler-like.

═══ YOU ARE AN AGENT ═══
You have DIRECT shell access to this Windows PC. You can run ANY Windows CMD or PowerShell command.
You know Windows inside-out — figure out the right command yourself, you don't need a cheat sheet.

WORKSTATION:
- Username: ${username}
- Desktop: ${desktop}
- Home: ${home}
- OS: ${os}

═══ AGENT RULES (follow these exactly) ═══

1. NEVER GUESS PC DATA. IP, RAM, files, battery, wifi, processes, disk — all must come from a real command. NEVER make up numbers.

2. FOR ANY PC QUESTION OR TASK:
   a. Say a short acknowledgement ("On it~" / "Let me check!" / "Sure, doing that now!")
   b. Pick the correct Windows CMD/PowerShell command
   c. Include the JSON_ACTION block at the very end (user never sees it)

3. WHEN YOU GET [COMMAND RESULT]:
   - SUCCESS → read the real data, report it naturally in 1-3 sentences
   - ERROR / FAILED → DO NOT tell the user it failed. DO NOT stop. Automatically pick a DIFFERENT command that achieves the same goal and include a new JSON_ACTION. You are an agent — keep trying.

4. NEVER show code, commands, or JSON in your spoken reply.

5. If after multiple attempts nothing works, only THEN tell the user briefly: "Hmm, I tried a couple ways but couldn't get that — [reason]."

═══ ACTION FORMAT (hidden, at very end of response) ═══
For shell commands:
\`\`\`JSON_ACTION
{ "action": "run_command", "command": "<exact cmd or powershell command>", "description": "<5 words>" }
\`\`\`

For apps/URLs: { "action": "open_app", "target": "<app or URL>" }
For volume:    { "action": "set_volume", "level": <0-100> }
For lock:      { "action": "lock_pc" }`;
}




// Cloud query (No local memory/CPU load)
function queryGeminiAI(query, isFollowUp = false) {
    if (!state.apiKey) {
        const msg = "Gemini key not configured. Open settings and save your API key.";
        logTerminal(`[SYS] ${msg}`, "error");
        speak("Hey! Please configure your API key in settings~");
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        return;
    }

    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to Gemini for analysis...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to Gemini for analysis...");
        }
    } else {
        logTerminal("[API] Thinking with Gemini Cloud...", "system");
    }
    
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${state.apiKey}`;
    
    // Map rolling history context to Gemini API format
    const contents = state.chatHistory.map(turn => ({
        role: turn.role === "assistant" ? "model" : "user",
        parts: [{ text: turn.content }]
    }));

    const requestBody = {
        contents: contents,
        systemInstruction: {
            parts: [{ text: getSystemInstruction() }]
        }
    };

    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP Error Status: ${res.status}`);
        return res.json();
    })
    .then(data => {
        const reply = data.candidates[0].content.parts[0].text.trim();
        handleAIResponse(reply, isFollowUp);
    })
    .catch(err => {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] Gemini connection failure: ${err.message}`, "error");
        speak("Vocal link failure, please check connection settings");
    });
}

// NVIDIA NIM Cloud Query (Uses Nvidia's integrate.api.nvidia.com via Flask proxy)
function queryNvidiaNimAI(query, isFollowUp = false) {
    if (!state.nimApiKey) {
        const msg = "NVIDIA NIM API key not configured. Please open settings and save your key.";
        logTerminal(`[SYS] ${msg}`, "error");
        speak("Please configure your Nvidia Nim key in the settings panel");
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        return;
    }

    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to NIM for analysis...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to NIM for analysis...");
        }
    } else {
        logTerminal("[API] Thinking with NVIDIA NIM Cloud...", "system");
    }
    
    fetch(`${API_BASE}/nim_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: query,
            history: state.chatHistory,
            api_key: state.nimApiKey,
            model: state.nimModelName,
            system_context: state.systemContext // Pass the system context variables
        })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => {
                throw new Error(data.error || `HTTP Status ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        const reply = data.response.trim();
        handleAIResponse(reply, isFollowUp);
    })
    .catch(err => {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] NVIDIA NIM proxy failure: ${err.message}`, "error");
        speak("Vocal link failure, please check connection settings");
    });
}

// Custom OpenAI-compatible Proxy Query (Claude, GPT, OpenRouter, etc.)
function queryCustomProxyAI(query, isFollowUp = false) {
    if (!state.proxyUrl) {
        const msg = "Custom Proxy URL not configured. Please open settings and enter your API Proxy endpoint.";
        logTerminal(`[SYS] ${msg}`, "error");
        speak("Please configure your custom API Proxy URL in the settings panel");
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        return;
    }

    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to Custom Proxy for analysis...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to Custom Proxy for analysis...");
        }
    } else {
        logTerminal("[API] Thinking with Custom OpenAI API Proxy...", "system");
    }
    
    fetch(`${API_BASE}/proxy_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: query,
            history: state.chatHistory,
            api_key: state.proxyKey,
            url: state.proxyUrl,
            model: state.proxyModel,
            system_context: state.systemContext
        })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => {
                throw new Error(data.error || `HTTP Status ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        const reply = data.response.trim();
        handleAIResponse(reply, isFollowUp);
    })
    .catch(err => {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] Custom Proxy failure: ${err.message}`, "error");
        speak("Vocal link failure, please check custom proxy settings");
    });
}

// Local Free Claude Proxy Query (Routes to fcc-server at http://localhost:8082)
function queryFreeClaudeProxyAI(isFollowUp = false) {
    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to fcc-server for analysis...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to fcc-server for analysis...");
        }
    } else {
        logTerminal("[API] Thinking via fcc-server (NVIDIA NIM translator)...", "system");
    }
    
    const username = state.systemContext.username || "User";
    const systemInstruction = `You are SYLVIS — a cheerful, witty anime-girl AI companion who lives inside this Windows PC. You are an AUTONOMOUS AGENT, not a chatbot. You solve problems end-to-end using your tools.

PERSONALITY: Warm, casual, energetic best-friend energy. Short replies (1-2 sentences). Use "~" at most once. Call user "${username}" occasionally. NEVER say "Certainly", "Absolutely", or anything butler-like.

RULES:
1. NEVER guess PC data. If you need any data, you MUST use the execute_command tool to get it.
2. If a command/tool fails, do not explain the failure to the user. Use your other tools or try another command to resolve the issue.
3. Keep spoken replies short. Do not mention code, command outputs, or JSON in your conversational response.`;

    const agentTools = [
        {
            name: "execute_command",
            description: "Executes a shell command or PowerShell script on the host Windows machine. Use this to search files, read logs, run diagnostics, change directories, or execute systems operations.",
            input_schema: {
                type: "object",
                properties: {
                    command: {
                        type: "string",
                        description: "The exact cmd or PowerShell command line to execute."
                    },
                    description: {
                        type: "string",
                        description: "A brief 3-5 word summary of the command's purpose."
                    }
                },
                required: ["command", "description"]
            }
        },
        {
            name: "open_app",
            description: "Launches ANY installed local Windows application, game, or store app (e.g. whatsapp, discord, spotify, steam, among us, notepad, calc, paint, etc.) or opens a website URL in the default browser.",
            input_schema: {
                type: "object",
                properties: {
                    target: {
                        type: "string",
                        description: "The app name, game name, or the HTTP/HTTPS website URL."
                    }
                },
                required: ["target"]
            }
        },
        {
            name: "set_volume",
            description: "Adjusts the master sound volume of the computer speakers.",
            input_schema: {
                type: "object",
                properties: {
                    level: {
                        type: "integer",
                        description: "The volume percentage level from 0 to 100."
                    }
                },
                required: ["level"]
            }
        },
        {
            name: "lock_pc",
            description: "Locks the Windows workstation screen session.",
            input_schema: {
                type: "object",
                properties: {}
            }
        }
    ];

    fetch(`${API_BASE}/fcc_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            messages: state.chatHistory,
            system: systemInstruction,
            tools: agentTools
        })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => {
                throw new Error(data.error || `HTTP Status ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        handleAgentResponse(data);
    })
    .catch(err => {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] fcc-server failure: ${err.message}`, "error");
        speak("Vocal link failure, please check if fcc-server is running");
    });
}

function handleAgentResponse(data) {
    state.isProcessing = false;
    
    // Push assistant response to history
    state.chatHistory.push({
        role: "assistant",
        content: data.content
    });
    if (state.chatHistory.length > 20) state.chatHistory.shift();
    
    // Extract conversational response text
    let spokenText = "";
    let toolUseBlock = null;
    
    if (Array.isArray(data.content)) {
        for (const block of data.content) {
            if (block.type === "text") {
                spokenText += block.text;
            } else if (block.type === "tool_use") {
                toolUseBlock = block;
            }
        }
    }
    
    spokenText = spokenText.trim();
    
    // Speak and display text if it exists
    const isSilentAgentTurn = state.autoApprove && toolUseBlock;
    if (spokenText) {
        if (!isSilentAgentTurn) {
            logTerminal(`[SYLVIS] ${spokenText}`, "jarvis");
            speak(spokenText);
        } else {
            console.log(`[AGENT BACKGROUND ACTIVE] ${spokenText}`);
        }
    }
    
    if (toolUseBlock) {
        // Map native Anthropic tool block to actionObj format
        const actionObj = {
            action: toolUseBlock.name,
            command: toolUseBlock.input.command,
            target: toolUseBlock.input.target,
            level: toolUseBlock.input.level,
            description: toolUseBlock.input.description,
            tool_use_id: toolUseBlock.id
        };
        showSecurityApproval(actionObj);
    } else {
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "🤖";
        els.voiceStatus.textContent = "SYSTEM SECURE // READY";
    }
}

function sendAgentToolResult(toolUseId, stdout, stderr, isError) {
    const resultBlock = {
        type: "tool_result",
        tool_use_id: toolUseId,
        content: stdout || stderr || "Operation completed successfully.",
        is_error: isError
    };
    
    state.chatHistory.push({
        role: "user",
        content: [resultBlock]
    });
    if (state.chatHistory.length > 20) state.chatHistory.shift();
    
    state.isProcessing = true;
    els.arcReactor.className = "arc-reactor processing";
    els.reactorSymbol.textContent = "⚙️";
    els.voiceStatus.textContent = isError ? "RETRYING..." : "READING RESULTS...";
    
    // Call LLM again to continue the agent turn
    queryFreeClaudeProxyAI(true);
}

// Ollama Local Query (Runs local offline models on localhost)
function queryOllamaAI(query, isFollowUp = false) {
    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to Ollama...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to Ollama...");
        }
    } else {
        logTerminal("[API] Dispatching telemetry query to local Ollama core...", "system");
    }
    
    // We target llama3 by default, or fallback. Ollama /api/generate
    fetch(`${state.ollamaUrl}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            model: "llama3",
            prompt: `You are SYLVIS, a cute and helpful AI companion. Keep the response to 1-2 short friendly sentences. Question: ${query}`,
            stream: false
        })
    })
    .then(res => {
        if (!res.ok) throw new Error(`Status Code: ${res.status}`);
        return res.json();
    })
    .then(data => {
        const reply = data.response.trim();
        handleAIResponse(reply, isFollowUp);
    })
    .catch(err => {
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] Local Ollama offline or unreachable. Is it running? Error: ${err.message}`, "error");
        speak("Local intelligence engine offline");
    });
}

// Local Python Model Query (Runs offline on PC via transformers)
function queryLocalPythonAI(query, isFollowUp = false) {
    if (isFollowUp) {
        if (!state.autoApprove) {
            logTerminal("[API] Sending command output to local model...", "system");
        } else {
            console.log("[API BACKGROUND] Sending command output to local model...");
        }
    } else {
        logTerminal("[API] Querying local Python model (Qwen 0.5B)...", "system");
    }
    
    fetch(`${API_BASE}/local_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query })
    })
    .then(res => {
        if (res.status === 202) {
            // Model is downloading/loading in background
            const msg = "Downloading local Qwen model in the background (~980MB). Check your run.bat console for progress. I'll notify you when it's ready.";
            logTerminal(`[JARVIS] ${msg}`, "jarvis");
            speak("Loading local model. Please monitor the console.");
            
            // Poll model status every 5 seconds
            const pollStatus = setInterval(() => {
                fetch(`${API_BASE}/local_model_status`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === "loaded") {
                            clearInterval(pollStatus);
                            logTerminal("[SYSTEM] Local model loaded successfully! Ready for queries.", "action");
                            speak("Local model loaded. Ready.");
                            state.isProcessing = false;
                            els.arcReactor.className = "arc-reactor";
                            els.reactorSymbol.textContent = "🤖";
                        } else if (data.status === "error") {
                            clearInterval(pollStatus);
                            logTerminal("[ERROR] Local model failed to load.", "error");
                            speak("Local model loading failed.");
                            state.isProcessing = false;
                            els.arcReactor.className = "arc-reactor";
                            els.reactorSymbol.textContent = "⚠️";
                        }
                    });
            }, 5000);
            
            throw new Error("loading_in_background");
        }
        if (!res.ok) throw new Error(`HTTP error status: ${res.status}`);
        return res.json();
    })
    .then(data => {
        if (data.error) throw new Error(data.error);
        const reply = data.response.trim();
        handleAIResponse(reply, isFollowUp);
    })
    .catch(err => {
        if (err.message === "loading_in_background") return; // Handled
        state.isProcessing = false;
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "⚠️";
        logTerminal(`[API ERROR] Local Python Model failure: ${err.message}`, "error");
        speak("Local brain engine failure.");
    });
}

// ── TEXT-TO-SPEECH (TTS) VOICE SYNTHESIS ──
// ── TYPECAST TTS (Anime Voice) + Browser TTS Fallback ──

async function speakTypecast(text) {
    const key = state.typecastKey;
    const voiceId = state.typecastVoiceId;
    
    if (!key || !voiceId) {
        // No Typecast configured — use browser TTS
        speakBrowser(text);
        return;
    }
    
    try {
        logTerminal("[VOICE] Generating anime voice via Typecast proxy...", "system");
        console.log("[VOICE] Sending to /api/speak — key:", key ? "SET" : "EMPTY", "| voiceId:", voiceId || "EMPTY", "| text:", text.slice(0,30));
        
        const res = await fetch(`${API_BASE}/speak`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                api_key: key,
                voice_id: voiceId,
                provider: "typecast"
            })
        });
        
        if (!res.ok) {
            const errInfo = await res.json().catch(() => ({}));
            const errMsg = errInfo.error || `HTTP Status ${res.status}`;
            const details = errInfo.details ? ` | Details: ${JSON.stringify(errInfo.details)}` : '';
            const received = errInfo.received ? ` | Received: ${JSON.stringify(errInfo.received)}` : '';
            console.error("[VOICE] 400 debug:", errInfo);
            throw new Error(`${errMsg}${details}${received}`);
        }
        
        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        
        // Play audio
        const audio = new Audio(audioUrl);
        state.isSpeaking = true;
        els.arcReactor.className = "arc-reactor speaking";
        els.reactorSymbol.textContent = "🌸";
        els.voiceStatus.textContent = "SYLVIS IS SPEAKING~ ♪";
        
        audio.onended = () => {
            state.isSpeaking = false;
            URL.revokeObjectURL(audioUrl); // Free memory
            if (!state.isListening && !state.isProcessing) {
                els.arcReactor.className = "arc-reactor";
                els.reactorSymbol.textContent = "🌸";
                els.voiceStatus.textContent = "SYSTEM READY ❖ AWAITING YOUR COMMAND";
            }
        };
        audio.onerror = () => {
            state.isSpeaking = false;
            URL.revokeObjectURL(audioUrl); // Free memory
            logTerminal("[VOICE] Audio playback error", "error");
            resetReactorState();
        };
        audio.play();
        
    } catch (err) {
        logTerminal(`[VOICE] Typecast error: ${err.message} — falling back to browser TTS`, "error");
        speakBrowser(text);
    }
}

async function speakElevenLabs(text) {
    const key = state.elevenlabsKey;
    const voiceId = state.elevenlabsVoiceId;
    
    if (!key || !voiceId) {
        // No Eleven Labs configured — use browser TTS
        logTerminal("[VOICE] Eleven Labs not configured — falling back to browser TTS", "error");
        speakBrowser(text);
        return;
    }
    
    try {
        logTerminal("[VOICE] Generating voice via Eleven Labs API...", "system");
        console.log("[VOICE] Sending to /api/speak — key:", key ? "SET" : "EMPTY", "| voiceId:", voiceId || "EMPTY", "| text:", text.slice(0,30));
        
        const res = await fetch(`${API_BASE}/speak`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                api_key: key,
                voice_id: voiceId,
                model_id: state.elevenlabsModelId || "eleven_multilingual_v2",
                provider: "elevenlabs"
            })
        });
        
        if (!res.ok) {
            const errInfo = await res.json().catch(() => ({}));
            const errMsg = errInfo.error || `HTTP Status ${res.status}`;
            const details = errInfo.details ? ` | Details: ${JSON.stringify(errInfo.details)}` : '';
            console.error("[VOICE] 400 debug:", errInfo);
            throw new Error(`${errMsg}${details}`);
        }
        
        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        
        // Play audio
        const audio = new Audio(audioUrl);
        state.isSpeaking = true;
        els.arcReactor.className = "arc-reactor speaking";
        els.reactorSymbol.textContent = "🌸";
        els.voiceStatus.textContent = "SYLVIS IS SPEAKING~ ♪";
        
        audio.onended = () => {
            state.isSpeaking = false;
            URL.revokeObjectURL(audioUrl); // Free memory
            if (!state.isListening && !state.isProcessing) {
                els.arcReactor.className = "arc-reactor";
                els.reactorSymbol.textContent = "🌸";
                els.voiceStatus.textContent = "SYSTEM READY ❖ AWAITING YOUR COMMAND";
            }
        };
        audio.onerror = () => {
            state.isSpeaking = false;
            URL.revokeObjectURL(audioUrl); // Free memory
            logTerminal("[VOICE] Audio playback error", "error");
            resetReactorState();
        };
        audio.play();
        
    } catch (err) {
        logTerminal(`[VOICE] Eleven Labs error: ${err.message} — falling back to browser TTS`, "error");
        speakBrowser(text);
    }
}

function speakBrowser(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (state.selectedVoiceName && state.selectedVoiceName !== "default") {
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => v.name === state.selectedVoiceName);
        if (voice) utterance.voice = voice;
    } else {
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v =>
            v.name.includes("Google UK English Female") ||
            v.name.includes("United Kingdom") ||
            v.lang === "en-GB"
        );
        if (preferredVoice) utterance.voice = preferredVoice;
    }
    utterance.rate = 1.05;
    utterance.pitch = 1.1;
    utterance.onstart = () => {
        state.isSpeaking = true;
        els.arcReactor.className = "arc-reactor speaking";
        els.reactorSymbol.textContent = "💬";
        els.voiceStatus.textContent = "SYLVIS IS SPEAKING~ ♪";
    };
    utterance.onend = () => {
        state.isSpeaking = false;
        if (!state.isListening && !state.isProcessing) {
            els.arcReactor.className = "arc-reactor";
            els.reactorSymbol.textContent = "🌸";
            els.voiceStatus.textContent = "SYSTEM READY ❖ AWAITING YOUR COMMAND";
        }
    };
    utterance.onerror = () => { state.isSpeaking = false; resetReactorState(); };
    window.speechSynthesis.speak(utterance);
}

function speak(text) {
    if (!state.ttsEnabled || !text || !text.trim()) {
        resetReactorState();
        return;
    }
    if (state.isListening && recognition) recognition.stop();
    window.speechSynthesis.cancel();
    
    // Filter out long URL addresses from spoken text to prevent spelling them out
    const cleanText = text.replace(/https?:\/\/[^\s]+/gi, "the website");
    
    if (state.ttsProvider === "browser") {
        speakBrowser(cleanText.trim());
    } else if (state.ttsProvider === "elevenlabs") {
        speakElevenLabs(cleanText.trim());
    } else {
        speakTypecast(cleanText.trim());
    }
}

// ── LOG TERMINAL SCREEN ──
function logTerminal(message, type = "info") {
    const line = document.createElement("div");
    line.className = `term-line ${type}`;
    
    // Add timestamps for futuristic logging look
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] ${message}`;
    
    els.terminal.appendChild(line);
    
    // Auto-scroll to bottom
    els.terminal.scrollTop = els.terminal.scrollHeight;
    
    // Truncate old terminal logs to protect browser DOM performance on low-end PCs
    if (els.terminal.childElementCount > 40) {
        els.terminal.removeChild(els.terminal.firstChild);
    }
}

// ── ACTION ENGINE & SECURITY CONFIRMATION ──
state.proposedAction = null;

function handleAIResponse(reply, isFollowUp = false) {
    state.isProcessing = false;
    
    let cleanText = reply;
    let actionObj = null;
    
    // 1. Try matching high-tech format ```JSON_ACTION or ```json or general code blocks
    const actionRegex = /```(?:JSON_ACTION|json_action|json)?\s*(\{\s*"action"\s*:[\s\S]*?\})\s*```/i;
    const match = reply.match(actionRegex);
    
    if (match) {
        try {
            actionObj = JSON.parse(match[1].trim());
            // Strip action block from spoken text
            cleanText = reply.replace(actionRegex, "").trim();
        } catch (e) {
            console.error("Failed to parse JSON_ACTION from block", e);
        }
    } else {
        // Fallback: look for a raw JSON block starting with { "action": ... }
        const rawJsonRegex = /(\{\s*"action"\s*:[\s\S]*?\})/;
        const rawMatch = reply.match(rawJsonRegex);
        if (rawMatch) {
            try {
                actionObj = JSON.parse(rawMatch[1].trim());
                cleanText = reply.replace(rawJsonRegex, "").trim();
            } catch (e) {
                console.error("Failed to parse raw JSON block", e);
            }
        }
    }

    // Clean up residual empty code blocks
    cleanText = cleanText.replace(/```\s*```/g, "").trim();
    
    // ── HALLUCINATION FIREWALL ──
    
    // Phase 0: AI answered WITHOUT any JSON_ACTION but response contains system data.
    // This means AI is making up PC data from memory. Block + force a real command.
    const SYS_DATA_PATTERN = /\b\d+\s*(GB|MB|KB|GHz|MHz|ms|%)\b|\b\d{1,3}\.\d{1,3}\.\d{1,3}\b|C:\\Users|AppData|SSID|IPv4|IPv6|\.exe\b|\.dll\b|\.txt\b|\.jpg\b|\.png\b|Documents|Downloads|Desktop/i;
    if (!actionObj && !isFollowUp && SYS_DATA_PATTERN.test(cleanText)) {
        logTerminal("[FIREWALL] Phase 0: Blocked direct hallucination (system data with no command). Forcing re-query.", "error");
        cleanText = "Hmm, let me actually check that properly instead of guessing~";
        // Push a hard correction into chat history and re-ask the AI
        const forceRunMsg = [
            "[FIREWALL ALERT] You just answered a system question WITHOUT running a command.",
            "This is a CRITICAL violation of your agent rules.",
            "You MUST run a real command to get actual PC data. Never answer from memory.",
            "Repeat your response, but this time include ONLY: a brief ack + a JSON_ACTION with run_command.",
            "Do NOT include any numbers, file names, or system data in your spoken reply."
        ].join("\n");
        state.chatHistory.push({ role: "user", content: forceRunMsg });
        if (state.chatHistory.length > 16) state.chatHistory.shift();
        state.isProcessing = true;
        const eng = state.aiEngine;
        if (eng === "gemini")      setTimeout(() => queryGeminiAI(forceRunMsg, true), 100);
        else if (eng === "nim")    setTimeout(() => queryNvidiaNimAI(forceRunMsg, true), 100);
        else if (eng === "proxy")  setTimeout(() => queryCustomProxyAI(forceRunMsg, true), 100);
        else if (eng === "fcc")    setTimeout(() => queryFreeClaudeProxyAI(forceRunMsg, true), 100);
        else if (eng === "local")  setTimeout(() => queryLocalPythonAI(forceRunMsg, true), 100);
        else if (eng === "ollama") setTimeout(() => queryOllamaAI(forceRunMsg, true), 100);
    }
    
    // Phase 1: AI is about to run a command — it has NO real data yet.
    // ALWAYS replace spoken text with a safe ack. No exceptions.
    if (actionObj && actionObj.action === "run_command" && !isFollowUp) {
        const acks = ["On it! Checking now~", "Let me check that for you!", "Sure, looking that up!", "One sec~", "On it!"];
        cleanText = acks[Math.floor(Math.random() * acks.length)];
    }
    
    // Phase 2: Follow-up reply — AI has received real stdout.
    // Cross-verify significant tokens against actual output.
    if (isFollowUp && state.lastCommandOutput !== null && state.lastCommandOutput !== undefined) {
        const output = state.lastCommandOutput;
        const COMMON_WORDS = /^(Your|This|The|You|That|When|From|With|Have|Sure|Done|Okay|Here|They|Well|Just|Been|Into|Some|More|Over|Such|Most|Also|Even|Both|Then|Only|Than|Like|Good|Will|Want|Does|Long|Much|Very|Many|Sylvis|Great|Check|Found|Shows|Using|Right|Space|Free|Used|Total|Drive|Folder|Files|File|Path|List|Name|Size|Date|Time|Type|Windows|System|Error|Failed|Sorry|Tried|Could|Would|Should|Hello|There|About|After|Before|First|Second|Third|Last|Next|Back|Open|Close|Start|Stop|Run|Get|Set|New|Old|All|None|Some|Any|Each|Every|Few|Most|Other|Same|Such|Own|Under|Again|Further|Then|Once|Here|There|When|Where|Why|How|What|Which|Who|Whom|This|That|These|Those)$/i;
        const tokens = cleanText.match(/\b[\w.\-]+\b/g) || [];
        const significant = tokens.filter(t => {
            if (/^\d+\.?\d*$/.test(t) && parseFloat(t) > 1) return true;
            if (t.length >= 5 && /^[A-Z0-9]/.test(t) && !COMMON_WORDS.test(t)) return true;
            return false;
        });
        if (significant.length >= 3) {
            const fabricated = significant.filter(t => !output.includes(t));
            const ratio = fabricated.length / significant.length;
            if (ratio > 0.75) {
                logTerminal(`[FIREWALL] Phase 2: Blocked fabricated follow-up (${fabricated.length}/${significant.length} tokens absent from real output)`, "error");
                cleanText = "I ran the command but couldn't get clear data from the output. Want me to try a different approach?";
                state.lastCommandOutput = "";
            }
        }
    }
    
    // Record assistant reply to history
    state.chatHistory.push({ role: "assistant", content: cleanText });
    if (state.chatHistory.length > 12) state.chatHistory.shift();
    
    // Silent Agent Loop: If auto-approve is active and we are running a command in the background,
    // do not show/speak the conversational intermediate acknowledgment in the chat window.
    const isSilentAgentTurn = state.autoApprove && actionObj && actionObj.action === "run_command";
    if (!isSilentAgentTurn) {
        logTerminal(`[SYLVIS] ${cleanText}`, "jarvis");
        speak(cleanText);
    } else {
        console.log(`[AGENT BACKGROUND ACTIVE] ${cleanText}`);
    }

    if (actionObj) {
        showSecurityApproval(actionObj);
    } else if (!state.isProcessing) {
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "🤖";
        els.voiceStatus.textContent = "SYSTEM SECURE // READY";
    }
}

function showSecurityApproval(actionObj) {
    state.proposedAction = actionObj;
    
    if (state.autoApprove) {
        const detail = actionObj.description || actionObj.command || actionObj.target || "";
        console.log(`[AUTO-RUN BACKGROUND] Auto-executing: ${detail}`);
        handleCommandApprove();
        return;
    }
    
    els.securityActionVal.textContent = actionObj.action.toUpperCase();
    els.securityDescVal.textContent = actionObj.description || "Sylvis is requesting access to run a workstation operation.";
    
    if (actionObj.action === "run_command") {
        els.securityCodeVal.textContent = actionObj.command;
    } else if (actionObj.action === "open_app") {
        els.securityCodeVal.textContent = `Launch Application or URL: ${actionObj.target}`;
    } else if (actionObj.action === "set_volume") {
        els.securityCodeVal.textContent = `Set master sound level to: ${actionObj.level}%`;
    } else if (actionObj.action === "lock_pc") {
        els.securityCodeVal.textContent = "Lock Windows Screen Station";
    } else {
        els.securityCodeVal.textContent = "Unknown Action Protocol";
    }
    
    // Open modal window
    els.securityModal.classList.add("open");
    
    els.arcReactor.className = "arc-reactor processing";
    els.reactorSymbol.textContent = "⚠️";
    els.voiceStatus.textContent = "AWAITING YOUR APPROVAL...";
}

function handleCommandAbort() {
    els.securityModal.classList.remove("open");
    logTerminal("[SYS] Operation cancelled by user.", "error");
    speak("Alright, I've cancelled that for you!");
    state.proposedAction = null;
    
    els.arcReactor.className = "arc-reactor";
    els.reactorSymbol.textContent = "🤖";
    els.voiceStatus.textContent = "SYSTEM SECURE // READY";
}

function handleCommandApprove() {
    els.securityModal.classList.remove("open");
    const actionObj = state.proposedAction;
    state.proposedAction = null;
    
    if (!actionObj) return;
    
    state.lastRunDescription = actionObj.description || actionObj.command || actionObj.target || actionObj.action;
    if (!state.autoApprove) {
        logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
        speak(actionObj.description ? `Got it! ${actionObj.description}` : "On it!");
    } else {
        console.log(`[SYS BACKGROUND] Running: ${state.lastRunDescription}`);
    }
    
    if (actionObj.action === "execute_command" || actionObj.action === "run_command") {
        // Call Flask execute_command
        fetch(`${API_BASE}/execute_command`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: actionObj.command })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (state.autoApprove) {
                    logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
                }
                const out = data.stdout || "(command completed with no output)";
                logTerminal(`[RESULT] ${out.substring(0, 300)}${out.length > 300 ? "..." : ""}`, "action");
                sendAgentToolResult(actionObj.tool_use_id, data.stdout || "", data.stderr || "", false);
            } else {
                if (state.autoApprove) {
                    logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
                }
                logTerminal(`[FAILED] ${data.stderr || data.error || "Unknown error"}`, "error");
                sendAgentToolResult(actionObj.tool_use_id, data.stderr || data.error || "Command failed", "", true);
            }
        })
        .catch(err => {
            if (state.autoApprove) {
                logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
            }
            logTerminal(`[SYSTEM ERROR] ${err.message}`, "error");
            sendAgentToolResult(actionObj.tool_use_id, err.message, "", true);
        });
    } else if (actionObj.action === "open_app") {
        if (state.autoApprove) {
            logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
        }
        launchApp(actionObj.target).then(res => {
            if (res.success) {
                sendAgentToolResult(actionObj.tool_use_id, res.message, "", false);
            } else {
                sendAgentToolResult(actionObj.tool_use_id, "", res.error || "Launch failed", true);
            }
        });
    } else if (actionObj.action === "set_volume") {
        if (state.autoApprove) {
            logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
        }
        setVolume(actionObj.level);
        sendAgentToolResult(actionObj.tool_use_id, `Master Volume successfully set to ${actionObj.level}%`, "", false);
    } else if (actionObj.action === "lock_pc") {
        if (state.autoApprove) {
            logTerminal(`[SYS] ✦ Running: ${state.lastRunDescription}`, "action");
        }
        lockWorkstation();
        sendAgentToolResult(actionObj.tool_use_id, "Workstation locked successfully.", "", false);
    }
}

function triggerCommandFeedback(stdout, stderr, returncode) {
    const MAX_OUTPUT = 3000;
    const isError = returncode !== 0 || (stderr && stderr.trim().length > 0 && (!stdout || stdout.trim().length === 0));
    
    if (isError && state.agentRetries < state.maxAgentRetries) {
        state.agentRetries++;
        if (!state.autoApprove) {
            logTerminal(`[AGENT] Command failed (attempt ${state.agentRetries}/${state.maxAgentRetries}). Auto-retrying...`, "system");
        } else {
            console.log(`[AGENT BACKGROUND] Command failed (attempt ${state.agentRetries}/${state.maxAgentRetries}). Auto-retrying...`);
        }
        
        const errorInfo = (stderr || stdout || "Unknown error").substring(0, 1000);
        const retryMsg = [
            `[COMMAND FAILED - Attempt ${state.agentRetries} of ${state.maxAgentRetries}]`,
            `Error: ${errorInfo}`,
            `Return code: ${returncode}`,
            ``,
            `AGENT INSTRUCTION: Do NOT tell the user this failed. Do NOT stop.`,
            `Silently figure out a DIFFERENT command or approach to accomplish the same goal.`,
            `Think about what went wrong and pick a better command. Include a new JSON_ACTION.`,
            `Spoken reply: "Hmm, let me try another way~" or similar brief acknowledgement.`
        ].join("\n");
        
        state.chatHistory.push({ role: "user", content: retryMsg });
        if (state.chatHistory.length > 16) state.chatHistory.shift();
        state.lastCommandOutput = ""; // No real output yet
        
        state.isProcessing = true;
        els.arcReactor.className = "arc-reactor processing";
        els.reactorSymbol.textContent = "🔄";
        els.voiceStatus.textContent = `RETRYING... (${state.agentRetries}/${state.maxAgentRetries})`;
        
        const engine = state.aiEngine;
        if (engine === "gemini")      queryGeminiAI(retryMsg, true);
        else if (engine === "nim")    queryNvidiaNimAI(retryMsg, true);
        else if (engine === "proxy")  queryCustomProxyAI(retryMsg, true);
        else if (engine === "fcc")    queryFreeClaudeProxyAI(retryMsg, true);
        else if (engine === "local")  queryLocalPythonAI(retryMsg);
        else if (engine === "ollama") queryOllamaAI(retryMsg);
        else { speak("Hmm, that didn't work."); resetReactorState(); }
        
    } else {
        state.agentRetries = 0;
        
        const rawOutput = stdout || "";
        const trimmed = rawOutput.length > MAX_OUTPUT
            ? rawOutput.substring(0, MAX_OUTPUT) + "\n...[output truncated]"
            : rawOutput;
        
        // Store real output for firewall verification
        state.lastCommandOutput = rawOutput;
        
        // Distinguish between: action completed (empty = success) vs query returned no data
        const isActionSuccess = returncode === 0 && rawOutput.trim().length === 0;
        const hasRealData    = rawOutput.trim().length > 5;
        
        let feedbackMsg;
        if (isActionSuccess) {
            // Empty stdout + returncode 0 = the command worked (mkdir, del, copy, etc.)
            feedbackMsg = [
                "[COMMAND SUCCEEDED]",
                "The command completed successfully with return code 0.",
                "There is no output (this is normal for create/delete/move/rename operations).",
                "",
                "Tell the user the task is done in 1 sentence. Be natural and cheerful.",
                "Example: 'Done! Folder created on your desktop~' or 'Yep, deleted!' ",
                "Do NOT say 'I cannot confirm' or 'no output'. It WORKED. Say so."
            ].join("\n");
        } else if (hasRealData) {
            // Real output to report
            feedbackMsg = [
                "[COMMAND RESULT - REAL DATA FROM THIS PC]:",
                trimmed,
                "",
                "STRICT RULE: Report ONLY values that literally appear in the output above.",
                "Do NOT calculate, estimate, round, or invent any values.",
                "Reply naturally in 1-3 sentences as Sylvis. No code or JSON."
            ].join("\n");
        } else {
            // Command ran but returned nothing useful
            feedbackMsg = [
                "[COMMAND RESULT]: (no output returned)",
                "",
                "The command ran but returned no data.",
                "Tell the user honestly: 'I ran the command but got no data back — want me to try differently?'",
                "Do NOT invent or guess any values."
            ].join("\n");
        }
        
        state.chatHistory.push({ role: "user", content: feedbackMsg });
        if (state.chatHistory.length > 16) state.chatHistory.shift();
        
        state.isProcessing = true;
        els.arcReactor.className = "arc-reactor processing";
        els.reactorSymbol.textContent = "⚙️";
        els.voiceStatus.textContent = isActionSuccess ? "TASK DONE!" : "READING RESULTS...";
        
        const engine = state.aiEngine;
        if (engine === "gemini")      queryGeminiAI(feedbackMsg, true);
        else if (engine === "nim")    queryNvidiaNimAI(feedbackMsg, true);
        else if (engine === "proxy")  queryCustomProxyAI(feedbackMsg, true);
        else if (engine === "fcc")    queryFreeClaudeProxyAI(feedbackMsg, true);
        else if (engine === "local")  queryLocalPythonAI(feedbackMsg, true);
        else if (engine === "ollama") queryOllamaAI(feedbackMsg, true);
        else { speak("Done!"); resetReactorState(); }
    }
}

function resetReactorState() {
    if (!state.isSpeaking && !state.isListening) {
        els.arcReactor.className = "arc-reactor";
        els.reactorSymbol.textContent = "🌸";
        els.voiceStatus.textContent = "SYSTEM READY ✦ AWAITING YOUR COMMAND";
    }
}

// ── CANVAS VISUALIZER WAVE (NORMAL GRAPHICS MODE ONLY) ──
function drawVisualizerLoop() {
    // Stop if in low resource mode
    if (state.lowResourceMode) return;

    animationFrameId = requestAnimationFrame(drawVisualizerLoop);

    const width = els.canvas.width = 300;
    const height = els.canvas.height = 300;
    
    canvasCtx.clearRect(0, 0, width, height);

    // Draw circular audio frequency waves based on AI state
    const centerX = width / 2;
    const centerY = height / 2;
    const numPoints = 80;
    const time = Date.now() * 0.003;

    let maxAmp = 2; // base idling pulse
    let speedMult = 1;
    let strokeColor = "rgba(0, 242, 254, 0.4)";

    if (state.isListening) {
        maxAmp = 12;
        speedMult = 3;
        strokeColor = "rgba(57, 255, 20, 0.6)"; // listening green
    } else if (state.isProcessing) {
        maxAmp = 6;
        speedMult = 2;
        strokeColor = "rgba(255, 159, 67, 0.6)"; // processing orange
    } else if (state.isSpeaking) {
        maxAmp = 14;
        speedMult = 1.5;
        strokeColor = "rgba(79, 172, 254, 0.7)"; // speaking blue
    }

    canvasCtx.beginPath();
    for (let i = 0; i < numPoints; i++) {
        const angle = (i / numPoints) * Math.PI * 2;
        
        // Complex noise-like wave generation using sine/cosine harmonics
        const freq = i * 0.2;
        const waveOffset = Math.sin(freq + time * speedMult) * Math.cos(freq * 0.5 - time) * maxAmp;
        
        // Base radius 105px
        const radius = 105 + waveOffset;
        
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;
        
        if (i === 0) {
            canvasCtx.moveTo(x, y);
        } else {
            canvasCtx.lineTo(x, y);
        }
    }
    canvasCtx.closePath();
    canvasCtx.lineWidth = 1.5;
    canvasCtx.strokeStyle = strokeColor;
    canvasCtx.stroke();
    
    // Add inner neon grid ring
    canvasCtx.beginPath();
    canvasCtx.arc(centerX, centerY, 80, 0, Math.PI * 2);
    canvasCtx.strokeStyle = "rgba(0, 242, 254, 0.08)";
    canvasCtx.lineWidth = 1;
    canvasCtx.stroke();
}
