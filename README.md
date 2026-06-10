# S.Y.L.V.I.S. (Synthetic Yielding Linguistic Virtual Intelligence System)

S.Y.L.V.I.S. is an open-source, fully autonomous, and highly visual Windows Desktop AI Assistant. Designed with a custom cyberpunk HUD aesthetic, she floats borderlessly on your screen, listens to system-wide hotkeys, speaks to you, and executes local command workflows on your PC with full security approval popups.

---

## 🎨 Core Features

- **Borderless HUD Visualizer**: A custom floating canvas visualizer orb (`SylvisWidget`) with rotating ticks, ambient reactor particles, and concentric telemetry grids.
- **Dynamic Telemetry Diagnostic Panel**: A command terminal console (`SylvisConsole`) featuring live CPU and RAM dashboard meters, a scrolling oscilloscope waveform, and control badges.
- **Global Hotkey Activator**: Press **Scroll Lock** or **Pause** at any time to instantly wake her up and record a voice command.
- **Dual AI Brain Engines**:
  - **Free Claude Server**: Connects locally through `fcc-server` to leverage Anthropic's Claude 3.5 Sonnet.
  - **Local Offline AI**: Lazy loads Qwen 2.5 (0.5B-Instruct) locally on your CPU for completely network-free companion chat.
- **Speech & Audio Integration**:
  - **Speech-to-Text**: Captures and processes commands using Google Speech Recognition.
  - **Text-to-Speech**: Supports native Windows SAPI5 offline voice, ElevenLabs, and Typecast.
- **Local PC Agent Execution**: With user permission clearance, Sylvis can run CMD/PowerShell commands, launch web apps, lock your workstation, and set master volume.
- **System Tray Support**: Minimize her fully to the taskbar tray for silent background monitoring.
- **SSL Bypass Support**: Auto-deactivates strict certificate checks for developer environments behind corporate proxy servers.

---

## 📦 File Architecture

- `app.py`: Main python application script containing UI layout, thread queues, and orchestration logic.
- `Launch Sylvis.vbs`: Helper VBScript to launch the assistant silently in the background without spawning terminal windows.
- `run.bat`: Primary command batch script that installs dependencies and runs the assistant using Python 3.11.
- `run_all_hidden.bat`: Background launcher that handles port reclamation and starts local servers silently.
- `manual.html`: Glowing interactive browser-based user manual.
- `requirements.txt`: Python package dependency listings.
- `static/`: Frontend web UI interface assets for local admin pages.

---

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.11**: Make sure Python 3.11 is installed on your Windows machine and registered in your system PATH environment.
- **NVIDIA NIM Account** (Optional for Free Claude Server): Create a free account at [build.nvidia.com](https://build.nvidia.com/) to obtain API tokens.

### Quick Start

1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/apexvoidd/sylvis.git
   cd sylvis
   ```
2. Double-click `run.bat` to automatically verify Python, install packages, and launch the assistant.
3. To launch in background hidden mode, run `Launch Sylvis.vbs`.

---

## ⚙️ Configuration & API Settings

Upon first-run, S.Y.L.V.I.S. will automatically open two browser tabs:
1. **Admin Control Panel** (`http://localhost:8082/admin`): Add your API keys (NVIDIA NIM token for Claude, ElevenLabs, or Typecast).
2. **User Manual**: The offline interactive handbook (`manual.html`) outlining advanced settings.

To re-open the settings manually, click the **SETTINGS** button inside the Terminal Console or right-click the central orb to access the context menu.

---

## 🛡️ License & Liability

This project is licensed under the **MIT License**. 

Anyone is free to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software. Contributions are highly welcomed!

**Disclaimer**: The software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability.
