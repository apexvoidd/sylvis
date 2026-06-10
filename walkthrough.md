# S.Y.L.V.I.S. UI Overhaul & Interactive Manual Walkthrough

The S.Y.L.V.I.S. PC Assistant has been upgraded to a **completely custom borderless futuristic desktop environment**. Window borders and standard title bars have been removed in favor of neon-lit HUD panels, real-time diagnostic grids, and an interactive browser-based User Manual.

---

## 🎨 Futuristic HUD Redesign

1. **Borderless Floating Windows (`overrideredirect`)**:
   - Standard Windows title bars, minimize/maximize boxes, and window borders have been completely removed from **SylvisConsole**, **SylvisSettingsWindow**, and **SecureApprovalWindow**.
   - The windows are rendered as floating sci-fi data decks, making them look highly integrated with your desktop.
   - **Glow Borders**: Added 2px neon borders surrounding each panel:
     - *Terminal Console*: Neon Cyan (`#00ffff`) glow border.
     - *Settings Panel*: Neon Pink/Magenta (`#ff007f`) glow border.
     - *Firewall Authorization Box*: Neon Red (`#ef4444`) glow border.

2. **Custom Window Drag Handlers**:
   - Because standard title bars are removed, clicking and dragging on the custom headers (or header label texts) of the Console, Settings, or Approval windows allows you to smoothly drag and reposition them anywhere on the screen.

3. **Active System Diagnostics Dashboard**:
   - Added a real-time diagnostics bar inside the header of the Command Terminal:
     - **CPU**: Live CPU load percentage (red text).
     - **RAM**: Live virtual memory utilization percentage (yellow text).
     - **BRAIN**: Shows the active cloud or local offline intelligence engine (cyan text).
     - **VOICE**: Displays the active text-to-speech speaker configuration (green text).
   - Metrics are polled and updated automatically in the background every 2 seconds.

4. **Visualizer Telemetry Indicators**:
   - Redesigned the Canvas drawing of the central orb widget (`SylvisWidget`) with futuristic HUD lines:
     - Corner framing brackets centered around the visualizer coordinates.
     - Concentric outer tech circles and dashed ring orbits.
     - Real-time **status telemetry badges** drawn above the core (e.g. `[SYS.ONLINE]`, `[REC.AUDIO]`, `[COMP.COGNITIVE]`, `[SYS.TRANSMIT]`) changing dynamically with state transitions.

---

## 📖 Interactive Web User Manual

1. **Cyberpunk User Manual (`manual.html`)**:
   - Created a standalone HTML document styled with a glowing dark theme using Google Fonts (`Outfit` and `JetBrains Mono`), glassmorphic content cards, and transition animations.
   - Includes full setup instructions for all components (waking hotkeys, context menus, low resource mode, offline local LLM files).

2. **Free API Setup Guide**:
   - Explains how to sign up and retrieve API keys for free:
     - **NVIDIA NIM**: Create an account on build.nvidia.com to get 1,000 free tokens for Claude 3.5 Sonnet.
     - **ElevenLabs**: Access 10k free monthly characters for high-fidelity speech.
     - **Typecast**: Access monthly characters for anime voice actors.

3. **In-App Integration**:
   - Added a **❓ MANUAL** button in the Console panel next to `SETTINGS` that automatically opens the local user manual in the user's default browser.
   - Added `manual.html` to PyInstaller's `--add-data` data bundling list so it is packed cleanly inside `Sylvis.exe`.

---

## 🛠️ Startup and State Fixes

5. **First-Run Launch Fix**:
   - Consolidated the first-run browser launch trigger. The `"first_run"` flag is now stored and persisted directly inside the main `~/.sylvis_settings.json` file.
   - This fixes a bug where the browser would open the admin settings page on every single startup. Now, the browser tabs (NVIDIA Admin settings & S.Y.L.V.I.S. User Manual) only open on the very first execution. Subsequent launches run silently.

---

## 🔒 SSL & Corporate Proxy Fixes (Claude Mode Recovery)

1. **Strict SSL Validation Bypass (`sitecustomize.py`)**:
   - Modern python environments (Python 3.12/3.13+) and OpenSSL 3.x enforce strict certificate verification (`VERIFY_X509_STRICT` enabled by default).
   - If you are behind a corporate proxy/firewall that signs HTTPS traffic using a custom root CA, OpenSSL rejects the corporate certificate because the CA's "Basic Constraints" extension isn't marked as critical (violating strict RFC standards).
   - Created a self-healing patch at `~/.fcc/python_patch/sitecustomize.py` that dynamically intercepts and clears `ssl.VERIFY_X509_STRICT` when Python's `ssl` module creates a context.
   - `app.py` has been updated to automatically verify/write this patch on startup and execute `fcc-server.exe` with `PYTHONPATH` set to the patch directory. This lets the proxy server connect securely to NVIDIA NIM.

2. **Local AI Branch Fix**:
   - Added a missing `return` statement to the local Qwen brain branch in `agent_chat_thread`. Switching to offline local mode now exits cleanly and no longer crashes when trying to execute Claude mode.

---

## 🔍 Verification Checklist

To verify the newly compiled borderless S.Y.L.V.I.S. PC Assistant:

1. **Trigger First Run**:
   - In settings, ensure `"first_run": true` (or delete `~/.sylvis_settings.json`).
2. **Launch Assistant**:
   - Double-click **[Sylvis.exe](file:///c:/Users/ayush/Downloads/New%20folder%20(2)/jarvis-pc/Sylvis.exe)**.
3. **Verify Browser Launch**:
   - Confirm that two browser tabs open automatically: the NVIDIA NIM proxy settings and the custom user manual page (`manual.html`).
   - Confirm that on subsequent restarts of `Sylvis.exe`, the browser does not open.
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

---

## 🔧 Threading & UI Bug Fixes (Scroll Lock & Text Chat Recovery)

1. **Global `gui_queue` Scope**:
   - Moved `gui_queue` initialization from the local `if __name__ == "__main__":` block to the global module scope of `app.py`.
   - This ensures that background thread workers and helper functions started at import time can safely put messages into the queue without triggering `NameError`.

2. **Added Missing `set_state` Method**:
   - Defined `set_state(self, state)` on `SylvisWidget` to correctly update `self.state = state`.
   - This prevents an `AttributeError` from being raised when the background threads request a state transition (e.g. `listening`, `processing`, `speaking`, `idle`), which was previously crashing the queue loop and disabling text/speech replies.

