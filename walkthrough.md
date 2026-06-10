# S.Y.L.V.I.S. UI Overhaul & Interactive Manual Walkthrough

The S.Y.L.V.I.S. PC Assistant operates within a **custom borderless desktop HUD environment**. Traditional window borders and standard Windows title bars are replaced with neon-lit dashboards, diagnostic grids, and an interactive browser-based User Manual.

---

## 🎨 Futuristic HUD Design

1. **Borderless Floating Windows (`overrideredirect`)**:
   - Window borders have been completely removed from **SylvisConsole**, **SylvisSettingsWindow**, and **SecureApprovalWindow**.
   - **Glow Borders**: Added 2px neon borders surrounding each panel:
     - *Terminal Console*: Neon Cyan (`#00ffff`) glow border.
     - *Settings Panel*: Neon Pink/Magenta (`#ff007f`) glow border.
     - *Firewall Authorization Box*: Neon Red (`#ef4444`) glow border.

2. **Custom Window Drag Handlers**:
   - Because standard title bars are removed, clicking and dragging on the custom headers (or header labels) of the Console, Settings, or Approval windows allows you to smoothly reposition them anywhere on your desktop.

3. **Active System Diagnostics Dashboard**:
   - A real-time diagnostics bar is integrated directly inside the header of the Command Terminal:
     - **CPU**: Live CPU load percentage (cyan telemetry meter).
     - **RAM**: Live virtual memory utilization percentage (pink telemetry meter).
     - **BRAIN**: Shows the active cloud or local offline intelligence engine (purple badge).
     - **VOICE**: Displays the active text-to-speech speaker configuration (green badge).
   - Metrics are polled and updated automatically in the background every 2 seconds.

4. **Visualizer Telemetry Indicators**:
   - The central orb widget (`SylvisWidget`) renders breathing, pulsing, or rotating HUD rings:
     - Corner framing brackets centered around the visualizer coordinates.
     - Concentric outer tech circles and dashed ring orbits.
     - Real-time **status telemetry badges** drawn above the core (e.g. `[SYS.ONLINE]`, `[REC.AUDIO]`, `[COMP.COGNITIVE]`, `[SYS.TRANSMIT]`) changing dynamically with state transitions (Idle, Listening, Processing, Speaking).

---

## 📖 Interactive Web User Manual

1. **Cyberpunk User Manual (`manual.html`)**:
   - A standalone HTML document styled with a glowing dark theme using Google Fonts (`Outfit` and `JetBrains Mono`), glassmorphic cards, and hover transitions.
   - Includes full setup instructions for all components (waking hotkeys, context menus, low resource mode, offline local LLM files).

2. **Free API Setup Guide**:
   - Explains how to sign up and retrieve API keys for free (NVIDIA NIM tokens for Claude 3.5 Sonnet, ElevenLabs, or Typecast).

3. **In-App Integration**:
   - Added a **❓ MANUAL** button in the Console panel next to `SETTINGS` that automatically opens the local user manual in your default browser.

---

## 🔒 SSL & Corporate Proxy Bypass (Claude Mode Recovery)

1. **Strict SSL Validation Bypass (`sitecustomize.py`)**:
   - Python 3.11+ and OpenSSL 3.x enforce strict certificate verification by default. If you are behind a corporate proxy/firewall that signs HTTPS traffic using a custom root CA, OpenSSL will block the connection if the CA's "Basic Constraints" extension isn't marked as critical.
   - S.Y.L.V.I.S. automatically writes a self-healing patch at `~/.fcc/python_patch/sitecustomize.py` on startup that intercepts and clears `ssl.VERIFY_X509_STRICT` when Python's `ssl` module creates a context.
   - `app.py` runs the background proxy (`fcc-server.exe`) with `PYTHONPATH` set to this patch directory, letting it connect securely to NVIDIA NIM.

2. **Local AI Chat Mode**:
   - Supports Qwen 2.5 (0.5B-Instruct) locally on your CPU. Choosing **Local Offline AI** in settings allows conversational chat without needing any network connection or cloud API keys.

---

## 🔍 Verification Checklist

To verify the S.Y.L.V.I.S. PC Assistant:

1. **Clean Settings State**:
   - In settings, ensure `"first_run": true` (or delete `~/.sylvis_settings.json`).
2. **Launch Assistant**:
   - Double-click **[run.bat](file:///c:/Users/ayush/Downloads/New%20folder%20(2)/jarvis-pc/run.bat)** or **[Launch Sylvis.vbs](file:///c:/Users/ayush/Downloads/New%20folder%20(2)/jarvis-pc/Launch%20Sylvis.vbs)**.
3. **Verify Browser Launch**:
   - Confirm that two browser tabs open automatically on first boot: the NVIDIA NIM proxy settings and the custom user manual page (`manual.html`).
   - Confirm that on subsequent restarts of the application, the browser does not open.
4. **Inspect Borderless UI**:
   - Double-click the visualizer orb to toggle the terminal. Verify the terminal is borderless, has a cyan neon border, and live CPU/RAM stats update in the header.
   - Click **SETTINGS** and verify the settings configuration deck opens borderlessly with a pink neon border.
   - Verify both panels can be dragged smoothly by clicking and dragging on their header areas.
5. **Verify Claude Mode Connectivity**:
   - Set AI provider to **Free Claude Server**.
   - Input a message like "hi". Verify Sylvis processes the message, queries the proxy, and replies to you naturally.
6. **Verify Local Offline AI Mode**:
   - Set AI provider to **Local Offline AI**.
   - Input a message. Verify Sylvis responds using the Qwen model without trying to reach `fcc-server` or throwing connection errors.
7. **Firewall Verification**:
   - Ask Sylvis to open an application or run a test script. Confirm the firewall clearance dialog pops up borderlessly with a glowing red border and custom drag handles.
