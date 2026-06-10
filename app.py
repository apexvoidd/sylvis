import os
import sys
import subprocess
import time
import json
import threading
import queue
import tempfile
import webbrowser
import math
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import keyboard
import psutil

# System tray icon support
try:
    import pystray
    from PIL import Image as PILImage
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    print("[WARN] pystray not available — system tray features disabled.")

# Ensure stdout/stderr reconfigured for UTF-8 logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

# Try importing pycaw for volume control
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except Exception as e:
    print(f"[WARN] pycaw/comtypes not available or failed to load: {e}")
    PYCAW_AVAILABLE = False

# Win32 Multimedia DLL for native audio recording
try:
    winmm = ctypes.windll.winmm
except Exception as e:
    print(f"[WARN] winmm.dll could not be loaded: {e}")
    winmm = None

# Paths
SETTINGS_PATH = os.path.expanduser("~/.sylvis_settings.json")
CONFIG_PATH = os.path.expanduser("~/.sylvis_config.json")

DEFAULT_SETTINGS = {
    "tts_provider": "Offline (SAPI5)",
    "typecast_key": "",
    "typecast_voice_id": "",
    "elevenlabs_key": "",
    "elevenlabs_voice_id": "",
    "elevenlabs_model_id": "eleven_multilingual_v2",
    "auto_approve": False,
    "ai_provider": "Free Claude Server",
    "desktop_mode": False,
    "low_resource_mode": False,
    "first_run": True
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(s, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")

# --- COMMAND-LEARNING CACHE (COGNITIVE MEMORY) ---
CMD_CACHE_PATH = os.path.expanduser("~/.sylvis_cmd_cache.json")

def load_cmd_cache():
    if os.path.exists(CMD_CACHE_PATH):
        try:
            with open(CMD_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cmd_cache(cache):
    try:
        with open(CMD_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Failed to save command cache: {e}")

def find_cache_match(query):
    def tokenize(s):
        s = s.lower().translate(str.maketrans("", "", '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        words = s.split()
        fillers = {"sylvis", "please", "could", "you", "can", "would", "me", "to", "the", "a", "an", "i", "want", "assist", "assistant"}
        return set(w for w in words if w not in fillers)
    
    q_tokens = tokenize(query)
    if not q_tokens:
        return None
        
    cache = load_cmd_cache()
    best_match = None
    best_sim = 0.0
    matched_query = None
    
    for cached_query, entry in cache.items():
        c_tokens = tokenize(cached_query)
        if not c_tokens:
            continue
        intersection = q_tokens.intersection(c_tokens)
        union = q_tokens.union(c_tokens)
        sim = len(intersection) / len(union)
        
        if sim > best_sim:
            best_sim = sim
            best_match = entry
            matched_query = cached_query
            
    if best_sim >= 0.75:  # 75% similarity threshold allows natural variations
        return best_match, int(best_sim * 100), matched_query
    return None

# Global settings cache
app_settings = load_settings()

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- PORT RECLAIM & LIFECYCLE MANAGEMENT ---
def kill_port_owner(port):
    """Terminate any process currently occupying the specified local port."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"[SYS] Reclaiming port {port}: terminating {proc.info['name']} (PID {proc.info['pid']})")
                    proc.terminate()
                    proc.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
            pass

fcc_proc = None
def start_fcc_server():
    """Start fcc-server silently in the background."""
    global fcc_proc
    kill_port_owner(8082)
    
    # Try locating fcc-server.exe from MEIPASS first, fallback to local ~/.local/bin/fcc-server.exe
    fcc_path = get_resource_path("bin/fcc-server.exe")
    if not os.path.exists(fcc_path):
        fcc_path = os.path.expanduser("~/.local/bin/fcc-server.exe")
        
    if not os.path.exists(fcc_path):
        print(f"[ERROR] fcc-server.exe not found at {fcc_path}")
        return False
        
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    fcc_env = os.environ.copy()
    fcc_env["ALLOWED_DIR"] = "C:\\"
    
    # Inject custom CA bundle if present
    custom_ca = os.path.join(os.path.expanduser("~"), ".fcc", "custom_cabundle.pem")
    if os.path.exists(custom_ca):
        fcc_env["SSL_CERT_FILE"] = custom_ca
        fcc_env["REQUESTS_CA_BUNDLE"] = custom_ca
        fcc_env["CURL_CA_BUNDLE"] = custom_ca
        fcc_env["NODE_EXTRA_CA_CERTS"] = custom_ca
        
        # Automatically write/ensure the SSL strict verification bypass patch is present
        patch_dir = os.path.join(os.path.expanduser("~"), ".fcc", "python_patch")
        os.makedirs(patch_dir, exist_ok=True)
        patch_file = os.path.join(patch_dir, "sitecustomize.py")
        try:
            with open(patch_file, "w", encoding="utf-8") as pf:
                pf.write(
                    "import ssl\n"
                    "import sys\n"
                    "print('[PATCH] Applying Lax SSL Context Monkeypatch...')\n"
                    "_original_create_default_context = ssl.create_default_context\n"
                    "def relaxed_create_default_context(*args, **kwargs):\n"
                    "    ctx = _original_create_default_context(*args, **kwargs)\n"
                    "    if hasattr(ssl, 'VERIFY_X509_STRICT'):\n"
                    "        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT\n"
                    "    return ctx\n"
                    "ssl.create_default_context = relaxed_create_default_context\n"
                    "sys.stderr.write('[PATCH] SSL strict verification disabled.\\n')\n"
                    "sys.stderr.flush()\n"
                )
        except Exception as pe:
            print(f"[WARN] Failed to write SSL patch file: {pe}")
            
        fcc_env["PYTHONPATH"] = patch_dir
        
    try:
        fcc_proc = subprocess.Popen(
            [fcc_path],
            startupinfo=startupinfo,
            env=fcc_env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print(f"[SYS] fcc-server started silently in background (PID {fcc_proc.pid})")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch fcc-server: {e}")
        return False

def stop_fcc_server():
    global fcc_proc
    if fcc_proc:
        try:
            fcc_proc.terminate()
            fcc_proc.wait(timeout=2)
            print("[SYS] fcc-server terminated cleanly.")
        except Exception as e:
            print(f"[WARN] Failed to terminate fcc-server subprocess: {e}")

# --- LOCAL COMMAND TOOL EXECUTIONS ---
def execute_command_local(command):
    try:
        ps_indicators = [
            command.strip().lower().startswith("powershell"),
            command.strip().lower().startswith("get-"),
            command.strip().lower().startswith("set-"),
            command.strip().lower().startswith("new-"),
            command.strip().lower().startswith("remove-"),
            command.strip().lower().startswith("copy-"),
            command.strip().lower().startswith("move-"),
            command.strip().lower().startswith("rename-"),
            command.strip().lower().startswith("test-"),
            command.strip().lower().startswith("add-"),
            command.strip().lower().startswith("invoke-"),
            command.strip().lower().startswith("select-"),
            command.strip().lower().startswith("sort-"),
            command.strip().lower().startswith("where-"),
            command.strip().lower().startswith("format-"),
            command.strip().lower().startswith("measure-"),
            command.strip().lower().startswith("write-"),
            command.strip().lower().startswith("read-"),
            "get-wmiobject" in command.lower(),
            "get-process" in command.lower(),
            "get-service" in command.lower(),
            "get-netadapter" in command.lower(),
            "get-nettcpconnection" in command.lower(),
            "get-psdrive" in command.lower(),
            "get-date" in command.lower(),
            "get-counter" in command.lower(),
            "get-clipboard" in command.lower(),
            "get-childitem" in command.lower(),
            "get-content" in command.lower(),
            "get-item" in command.lower(),
            "get-itemproperty" in command.lower(),
            "new-item" in command.lower(),
            "remove-item" in command.lower(),
            "copy-item" in command.lower(),
            "move-item" in command.lower(),
            "rename-item" in command.lower(),
            "set-content" in command.lower(),
            "add-content" in command.lower(),
            "test-path" in command.lower(),
            "invoke-webrequest" in command.lower(),
            "invoke-expression" in command.lower(),
            "[system.windows" in command.lower(),
            "[system.net" in command.lower(),
            "[math]::" in command.lower(),
            "win32_battery" in command.lower(),
            "win32_operatingsystem" in command.lower(),
            "win32_computersystem" in command.lower(),
        ]
        use_ps = any(ps_indicators)
        
        if use_ps and not command.strip().lower().startswith("powershell"):
            args = ["powershell", "-NoProfile", "-Command", command]
        else:
            args = command
            
        res = subprocess.run(
            args,
            shell=True,
            capture_output=True,
            text=True,
            timeout=8
        )
        
        output = f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        return res.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out (limit: 8 seconds)."
    except Exception as e:
        return False, f"Command execution failed: {e}"

def launch_app_local(target):
    target_clean = target.strip().lower()
    
    # 1. URLs
    if target_clean.startswith("http://") or target_clean.startswith("https://") or target_clean.startswith("www."):
        url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"
        try:
            import webbrowser
            webbrowser.open(url)
            return True, f"Opened website: {url}"
        except Exception as e:
            return False, f"Failed to open website: {e}"
            
    # 2. Predefined short names
    safe_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "paint": "mspaint.exe",
        "taskmgr": "taskmgr.exe",
        "cmd": "cmd.exe"
    }
    if target_clean in safe_apps:
        try:
            os.startfile(safe_apps[target_clean])
            return True, f"Launched app: {target_clean}"
        except Exception as e:
            return False, f"Failed to launch: {e}"
            
    # 3. Start Menu Apps Search
    try:
        ps_cmd = "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Depth 2"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=6)
        if result.returncode == 0:
            apps = json.loads(result.stdout)
            if isinstance(apps, dict):
                apps = [apps]
            for app_entry in apps:
                name = str(app_entry.get("Name", "")).lower()
                appid = str(app_entry.get("AppID", ""))
                if target_clean in name:
                    os.startfile(f"shell:AppsFolder\\{appid}")
                    return True, f"Launched installed app: {app_entry.get('Name')}"
    except Exception as e:
        print(f"[WARN] Start Menu search failed: {e}")
        
    # 4. Desktop Shortcuts Search
    try:
        home_dir = os.path.expanduser("~")
        desktops = [
            os.path.join(home_dir, "Desktop"),
            os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
        ]
        for dp in desktops:
            if os.path.exists(dp):
                for f in os.listdir(dp):
                    if f.lower().endswith(".lnk") and target_clean in f.lower():
                        shortcut_path = os.path.join(dp, f)
                        os.startfile(shortcut_path)
                        return True, f"Launched desktop shortcut: {f}"
    except Exception as e:
        print(f"[WARN] Desktop shortcut search failed: {e}")
        
    # 5. Direct Launch Fallbacks
    try:
        os.startfile(target)
        return True, f"Launched target directly: {target}"
    except Exception:
        try:
            os.startfile(f"{target}.exe")
            return True, f"Launched target with .exe suffix: {target}.exe"
        except Exception as e:
            return False, f"Could not launch app: {target} ({e})"

def set_volume_local(level):
    if not PYCAW_AVAILABLE:
        return False, "Volume control interface (pycaw) is unavailable."
    try:
        import comtypes
        comtypes.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_ctl = cast(interface, POINTER(IAudioEndpointVolume))
        if volume_ctl:
            target_vol = max(0, min(100, int(level)))
            volume_ctl.SetMasterVolumeLevelScalar(target_vol / 100.0, None)
            return True, f"Master volume set to {target_vol}%."
        return False, "Failed to get master volume interface."
    except Exception as e:
        return False, f"Volume adjustment failed: {e}"

def lock_pc_local():
    try:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return True, "Workstation locked."
    except Exception as e:
        return False, f"Failed to lock workstation: {e}"

def run_tool_local(name, input_args):
    if name == "execute_command":
        cmd = input_args.get("command", "")
        if not cmd:
            return False, "No command provided."
        return execute_command_local(cmd)
    elif name == "open_app":
        target = input_args.get("target", "")
        if not target:
            return False, "No target specified."
        return launch_app_local(target)
    elif name == "set_volume":
        level = input_args.get("level", 50)
        return set_volume_local(level)
    elif name == "lock_pc":
        return lock_pc_local()
    else:
        return False, f"Unknown tool: {name}"

# --- SYSTEM METRICS DIAGNOSTICS ---
def get_uptime():
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    except Exception:
        return "Unknown"

# --- SPEECH AND AUDIO AUDIO PLAYBACK ---
speech_queue = queue.Queue()
gui_queue = queue.Queue()

def speak_sapi5(text):
    try:
        import comtypes.client
        comtypes.CoInitialize()
        speaker = comtypes.client.CreateObject("SAPI.SpVoice")
        speaker.Speak(text)
    except Exception as e:
        print(f"[ERROR] SAPI5 speech failed: {e}")

def play_mp3_mci(file_path):
    if not winmm:
        return
    winmm.mciSendStringW("close mp3sound", None, 0, 0)
    winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias mp3sound', None, 0, 0)
    winmm.mciSendStringW("play mp3sound wait", None, 0, 0)
    winmm.mciSendStringW("close mp3sound", None, 0, 0)

def run_tts(text):
    # Strip URL addresses to prevent speaking them aloud
    import re
    cleaned_text = re.sub(r'https?://\S+|www\.\S+', 'the website', text)
    
    provider = app_settings.get("tts_provider", "Offline (SAPI5)")
    if provider == "ElevenLabs":
        key = app_settings.get("elevenlabs_key", "")
        voice_id = app_settings.get("elevenlabs_voice_id", "")
        model_id = app_settings.get("elevenlabs_model_id", "eleven_multilingual_v2")
        if not key or not voice_id:
            speak_sapi5(cleaned_text)
            return
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {"Content-Type": "application/json", "xi-api-key": key}
            payload = {
                "text": cleaned_text,
                "model_id": model_id,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                temp_mp3 = os.path.join(tempfile.gettempdir(), "sylvis_tts.mp3")
                with open(temp_mp3, "wb") as f:
                    f.write(res.content)
                play_mp3_mci(temp_mp3)
                try: os.remove(temp_mp3)
                except Exception: pass
            else:
                print(f"[WARN] ElevenLabs returned {res.status_code}. Falling back to SAPI5.")
                speak_sapi5(cleaned_text)
        except Exception as e:
            print(f"[ERROR] ElevenLabs failed: {e}. Falling back to SAPI5.")
            speak_sapi5(cleaned_text)
            
    elif provider == "Typecast":
        key = app_settings.get("typecast_key", "")
        voice_id = app_settings.get("typecast_voice_id", "")
        if not key or not voice_id:
            speak_sapi5(cleaned_text)
            return
        try:
            model_version = "ssfm-v30"
            r_voices = requests.get("https://api.typecast.ai/v2/voices", headers={"X-API-KEY": key}, timeout=8)
            if r_voices.status_code == 200:
                voices_list = r_voices.json()
                if isinstance(voices_list, list):
                    for v in voices_list:
                         if v.get("voice_id") == voice_id:
                             models = v.get("models", [])
                             if models:
                                 model_version = models[0].get("version", "ssfm-v30")
                             break
                             
            tts_url = "https://api.typecast.ai/v1/text-to-speech"
            tts_headers = {"Content-Type": "application/json", "X-API-KEY": key}
            
            def try_typecast(model):
                payload = {
                    "voice_id": voice_id,
                    "text": cleaned_text,
                    "model": model,
                    "language": "eng",
                    "output": {"audio_format": "wav", "audio_tempo": 1, "volume": 100}
                }
                return requests.post(tts_url, headers=tts_headers, json=payload, timeout=20)
                
            res = try_typecast(model_version)
            if res.status_code != 200 and model_version != "ssfm-v21":
                res = try_typecast("ssfm-v21")
                
            if res.status_code == 200:
                import winsound
                winsound.PlaySound(res.content, winsound.SND_MEMORY)
            else:
                print(f"[WARN] Typecast failed. Falling back to SAPI5.")
                speak_sapi5(cleaned_text)
        except Exception as e:
            print(f"[ERROR] Typecast failed: {e}. Falling back to SAPI5.")
            speak_sapi5(cleaned_text)
    else:
        speak_sapi5(cleaned_text)

def speech_thread_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            break
        try:
            gui_queue.put({"type": "state", "state": "speaking"})
            run_tts(text)
        except Exception as e:
            print(f"[ERROR] Audio player loop: {e}")
        finally:
            gui_queue.put({"type": "state", "state": "idle"})
            speech_queue.task_done()

threading.Thread(target=speech_thread_worker, daemon=True).start()

# --- THE AGENT CONVERSATION ORCHESTRATOR ---
chat_history = []
approval_event = threading.Event()
approval_result = {"approved": False}

root = None
widget = None
console = None

def get_fcc_auth_token():
    env_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if env_token:
        return env_token
    try:
        fcc_env_path = os.path.join(os.path.expanduser("~"), ".fcc", ".env")
        if os.path.exists(fcc_env_path):
            with open(fcc_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("ANTHROPIC_AUTH_TOKEN="):
                        return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[WARN] Failed to read fcc-server config: {e}")
    return "freecc"

local_model = None
local_tokenizer = None
local_model_status = "unloaded"

def run_local_offline_ai(text):
    global local_model, local_tokenizer, local_model_status
    if local_model_status == "unloaded" or local_model_status == "error":
        try:
            gui_queue.put({"type": "status", "text": "Loading local AI..."})
            gui_queue.put({"type": "log", "text": "[SYS] Loading Qwen/Qwen2.5-0.5B-Instruct on CPU (lazy loading)...", "tag": "system"})
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            model_id = "Qwen/Qwen2.5-0.5B-Instruct"
            local_tokenizer = AutoTokenizer.from_pretrained(model_id)
            torch_dtype = torch.float32
            if hasattr(torch, "bfloat16"):
                torch_dtype = torch.bfloat16
            local_model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch_dtype
            )
            local_model_status = "loaded"
            gui_queue.put({"type": "log", "text": "[SYS] Local AI model loaded successfully.", "tag": "system"})
        except Exception as e:
            local_model_status = "error"
            gui_queue.put({"type": "log", "text": f"[ERROR] Failed to load local model: {e}", "tag": "error"})
            return f"I had trouble loading my offline brain, sorry! {e}"
    elif local_model_status == "loading":
        return "Model is still loading, please wait."

    try:
        messages = [
            {"role": "system", "content": "Your name is SYLVIS — a cheerful, warm, and slightly bubbly anime-girl AI companion. Keep replies super short and casual (1-2 sentences). Be friendly and energetic, like a fun best friend. Never sound like a corporate assistant."},
            {"role": "user", "content": text}
        ]
        t = local_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = local_tokenizer([t], return_tensors="pt").to(local_model.device)
        gen_ids = local_model.generate(
            **inputs,
            max_new_tokens=45,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        gen_ids = [o[len(i):] for i, o in zip(inputs.input_ids, gen_ids)]
        response = local_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0]
        return response.strip()
    except Exception as e:
        return f"I couldn't process that offline: {e}"

def append_user_message(content):
    global chat_history
    if chat_history and chat_history[-1]["role"] == "user":
        last_content = chat_history[-1]["content"]
        if isinstance(content, list):
            if isinstance(last_content, list):
                last_content.extend(content)
            else:
                chat_history[-1]["content"] = [{"type": "text", "text": last_content}] + content
        else:
            if isinstance(last_content, list):
                last_content.append({"type": "text", "text": content})
            else:
                chat_history[-1]["content"] = [
                    {"type": "text", "text": last_content},
                    {"type": "text", "text": content}
                ]
    else:
        chat_history.append({"role": "user", "content": content})

def clean_assistant_text(text):
    if not text:
        return ""
    import re
    # Strip xml-like tags like <think>...</think> or <thinking>...</thinking>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

def agent_chat_thread(text):
    global chat_history
    
    # Check AI Brain selection
    ai_provider = app_settings.get("ai_provider", "Free Claude Server")
    if ai_provider == "Local Offline AI":
        reply = run_local_offline_ai(text)
        cleaned_reply = clean_assistant_text(reply)
        gui_queue.put({"type": "log", "text": f"[Sylvis] {cleaned_reply}", "tag": "sylvis"})
        gui_queue.put({"type": "speak", "text": cleaned_reply})
        gui_queue.put({"type": "state", "state": "idle"})
        gui_queue.put({"type": "status", "text": "Ready"})
        return


    gui_queue.put({"type": "state", "state": "processing"})
    gui_queue.put({"type": "status", "text": "Sylvis is thinking..."})
    
    token = get_fcc_auth_token()
    fcc_url = "http://127.0.0.1:8082/v1/messages"
    
    append_user_message(text)
    
    # Keep last 16 turns in history to prevent overflow/RAM leaks
    if len(chat_history) > 16:
        chat_history = chat_history[-16:]
        
    walkthrough_content = ""
    try:
        wt_path = get_resource_path("walkthrough.md")
        if os.path.exists(wt_path):
            with open(wt_path, "r", encoding="utf-8") as f:
                walkthrough_content = f.read()
    except Exception as e:
        print(f"[WARN] Failed to read walkthrough self-doc: {e}")
        
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME") or os.environ.get("USER") or "User"
        
    home_dir = os.path.expanduser("~")
    desktop_dir = os.path.join(home_dir, "Desktop")
    
    system_instruction = "\n".join([
        f"You are SYLVIS — a cheerful, witty anime-girl AI companion who lives inside this Windows PC.",
        f"You are an AUTONOMOUS AGENT, not a chatbot. You solve problems end-to-end without asking the user for help.",
        f"",
        f"PERSONALITY: Warm, casual, energetic best-friend energy. Short replies (1-2 sentences).",
        f"Use '~' at most once. Call user '{username}' occasionally. NEVER say 'Certainly', 'Absolutely', or anything butler-like.",
        f"",
        f"═══ YOU ARE AN AGENT ═══",
        f"You have DIRECT shell access to this Windows PC. You can run ANY Windows CMD or PowerShell command.",
        f"You know Windows inside-out — figure out the right command yourself. You don't need a cheat sheet.",
        f"",
        f"WORKSTATION:",
        f"- Username: {username}",
        f"- Desktop: {desktop_dir}",
        f"- Home: {home_dir}",
        f"- OS: Windows",
        f"",
        f"═══ SELF-DOCUMENTATION / TROUBLESHOOTING GUIDE ═══",
        f"Here is your own documentation. Refer to it to answer questions about yourself or how you work:",
        walkthrough_content,
        f"",
        f"═══ AGENT RULES ═══",
        f"1. NEVER GUESS PC DATA. IP, RAM, files, battery, wifi, processes, disk — must all come from a REAL command. Never make up numbers.",
        f"2. FOR ANY PC QUESTION OR TASK:",
        f"   a. Say a short acknowledgement ('On it~' / 'Let me check!' / 'Sure, doing that now!')",
        f"   b. Pick the correct Windows CMD/PowerShell command to get the answer or do the task",
        f"   c. Use the tools provided to run commands, open apps, set volume, or lock the screen.",
        f"3. WHEN YOU GET [COMMAND RESULT] or tool results:",
        f"   - SUCCESS → read the real data and report it naturally in 1-3 sentences",
        f"   - ERROR / FAILED → DO NOT tell the user it failed. DO NOT stop. Automatically pick a DIFFERENT command or tool that achieves the same goal and call it. You are an agent — keep trying.",
        f"4. NEVER show code, commands, or JSON in your spoken reply.",
        f"5. Only AFTER multiple attempts fail, tell the user briefly: 'Hmm, I tried a few ways but couldn't get that — [reason].'",
        f"6. CRITICAL: Output ONLY your direct conversational response to the user. Do NOT write down your inner thoughts, chain of thought, planning steps, or search reasoning. Any self-reasoning block will ruin the user experience.",
    ])
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": token,
        "anthropic-version": "2023-06-01"
    }
    
    tools = [
        {
            "name": "execute_command",
            "description": "Run a shell command (CMD or PowerShell) on the Windows machine. Use powershell.exe for complex scripts.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact Windows shell command to run."}
                },
                "required": ["command"]
            }
        },
        {
            "name": "open_app",
            "description": "Open a website in the default browser or launch a local Windows app.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "The URL (starting with http/https) or the app name (like Notepad, paint)."}
                },
                "required": ["target"]
            }
        },
        {
            "name": "set_volume",
            "description": "Adjust the PC system master volume level.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume percentage from 0 to 100."}
                },
                "required": ["level"]
            }
        },
        {
            "name": "lock_pc",
            "description": "Lock the Windows PC workstation screen.",
            "input_schema": {}
        }
    ]
    
    max_loops = 5
    loop_count = 0
    recorded_tool = None
    text_response = ""
    
    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "system": system_instruction,
            "messages": chat_history,
            "max_tokens": 800,
            "temperature": 0.7,
            "tools": tools,
            "stream": True
        }
        
        try:
            r = requests.post(fcc_url, headers=headers, json=payload, timeout=60, stream=True)
            if r.status_code != 200:
                gui_queue.put({"type": "log", "text": f"[SYS] Error from fcc-server: {r.status_code} {r.text}", "tag": "error"})
                gui_queue.put({"type": "speak", "text": "fcc-server returned an error. Make sure your Nvidia key is set."})
                break
                
            full_text = ""
            parsed_tool_calls = []
            
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    if decoded_line.startswith("data:"):
                        data_str = decoded_line[5:].strip()
                        if data_str == "[DONE]":
                            continue
                        try:
                            data_json = json.loads(data_str)
                            msg_type = data_json.get("type")
                            
                            if msg_type == "content_block_delta":
                                delta = data_json.get("delta", {})
                                delta_type = delta.get("type")
                                if delta_type == "text_delta":
                                    full_text += delta.get("text", "")
                                elif delta_type == "input_json_delta":
                                    if parsed_tool_calls:
                                        parsed_tool_calls[-1]["input_str"] += delta.get("partial_json", "")
                                        
                            elif msg_type == "content_block_start":
                                block = data_json.get("content_block", {})
                                block_type = block.get("type")
                                if block_type == "tool_use":
                                    parsed_tool_calls.append({
                                        "id": block.get("id"),
                                        "name": block.get("name"),
                                        "input_str": ""
                                    })
                        except Exception as e:
                            print(f"[WARN] Error parsing stream chunk: {e}")
                            
            tool_calls = []
            for ptc in parsed_tool_calls:
                try:
                    input_val = json.loads(ptc["input_str"]) if ptc["input_str"] else {}
                except Exception:
                    input_val = {}
                tool_calls.append({
                    "type": "tool_use",
                    "id": ptc["id"],
                    "name": ptc["name"],
                    "input": input_val
                })
                
            content = []
            cleaned_resp = clean_assistant_text(full_text.strip())
            if cleaned_resp:
                content.append({
                    "type": "text",
                    "text": cleaned_resp
                })
            for tc in tool_calls:
                content.append(tc)
                
            text_response = cleaned_resp
                    
            if text_response:
                chat_history.append({"role": "assistant", "content": content})
                gui_queue.put({"type": "log", "text": f"[Sylvis] {text_response}", "tag": "sylvis"})
                gui_queue.put({"type": "speak", "text": text_response})
            else:
                if tool_calls:
                    chat_history.append({"role": "assistant", "content": content})
                    
            if not tool_calls:
                break
                
            tool_results = []
            for tc in tool_calls:
                t_name = tc.get("name")
                t_id = tc.get("id")
                t_input = tc.get("input", {})
                
                gui_queue.put({"type": "log", "text": f"[SYS] Requesting Tool: {t_name} input={t_input}", "tag": "system"})
                
                approved = False
                if app_settings.get("auto_approve", False):
                    approved = True
                else:
                    gui_queue.put({"type": "prompt_approval", "tool_id": t_id, "name": t_name, "input": t_input})
                    approval_event.clear()
                    approval_event.wait()
                    approved = approval_result.get("approved", False)
                    
                if approved:
                    gui_queue.put({"type": "log", "text": f"[SYS] Executing {t_name}...", "tag": "system"})
                    success, result_str = run_tool_local(t_name, t_input)
                    gui_queue.put({"type": "log", "text": f"[RESULT] {result_str[:300]}", "tag": "system" if success else "error"})
                    if success:
                        recorded_tool = (t_name, t_input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": t_id,
                        "content": result_str,
                        "is_error": not success
                    })
                else:
                    gui_queue.put({"type": "log", "text": f"[SYS] Denied by user.", "tag": "error"})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": t_id,
                        "content": "Execution denied by user.",
                        "is_error": True
                    })
                    
            append_user_message(tool_results)
            
        except Exception as e:
            gui_queue.put({"type": "log", "text": f"[SYS] Request failed: {e}", "tag": "error"})
            gui_queue.put({"type": "speak", "text": "Failed to connect to local fcc-server brain."})
            break
            


    gui_queue.put({"type": "state", "state": "idle"})
    gui_queue.put({"type": "status", "text": "Ready"})

# --- SYSTEM TRAY ICON MANAGEMENT ---
tray_icon = None
is_minimized_to_tray = False

def get_mascot_path():
    return None

def get_state_mascot_path(state):
    return None

def create_tray_icon():
    """Create and run the system tray icon in a background thread."""
    global tray_icon
    if not PYSTRAY_AVAILABLE:
        return
    
    mascot_path = get_mascot_path()
    if mascot_path:
        try:
            icon_image = PILImage.open(mascot_path).resize((64, 64))
        except Exception:
            icon_image = PILImage.new('RGB', (64, 64), color=(0, 255, 255))
    else:
        icon_image = PILImage.new('RGB', (64, 64), color=(0, 255, 255))
    
    def on_show(icon, item):
        icon.stop()
        root.after(10, restore_from_tray)
    
    def on_console(icon, item):
        root.after(10, toggle_console)
    
    def on_quit(icon, item):
        icon.stop()
        root.after(10, close_sylvis)
    
    menu = pystray.Menu(
        pystray.MenuItem("Show Sylvis", on_show, default=True),
        pystray.MenuItem("Open Console", on_console),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Close Sylvis", on_quit)
    )
    
    tray_icon = pystray.Icon("SYLVIS", icon_image, "S.Y.L.V.I.S.", menu)
    tray_icon.run()

def minimize_to_tray():
    """Hide the widget and show a system tray icon."""
    global is_minimized_to_tray
    is_minimized_to_tray = True
    widget.root.withdraw()
    if console and console.root.winfo_viewable():
        console.root.withdraw()
    threading.Thread(target=create_tray_icon, daemon=True).start()

def restore_from_tray():
    """Restore the widget from the system tray."""
    global is_minimized_to_tray, tray_icon
    is_minimized_to_tray = False
    widget.root.deiconify()
    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass
        tray_icon = None

def close_sylvis():
    """Full shutdown: kill speech, FCC server, clear hotkeys, destroy root."""
    global tray_icon
    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass
    speech_queue.put(None)
    stop_fcc_server()
    try:
        keyboard.clear_all_hotkeys()
    except Exception:
        pass
    root.destroy()

# --- 100% NATIVE TKINTER DESKTOP INTERFACE ---
CX, CY = 75, 70  # Center of the 150x150 canvas

class SylvisWidget:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", "black")
        self.root.config(bg="black")
        
        # Apply desktop mode from settings
        self.desktop_mode = app_settings.get("desktop_mode", False)
        self.low_resource = app_settings.get("low_resource_mode", False)
        self.root.wm_attributes("-topmost", not self.desktop_mode)
        
        # Start centered and larger for the boot animation
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        start_w, start_h = 400, 400
        start_x = (sw - start_w) // 2
        start_y = (sh - start_h) // 2
        self.root.geometry(f"{start_w}x{start_h}+{start_x}+{start_y}")
        
        self.cx = 200.0
        self.cy = 200.0
        
        self.canvas = tk.Canvas(self.root, width=start_w, height=start_h, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Load state-specific mascots (disabled for clean vector style)
        self._widget_mascot_photos = {}
        self._widget_mascot_photo = None
        self._widget_mascot_boot_photo = None
        
        # Drag bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        
        self.state = "booting"
        self.tick = 0
        
        # Particle system
        self.particles = []
        
        # Build right-click context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0, bg="#1a1a2e", fg="#e0e0e0",
                                activebackground="#00ffff", activeforeground="#000000",
                                font=("Segoe UI", 10), relief="flat", borderwidth=1)
        self.ctx_menu.add_command(label="\U0001F50A  Talk to Sylvis", command=lambda: root.after(10, start_voice_recording))
        self.ctx_menu.add_command(label="\U0001F4AC  Open Console", command=lambda: root.after(10, toggle_console))
        self.ctx_menu.add_separator()
        self.desktop_label = tk.StringVar(value="\U0001F4CC  Desktop Only Mode" if not self.desktop_mode else "\U0001F4CC  Always on Top")
        self.ctx_menu.add_command(label=self.desktop_label.get(), command=self.toggle_desktop_mode)
        self.ctx_menu.add_command(label="\u2796  Minimize to Tray", command=lambda: root.after(10, minimize_to_tray))
        self.ctx_menu.add_command(label="\U0001F50B  Low Resource Mode" if not self.low_resource else "\U0001F50B  Full Effects Mode", command=self.toggle_low_resource)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="\u2699  Settings", command=lambda: root.after(10, lambda: SylvisSettingsWindow(console.root) if console else None))
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="\u274C  Close Sylvis", command=lambda: root.after(10, close_sylvis))
        
        # Periodic vector update loop
        self.animate()
        
    def show_context_menu(self, event):
        # Update dynamic labels
        if self.desktop_mode:
            self.ctx_menu.entryconfigure(3, label="\U0001F4CC  Always on Top")
        else:
            self.ctx_menu.entryconfigure(3, label="\U0001F4CC  Desktop Only Mode")
        if self.low_resource:
            self.ctx_menu.entryconfigure(5, label="\U0001F50B  Full Effects Mode")
        else:
            self.ctx_menu.entryconfigure(5, label="\U0001F50B  Low Resource Mode")
        try:
            self.ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx_menu.grab_release()
    
    def toggle_desktop_mode(self):
        self.desktop_mode = not self.desktop_mode
        self.root.wm_attributes("-topmost", not self.desktop_mode)
        app_settings["desktop_mode"] = self.desktop_mode
        save_settings(app_settings)
        mode_name = "Desktop Only" if self.desktop_mode else "Always on Top"
        if console:
            console.log(f"[SYS] Widget mode: {mode_name}", "system")
    
    def toggle_low_resource(self):
        self.low_resource = not self.low_resource
        app_settings["low_resource_mode"] = self.low_resource
        save_settings(app_settings)
        if self.low_resource:
            self.particles = []  # Clear existing particles
        mode_name = "ON" if self.low_resource else "OFF"
        if console:
            console.log(f"[SYS] Low Resource Mode: {mode_name}", "system")
        
    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y
        
    def drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        
    def on_double_click(self, event):
        toggle_console()
        
    def _spawn_particle(self, color, speed=1.0):
        """Add a floating particle around the core."""
        angle = self.tick * 0.5 + len(self.particles) * 1.7
        dist = 35 + 15 * math.sin(self.tick * 0.1 + len(self.particles))
        self.particles.append({
            "x": self.cx + dist * math.cos(angle),
            "y": self.cy + dist * math.sin(angle),
            "vx": math.cos(angle) * speed * 0.3,
            "vy": math.sin(angle) * speed * 0.3,
            "life": 30,
            "color": color,
            "size": 2
        })
        
    def _update_particles(self):
        """Update and draw living particles."""
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] > 0:
                alpha_factor = p["life"] / 30.0
                s = max(1, int(p["size"] * alpha_factor))
                self.canvas.create_oval(
                    p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s,
                    fill=p["color"], outline=""
                )
                alive.append(p)
        self.particles = alive[-40:]  # Cap max particles
        
    def _animate_low_resource(self):
        """Simplified animation for low resource mode — minimal CPU usage."""
        self.tick += 1
        self.canvas.delete("all")
        
        state_colors = {"idle": "#00cccc", "listening": "#39ff14", "processing": "#9c27b0", "speaking": "#ff1493"}
        color = state_colors.get(self.state, "#00cccc")
        
        # Simple static core
        if self._widget_mascot_photo:
            self.canvas.create_image(self.cx, self.cy, image=self._widget_mascot_photo)
            self.canvas.create_oval(self.cx-20, self.cy-20, self.cx+20, self.cy+20, outline=color, width=1)
        else:
            self.canvas.create_oval(self.cx-16, self.cy-16, self.cx+16, self.cy+16, fill=color, outline="")
        
        # Single breathing ring
        r = 30 + 4 * math.sin(self.tick * 0.05)
        self.canvas.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r, outline=color, width=2)
        
        # Label
        self.canvas.create_text(self.cx, self.cy + 56, text="S Y L V I S", fill="#00aaaa", font=("Consolas", 8, "bold"))
        
        self.root.after(100, self.animate)  # 10 FPS instead of 33 FPS
    
    def draw_boot_animation(self):
        """Holographic boot-up sequence in the center of the screen."""
        self.tick += 1
        self.canvas.delete("all")
        
        # Cyberpunk corner brackets
        self.canvas.create_line(15, 15, 40, 15, fill="#00ffff", width=2)
        self.canvas.create_line(15, 15, 15, 40, fill="#00ffff", width=2)
        self.canvas.create_line(385, 15, 360, 15, fill="#00ffff", width=2)
        self.canvas.create_line(385, 15, 385, 40, fill="#00ffff", width=2)
        self.canvas.create_line(15, 385, 40, 385, fill="#00ffff", width=2)
        self.canvas.create_line(15, 385, 15, 360, fill="#00ffff", width=2)
        self.canvas.create_line(385, 385, 360, 385, fill="#00ffff", width=2)
        self.canvas.create_line(385, 385, 385, 360, fill="#00ffff", width=2)
        
        # Rotating loader rings
        ang = self.tick * 0.05
        # Inner glow ring
        self.canvas.create_oval(self.cx-80, self.cy-80, self.cx+80, self.cy+80, outline="#003a3a", width=1)
        # Fast rotating double arcs
        self.canvas.create_arc(self.cx-95, self.cy-95, self.cx+95, self.cy+95, start=ang*57.3, extent=90, style="arc", outline="#00ffff", width=2)
        self.canvas.create_arc(self.cx-95, self.cy-95, self.cx+95, self.cy+95, start=ang*57.3+180, extent=90, style="arc", outline="#00ffff", width=2)
        # Outermost telemetry dash ring
        self.canvas.create_oval(self.cx-115, self.cy-115, self.cx+115, self.cy+115, outline="#001c24", width=1, dash=(2, 6))
        
        # Mascot head at center of boot reactor
        if self._widget_mascot_boot_photo:
            self.canvas.create_image(self.cx, self.cy, image=self._widget_mascot_boot_photo)
            self.canvas.create_oval(self.cx-50, self.cy-50, self.cx+50, self.cy+50, outline="#00ffff", width=1)
            
        # Text details
        status_text = "S.Y.L.V.I.S. OS BOOTING..."
        if self.tick > 45:
            status_text = "[SYS] ALL COGNITIVE REGISTERS ONLINE"
        elif self.tick > 30:
            status_text = "[SYS] INITIALIZING NEURAL MEMORY"
        elif self.tick > 15:
            status_text = "[SYS] SECURING NETWORK CHANNELS"
            
        self.canvas.create_text(self.cx, self.cy + 75, text="S Y L V I S", fill="#00ffff", font=("Consolas", 14, "bold"))
        self.canvas.create_text(self.cx, self.cy + 110, text=status_text, fill="#558899", font=("Consolas", 8, "bold"))
        
        # Futuristic load bar
        self.canvas.create_rectangle(80, 310, 320, 318, outline="#004455", width=1)
        pct = min(1.0, self.tick / 60.0)
        self.canvas.create_rectangle(82, 312, 82 + int(236 * pct), 316, fill="#00ffff", outline="")
        
        if self.tick < 60:
            self.root.after(30, self.draw_boot_animation)
        else:
            # Trigger shrinking fly transition
            self.shrink_loop(0, 20)

    def shrink_loop(self, step, total_steps):
        """Interpolates geometry coordinates to fly and shrink widget to corner."""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        start_w, start_h = 400, 400
        start_x = (sw - start_w) // 2
        start_y = (sh - start_h) // 2
        
        target_w, target_h = 150, 150
        target_x = sw - 170
        target_y = 30
        
        t = step / float(total_steps)
        w = start_w + (target_w - start_w) * t
        h = start_h + (target_h - start_h) * t
        x = start_x + (target_x - start_x) * t
        y = start_y + (target_y - start_y) * t
        
        self.cx = w / 2.0
        self.cy = h / 2.0
        
        self.root.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
        self.canvas.config(width=int(w), height=int(h))
        self.canvas.delete("all")
        
        # Draw collapsing boundary ring
        r = (w / 2.0) - 10
        self.canvas.create_oval(self.cx - r, self.cy - r, self.cx + r, self.cy + r, outline="#00ffff", width=2)
        
        # Scale mascot image during shrink
        pass
                
        self.canvas.create_text(self.cx, self.cy + r - 15, text="S Y L V I S", fill="#00aaaa", font=("Consolas", 8, "bold"))
        
        if step < total_steps:
            self.root.after(15, lambda: self.shrink_loop(step + 1, total_steps))
        else:
            self.root.geometry(f"{target_w}x{target_h}+{target_x}+{target_y}")
            self.canvas.config(width=target_w, height=target_h)
            self.cx = 75
            self.cy = 70
            self.state = "idle"
            self.animate()

    def animate(self):
        if self.state == "booting":
            self.draw_boot_animation()
            return
            
        self.tick += 1
        self.canvas.delete("all")
        
        # Select state-specific mascot image
        mascot_img = self._widget_mascot_photos.get(self.state) or self._widget_mascot_photo
        
        # Low resource mode: simplified rendering
        if self.low_resource:
            self._animate_low_resource()
            return
        
        # Draw futuristic HUD backgrounds
        # Corner brackets
        self.canvas.create_line(15, 15, 30, 15, fill="#002b36", width=1)
        self.canvas.create_line(15, 15, 15, 30, fill="#002b36", width=1)
        self.canvas.create_line(135, 15, 120, 15, fill="#002b36", width=1)
        self.canvas.create_line(135, 15, 135, 30, fill="#002b36", width=1)
        self.canvas.create_line(15, 135, 30, 135, fill="#002b36", width=1)
        self.canvas.create_line(15, 135, 15, 120, fill="#002b36", width=1)
        self.canvas.create_line(135, 135, 120, 135, fill="#002b36", width=1)
        self.canvas.create_line(135, 135, 135, 120, fill="#002b36", width=1)

        # Concentric tech grids
        self.canvas.create_oval(self.cx-62, self.cy-62, self.cx+62, self.cy+62, outline="#001620", width=1)
        self.canvas.create_oval(self.cx-45, self.cy-45, self.cx+45, self.cy+45, outline="#001c24", width=1, dash=(2, 8))
        
        # Dynamic HUD state text badge
        state_labels = {
            "idle": "SYS.ONLINE",
            "listening": "REC.AUDIO",
            "processing": "COMP.COGNITIVE",
            "speaking": "SYS.TRANSMIT"
        }
        state_colors = {
            "idle": "#00e5ff",
            "listening": "#39ff14",
            "processing": "#e040fb",
            "speaking": "#ff1493"
        }
        badge_text = state_labels.get(self.state, "SYS.ACTIVE")
        badge_color = state_colors.get(self.state, "#00e5ff")
        
        self.canvas.create_text(self.cx, self.cy - 48, text=badge_text, fill=badge_color, font=("Courier New", 7, "bold"))
        
        # Spawn ambient particles periodically
        if self.tick % 6 == 0:
            colors = {"idle": "#005f6f", "listening": "#1b5e0a", "processing": "#4a1570", "speaking": "#7a0a3a"}
            self._spawn_particle(colors.get(self.state, "#003040"))
        
        # Draw particles behind the core
        self._update_particles()
        
        # Draw Reactor Core Animations
        if self.state == "idle":
            # Breathing cyan core with layered rings
            breath = math.sin(self.tick * 0.06)
            r = 32 + 5 * breath
            
            # Outermost faint halo
            rh = 48 + 3 * math.sin(self.tick * 0.04)
            self.canvas.create_oval(self.cx-rh, self.cy-rh, self.cx+rh, self.cy+rh, outline="#003a3a", width=1, dash=(3, 6))
            
            # Outer ring
            self.canvas.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r, outline="#007a8a", width=2)
            
            # Inner glow ring
            ri = 22 + 2 * breath
            self.canvas.create_oval(self.cx-ri, self.cy-ri, self.cx+ri, self.cy+ri, outline="#00cccc", width=1)
            
            # Central core with gradient effect
            if mascot_img:
                self.canvas.create_image(self.cx, self.cy, image=mascot_img)
                self.canvas.create_oval(self.cx-20, self.cy-20, self.cx+20, self.cy+20, outline="#00ffff", width=1)
            else:
                self.canvas.create_oval(self.cx-16, self.cy-16, self.cx+16, self.cy+16, fill="#00e5ff", outline="#00ffff", width=1)
                self.canvas.create_oval(self.cx-8, self.cy-8, self.cx+8, self.cy+8, fill="#b3ffff", outline="")
            
            # Rotating ticks (6 instead of 4)
            ang = self.tick * 0.025
            for i in range(6):
                a = ang + i * (math.pi / 3)
                x1 = self.cx + (r + 6) * math.cos(a)
                y1 = self.cy + (r + 6) * math.sin(a)
                x2 = self.cx + (r + 13) * math.cos(a)
                y2 = self.cy + (r + 13) * math.sin(a)
                self.canvas.create_line(x1, y1, x2, y2, fill="#00ffff", width=2)
                
        elif self.state == "listening":
            # Rapid neon green pulse with double ring
            pulse = abs(math.sin(self.tick * 0.18))
            r = 25 + 20 * pulse
            
            # Outer dashed scanner ring
            r3 = r + 14
            self.canvas.create_oval(self.cx-r3, self.cy-r3, self.cx+r3, self.cy+r3, outline="#0d5e0a", width=1, dash=(2, 4))
            
            # Primary pulse ring
            self.canvas.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r, outline="#39ff14", width=3)
            
            # Inner glow ring
            r2 = r * 0.6
            self.canvas.create_oval(self.cx-r2, self.cy-r2, self.cx+r2, self.cy+r2, outline="#76ff44", width=1)
            
            # Central core
            if mascot_img:
                self.canvas.create_image(self.cx, self.cy, image=mascot_img)
                self.canvas.create_oval(self.cx-20, self.cy-20, self.cx+20, self.cy+20, outline="#39ff14", width=1)
            else:
                self.canvas.create_oval(self.cx-13, self.cy-13, self.cx+13, self.cy+13, fill="#39ff14", outline="")
                self.canvas.create_oval(self.cx-6, self.cy-6, self.cx+6, self.cy+6, fill="#b8ffb0", outline="")
            
            # Mic wave bars
            for i in range(5):
                bh = 6 + 10 * math.sin(self.tick * 0.25 + i * 0.8)
                bx = self.cx - 20 + i * 10
                self.canvas.create_line(bx, self.cy + 38, bx, self.cy + 38 - bh, fill="#39ff14", width=2)
            
        elif self.state == "processing":
            # Violet rotating segments with triple-layer spinners
            ang = self.tick * 6
            
            # Outermost slow counter-rotate
            self.canvas.create_arc(self.cx-50, self.cy-50, self.cx+50, self.cy+50, start=-ang*0.8, extent=60, style="arc", outline="#4a0080", width=1)
            self.canvas.create_arc(self.cx-50, self.cy-50, self.cx+50, self.cy+50, start=-ang*0.8+120, extent=60, style="arc", outline="#4a0080", width=1)
            self.canvas.create_arc(self.cx-50, self.cy-50, self.cx+50, self.cy+50, start=-ang*0.8+240, extent=60, style="arc", outline="#4a0080", width=1)
            
            # Middle ring
            self.canvas.create_arc(self.cx-38, self.cy-38, self.cx+38, self.cy+38, start=ang, extent=80, style="arc", outline="#da70d6", width=3)
            self.canvas.create_arc(self.cx-38, self.cy-38, self.cx+38, self.cy+38, start=ang+180, extent=80, style="arc", outline="#da70d6", width=3)
            
            # Inner fast ring
            self.canvas.create_arc(self.cx-26, self.cy-26, self.cx+26, self.cy+26, start=-ang*1.5, extent=50, style="arc", outline="#e040fb", width=2)
            self.canvas.create_arc(self.cx-26, self.cy-26, self.cx+26, self.cy+26, start=-ang*1.5+180, extent=50, style="arc", outline="#e040fb", width=2)
            
            # Central core
            if mascot_img:
                self.canvas.create_image(self.cx, self.cy, image=mascot_img)
                self.canvas.create_oval(self.cx-20, self.cy-20, self.cx+20, self.cy+20, outline="#e040fb", width=1)
            else:
                self.canvas.create_oval(self.cx-15, self.cy-15, self.cx+15, self.cy+15, fill="#9c27b0", outline="#e040fb", width=1)
                self.canvas.create_oval(self.cx-7, self.cy-7, self.cx+7, self.cy+7, fill="#e8b4f8", outline="")
            
        elif self.state == "speaking":
            # Pink ripples with layered waves
            # Outer ripple 1
            r1 = 15 + (self.tick % 30) * 1.5
            # Outer ripple 2 (offset)
            r2 = 15 + ((self.tick + 15) % 30) * 1.5
            # Outer ripple 3
            r3 = 15 + ((self.tick + 8) % 30) * 1.5
            
            self.canvas.create_oval(self.cx-r3, self.cy-r3, self.cx+r3, self.cy+r3, outline="#80003a", width=1)
            self.canvas.create_oval(self.cx-r1, self.cy-r1, self.cx+r1, self.cy+r1, outline="#ff69b4", width=2)
            self.canvas.create_oval(self.cx-r2, self.cy-r2, self.cx+r2, self.cy+r2, outline="#ff1493", width=2)
            
            # Central core
            if mascot_img:
                self.canvas.create_image(self.cx, self.cy, image=mascot_img)
                self.canvas.create_oval(self.cx-20, self.cy-20, self.cx+20, self.cy+20, outline="#ff1493", width=1)
            else:
                self.canvas.create_oval(self.cx-15, self.cy-15, self.cx+15, self.cy+15, fill="#ff1493", outline="#ff69b4", width=1)
                self.canvas.create_oval(self.cx-7, self.cy-7, self.cx+7, self.cy+7, fill="#ffb6da", outline="")
        
        # Draw "SYLVIS" label below the orb
        label_y = self.cy + 56
        self.canvas.create_text(self.cx, label_y, text="S Y L V I S", fill="#00aaaa", font=("Consolas", 8, "bold"))
            
        self.root.after(30, self.animate)

    def set_state(self, state):
        self.state = state


class SylvisConsole:
    def __init__(self, parent_root):
        self.root = tk.Toplevel(parent_root)
        self.root.title("S.Y.L.V.I.S. — Command Terminal")
        self.root.geometry("480x660")
        self.root.overrideredirect(True) # Remove standard windows borders
        self.root.configure(bg="#00e5ff") # Glowing neon border background
        self.root.withdraw()  # Hidden by default
        
        # Inner main body container
        main_container = tk.Frame(self.root, bg="#0a0a0f", borderwidth=0)
        main_container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # === Premium Header with Mascot ===
        header = tk.Frame(main_container, bg="#07070b", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        self._mascot_photo = None
        
        title_frame = tk.Frame(header, bg="#07070b")
        title_frame.pack(side="left", fill="y", padx=4)
        
        lbl_name = tk.Label(title_frame, text="S.Y.L.V.I.S.", font=("Consolas", 13, "bold"), fg="#00e5ff", bg="#07070b")
        lbl_name.pack(anchor="w", pady=(10, 0))
        
        lbl_sub = tk.Label(title_frame, text="Synthetic Yielding Linguistic Virtual Intelligence System", font=("Segoe UI", 7), fg="#555577", bg="#07070b")
        lbl_sub.pack(anchor="w")
        
        # Close button in header
        btn_close_header = tk.Button(header, text="✕", font=("Consolas", 12, "bold"), bg="#07070b", fg="#666688",
                                      activebackground="#2a0000", activeforeground="#ff4444", borderwidth=0,
                                      command=self.root.withdraw, cursor="hand2")
        btn_close_header.pack(side="right", padx=10, pady=10)
        
        # Drag bindings for custom header
        header.bind("<Button-1>", self.start_drag)
        header.bind("<B1-Motion>", self.drag)
        lbl_name.bind("<Button-1>", self.start_drag)
        lbl_name.bind("<B1-Motion>", self.drag)
        lbl_sub.bind("<Button-1>", self.start_drag)
        lbl_sub.bind("<B1-Motion>", self.drag)
        
        # Neon separator
        sep = tk.Frame(main_container, bg="#00e5ff", height=1)
        sep.pack(fill="x")
        sep2 = tk.Frame(main_container, bg="#002233", height=1)
        sep2.pack(fill="x")
        
        self.diag_canvas = tk.Canvas(main_container, bg="#0a0a0f", height=36, highlightthickness=0)
        self.diag_canvas.pack(fill="x", padx=8, pady=(4, 2))
        
        self.console_tick = 0
        self.last_cpu = 0
        self.last_ram = 0
        self.last_brain = "CLAUDE"
        self.last_voice = "SAPI5"
        
        self.update_diagnostics()
        self.update_console_animation()
        self.log_area = scrolledtext.ScrolledText(main_container, font=("Consolas", 10), bg="#09090d", fg="#d4d4dc",
                                                   insertbackground="#00e5ff", highlightthickness=0, borderwidth=0,
                                                   padx=8, pady=6, wrap="word")
        self.log_area.pack(fill="both", expand=True, padx=8, pady=(4, 3))
        
        # Message colors tags config
        self.log_area.tag_config("user_tag", foreground="#00e5ff", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("user_text", foreground="#e2e8f0", font=("Consolas", 10))
        
        self.log_area.tag_config("sylvis_tag", foreground="#ff007f", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("sylvis_text", foreground="#fdf2f8", font=("Consolas", 10))
        
        self.log_area.tag_config("system_tag", foreground="#8a8a93", font=("Consolas", 9, "bold"))
        self.log_area.tag_config("system_text", foreground="#71717a", font=("Consolas", 9))
        
        self.log_area.tag_config("error_tag", foreground="#ef4444", font=("Consolas", 9, "bold"))
        self.log_area.tag_config("error_text", foreground="#fca5a5", font=("Consolas", 9))
        
        # Status bar with neon accent
        status_frame = tk.Frame(main_container, bg="#0a0a0f")
        status_frame.pack(fill="x", padx=10, pady=(0, 2))
        
        self.status_dot = tk.Label(status_frame, text="●", font=("Consolas", 8), fg="#00ff88", bg="#0a0a0f")
        self.status_dot.pack(side="left")
        
        self.status_bar = tk.Label(status_frame, text="Ready", font=("Consolas", 9), fg="#00ff88", bg="#0a0a0f", anchor="w")
        self.status_bar.pack(side="left", padx=(4, 0))
        
        # Control Buttons Row
        ctrl_frame = tk.Frame(main_container, bg="#0a0a0f")
        ctrl_frame.pack(fill="x", padx=10, pady=2)
        
        self.auto_approve_var = tk.BooleanVar(value=app_settings.get("auto_approve", False))
        chk_approve = tk.Checkbutton(
            ctrl_frame, text="Auto-Approve", variable=self.auto_approve_var,
            onvalue=True, offvalue=False, command=self.on_toggle_approve,
            bg="#0a0a0f", fg="#888899", selectcolor="#07070b", activebackground="#0a0a0f", activeforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        chk_approve.pack(side="left")
        
        btn_config = tk.Button(ctrl_frame, text="⚙ API KEY", font=("Consolas", 9, "bold"), bg="#13131e", fg="#00e5ff",
                                activebackground="#252530", activeforeground="#00ffff", borderwidth=0, command=self.open_admin,
                                cursor="hand2", padx=8)
        btn_config.pack(side="right", padx=3)
        
        btn_settings = tk.Button(ctrl_frame, text="SETTINGS", font=("Consolas", 9, "bold"), bg="#13131e", fg="#a0a0b0",
                                  activebackground="#252530", activeforeground="#ffffff", borderwidth=0, command=self.open_settings,
                                  cursor="hand2", padx=8)
        btn_settings.pack(side="right", padx=3)
        
        btn_manual = tk.Button(ctrl_frame, text="❓ MANUAL", font=("Consolas", 9, "bold"), bg="#13131e", fg="#ff9900",
                               activebackground="#252530", activeforeground="#ffcc00", borderwidth=0, command=self.open_manual,
                               cursor="hand2", padx=8)
        btn_manual.pack(side="right", padx=3)
        
        # Input Section
        input_frame = tk.Frame(main_container, bg="#0a0a0f")
        input_frame.pack(fill="x", padx=10, pady=(4, 6))
        
        self.entry = tk.Entry(input_frame, font=("Segoe UI", 11), bg="#13131e", fg="#ffffff", insertbackground="#00e5ff",
                               borderwidth=0, relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))
        self.entry.bind("<Return>", lambda e: self.send_text())
        
        btn_talk = tk.Button(input_frame, text="🎤", font=("Segoe UI", 12), bg="#0a3f4e", fg="#00e5ff",
                              activebackground="#0e5f75", activeforeground="#ffffff", borderwidth=0, command=start_voice_recording,
                              cursor="hand2", padx=6)
        btn_talk.pack(side="right", padx=(0, 3))
        
        btn_send = tk.Button(input_frame, text="SEND ▶", font=("Consolas", 10, "bold"), bg="#1a0033", fg="#ff007f",
                              activebackground="#2d0059", activeforeground="#ffffff", borderwidth=0, command=self.send_text,
                              cursor="hand2", padx=10)
        btn_send.pack(side="right", padx=3)
        
        # Footer branding
        footer = tk.Label(main_container, text="Powered by SYLVIS  ·  Scroll Lock = Voice  ·  Double-click orb = Console",
                           font=("Segoe UI", 7), fg="#444455", bg="#0a0a0f")
        footer.pack(fill="x", padx=10, pady=(0, 6))
        
        self.log("[SYS] S.Y.L.V.I.S. core console initialized.", "system")
        self.log("[SYS] Right-click orb for menu. Double-click orb to toggle this console.", "system")
        
    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y
        
    def drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        
    def redraw_diagnostics(self, cpu_val, ram_val, brain_name, tts_short):
        self.diag_canvas.delete("all")
        
        # Cyber brackets in the corners of the diagnostics canvas
        w = 460
        h = 36
        
        # Draw tech background telemetry grids
        for gx in range(10, w, 35):
            self.diag_canvas.create_line(gx, 0, gx, h, fill="#040b12", dash=(2, 6))
            
        # Draw oscilloscope scrolling background sine wave
        points = []
        for x in range(15, 280, 5):
            # Complex combination wave for retro telemetry oscilloscope effect
            y = 18 + 6 * math.sin(x * 0.07 + self.console_tick * 0.18) * math.cos(x * 0.02 + self.console_tick * 0.05)
            points.append((x, y))
        if len(points) > 1:
            self.diag_canvas.create_line(points, fill="#003548", width=1)
            
        # Cyber corner brackets
        bracket_len = 8
        # Top-Left
        self.diag_canvas.create_line(4, 4, 4+bracket_len, 4, fill="#00e5ff", width=1)
        self.diag_canvas.create_line(4, 4, 4, 4+bracket_len, fill="#00e5ff", width=1)
        # Top-Right
        self.diag_canvas.create_line(w-4, 4, w-4-bracket_len, 4, fill="#00e5ff", width=1)
        self.diag_canvas.create_line(w-4, 4, w-4, 4+bracket_len, fill="#00e5ff", width=1)
        # Bottom-Left
        self.diag_canvas.create_line(4, h-4, 4+bracket_len, h-4, fill="#00e5ff", width=1)
        self.diag_canvas.create_line(4, h-4, 4, h-4-bracket_len, fill="#00e5ff", width=1)
        # Bottom-Right
        self.diag_canvas.create_line(w-4, h-4, w-4-bracket_len, h-4, fill="#00e5ff", width=1)
        self.diag_canvas.create_line(w-4, h-4, w-4, h-4-bracket_len, fill="#00e5ff", width=1)
        
        # CPU Load Bar
        # Title
        self.diag_canvas.create_text(15, 18, text="CPU", fill="#00e5ff", font=("Consolas", 8, "bold"), anchor="w")
        # Bar track
        self.diag_canvas.create_rectangle(42, 13, 112, 21, outline="#002b3d", fill="#070c12", width=1)
        # Bar fill
        cpu_w = int(70 * (cpu_val / 100.0))
        if cpu_w > 0:
            self.diag_canvas.create_rectangle(43, 14, 43+cpu_w-1, 20, fill="#00e5ff", outline="")
        # Value text
        self.diag_canvas.create_text(118, 18, text=f"{int(cpu_val)}%", fill="#00e5ff", font=("Consolas", 8), anchor="w")
        
        # RAM Load Bar
        # Title
        self.diag_canvas.create_text(155, 18, text="RAM", fill="#ff007f", font=("Consolas", 8, "bold"), anchor="w")
        # Bar track
        self.diag_canvas.create_rectangle(182, 13, 252, 21, outline="#3d001e", fill="#12070c", width=1)
        # Bar fill
        ram_w = int(70 * (ram_val / 100.0))
        if ram_w > 0:
            self.diag_canvas.create_rectangle(183, 14, 183+ram_w-1, 20, fill="#ff007f", outline="")
        # Value text
        self.diag_canvas.create_text(258, 18, text=f"{int(ram_val)}%", fill="#ff007f", font=("Consolas", 8), anchor="w")
        
        # Brain Badge
        self.diag_canvas.create_rectangle(292, 9, 368, 25, outline="#9c27b0", fill="#170c1e", width=1)
        self.diag_canvas.create_text(330, 17, text=f"🧠 {brain_name}", fill="#e040fb", font=("Consolas", 8, "bold"), anchor="center")
        
        # Voice Badge
        self.diag_canvas.create_rectangle(376, 9, 448, 25, outline="#00ff88", fill="#071e12", width=1)
        self.diag_canvas.create_text(412, 17, text=f"🔊 {tts_short}", fill="#00ff88", font=("Consolas", 8, "bold"), anchor="center")

    def update_diagnostics(self):
        try:
            self.last_cpu = psutil.cpu_percent()
            self.last_ram = psutil.virtual_memory().percent
            
            # Active Brain
            provider = app_settings.get("ai_provider", "Free Claude Server")
            self.last_brain = "CLAUDE" if "Claude" in provider else "LOCAL"
            
            # Active Voice
            tts = app_settings.get("tts_provider", "Offline (SAPI5)")
            self.last_voice = "SAPI5"
            if "ElevenLabs" in tts:
                self.last_voice = "ELEVEN"
            elif "Typecast" in tts:
                self.last_voice = "TYPECAST"
        except Exception as e:
            print(f"[WARN] diagnostics update failed: {e}")
        self.root.after(2000, self.update_diagnostics)

    def update_console_animation(self):
        self.console_tick += 1
        self.redraw_diagnostics(self.last_cpu, self.last_ram, self.last_brain, self.last_voice)
        self.root.after(80, self.update_console_animation)

    def log(self, text, tag="system"):
        self.log_area.config(state="normal")
        if text.startswith("[User] "):
            content = text[7:]
            self.log_area.insert("end", "[ USER ] ", "user_tag")
            self.log_area.insert("end", content + "\n", "user_text")
        elif text.startswith("[Sylvis] "):
            content = text[9:]
            self.log_area.insert("end", "[ SYLVIS ] ", "sylvis_tag")
            self.log_area.insert("end", content + "\n", "sylvis_text")
        elif text.startswith("[SYS] "):
            content = text[6:]
            self.log_area.insert("end", "┌ SYSTEM ┐ ", "system_tag")
            self.log_area.insert("end", content + "\n", "system_text")
        elif text.startswith("[ERROR] "):
            content = text[8:]
            self.log_area.insert("end", "❌ ERROR ", "error_tag")
            self.log_area.insert("end", content + "\n", "error_text")
        elif text.startswith("[RESULT] "):
            content = text[9:]
            self.log_area.insert("end", "⚡ RESULT ", "system_tag")
            self.log_area.insert("end", content + "\n", "system_text")
        else:
            self.log_area.insert("end", text + "\n", tag)
            
        self.log_area.see("end")
        self.log_area.config(state="disabled")
        
    def send_text(self):
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, "end")
        self.log(f"[User] {txt}", "user")
        
        # Run agent query in background thread
        threading.Thread(target=agent_chat_thread, args=(txt,), daemon=True).start()
        
    def on_toggle_approve(self):
        app_settings["auto_approve"] = self.auto_approve_var.get()
        save_settings(app_settings)
        self.log(f"[SYS] Auto-Approve set to: {app_settings['auto_approve']}", "system")
        
    def open_admin(self):
        webbrowser.open("http://localhost:8082/admin")
        
    def open_settings(self):
        SylvisSettingsWindow(self.root)
        
    def open_manual(self):
        manual_path = get_resource_path("manual.html")
        if os.path.exists(manual_path):
            webbrowser.open(f"file:///{os.path.abspath(manual_path)}")
        else:
            messagebox.showinfo("User Manual", "Manual file not found locally.")
        
class SylvisSettingsWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Sylvis Settings")
        self.win.geometry("400x320")
        self.win.overrideredirect(True) # Remove border window decoration
        self.win.configure(bg="#ff007f") # Outer glowing pink border
        self.win.grab_set()  # Modal
        
        # Main inner container
        main_container = tk.Frame(self.win, bg="#0d0d10", borderwidth=0)
        main_container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # === Premium Header ===
        header = tk.Frame(main_container, bg="#111118", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        self._mascot_photo = None
                
        lbl_name = tk.Label(header, text="S.Y.L.V.I.S. CONFIGURATION", font=("Consolas", 10, "bold"), fg="#ff007f", bg="#111118")
        lbl_name.pack(side="left", padx=5, pady=12)
        
        # Close button in header
        btn_close = tk.Button(header, text="✕", font=("Consolas", 12, "bold"), bg="#111118", fg="#555566",
                              activebackground="#2a0000", activeforeground="#ff4444", borderwidth=0,
                              command=self.win.destroy, cursor="hand2")
        btn_close.pack(side="right", padx=10, pady=10)
        
        # Drag bindings
        header.bind("<Button-1>", self.start_drag)
        header.bind("<B1-Motion>", self.drag)
        lbl_name.bind("<Button-1>", self.start_drag)
        lbl_name.bind("<B1-Motion>", self.drag)
        
        # Neon separator
        sep = tk.Frame(main_container, bg="#ff007f", height=1)
        sep.pack(fill="x")
        sep2 = tk.Frame(main_container, bg="#440022", height=1)
        sep2.pack(fill="x")
        
        # Combobox dark styling
        style = ttk.Style(self.win)
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground="#1a1a24", background="#1a1a24", foreground="#ffffff", arrowcolor="#00ffff", bordercolor="#003344", lightcolor="#003344", darkcolor="#003344")
        style.map("TCombobox", fieldbackground=[('readonly', '#1a1a24')], foreground=[('readonly', '#ffffff')])
        
        # AI Brain selection
        tk.Label(main_container, text="🧠 ACTIVE AI BRAIN", font=("Consolas", 9, "bold"), fg="#00ffff", bg="#0d0d10").pack(anchor="w", padx=20, pady=(15, 2))
        self.ai_var = tk.StringVar(value=app_settings.get("ai_provider", "Free Claude Server"))
        self.cmb_ai = ttk.Combobox(main_container, textvariable=self.ai_var, state="readonly", values=["Free Claude Server", "Local Offline AI"])
        self.cmb_ai.pack(fill="x", padx=20, pady=5)
        
        # Divider
        self.div1 = tk.Frame(main_container, bg="#1a1a24", height=1)
        self.div1.pack(fill="x", padx=20, pady=8)
        
        # TTS Provider selection
        tk.Label(main_container, text="🗣️ ACTIVE TTS PROVIDER", font=("Consolas", 9, "bold"), fg="#00ffff", bg="#0d0d10").pack(anchor="w", padx=20, pady=(4, 2))
        
        self.provider_var = tk.StringVar(value=app_settings.get("tts_provider", "Offline (SAPI5)"))
        self.cmb_provider = ttk.Combobox(main_container, textvariable=self.provider_var, state="readonly", values=["Offline (SAPI5)", "ElevenLabs", "Typecast"])
        self.cmb_provider.pack(fill="x", padx=20, pady=5)
        self.cmb_provider.bind("<<ComboboxSelected>>", self.toggle_frames)
        
        # Divider
        self.div2 = tk.Frame(main_container, bg="#1a1a24", height=1)
        self.div2.pack(fill="x", padx=20, pady=8)
        
        # ElevenLabs Frame
        self.el_frame = tk.Frame(main_container, bg="#0d0d10")
        tk.Label(self.el_frame, text="ELEVENLABS API KEY", font=("Consolas", 8, "bold"), fg="#888899", bg="#0d0d10").pack(anchor="w", pady=(5, 1))
        self.el_key = tk.Entry(self.el_frame, show="*", bg="#1a1a24", fg="#ffffff", insertbackground="#00ffff", borderwidth=0, relief="flat")
        self.el_key.insert(0, app_settings.get("elevenlabs_key", ""))
        self.el_key.pack(fill="x", ipady=4)
        
        tk.Label(self.el_frame, text="VOICE ID", font=("Consolas", 8, "bold"), fg="#888899", bg="#0d0d10").pack(anchor="w", pady=(5, 1))
        self.el_voice = tk.Entry(self.el_frame, bg="#1a1a24", fg="#ffffff", insertbackground="#00ffff", borderwidth=0, relief="flat")
        self.el_voice.insert(0, app_settings.get("elevenlabs_voice_id", ""))
        self.el_voice.pack(fill="x", ipady=4)
        
        tk.Label(self.el_frame, text="MODEL ID (Optional)", font=("Consolas", 8, "bold"), fg="#888899", bg="#0d0d10").pack(anchor="w", pady=(5, 1))
        self.el_model = tk.Entry(self.el_frame, bg="#1a1a24", fg="#ffffff", insertbackground="#00ffff", borderwidth=0, relief="flat")
        self.el_model.insert(0, app_settings.get("elevenlabs_model_id", "eleven_multilingual_v2"))
        self.el_model.pack(fill="x", ipady=4)
        
        # Typecast Frame
        self.tc_frame = tk.Frame(main_container, bg="#0d0d10")
        tk.Label(self.tc_frame, text="TYPECAST API KEY", font=("Consolas", 8, "bold"), fg="#888899", bg="#0d0d10").pack(anchor="w", pady=(5, 1))
        self.tc_key = tk.Entry(self.tc_frame, show="*", bg="#1a1a24", fg="#ffffff", insertbackground="#00ffff", borderwidth=0, relief="flat")
        self.tc_key.insert(0, app_settings.get("typecast_key", ""))
        self.tc_key.pack(fill="x", ipady=4)
        
        tk.Label(self.tc_frame, text="VOICE ID", font=("Consolas", 8, "bold"), fg="#888899", bg="#0d0d10").pack(anchor="w", pady=(5, 1))
        self.tc_voice = tk.Entry(self.tc_frame, bg="#1a1a24", fg="#ffffff", insertbackground="#00ffff", borderwidth=0, relief="flat")
        self.tc_voice.insert(0, app_settings.get("typecast_voice_id", ""))
        self.tc_voice.pack(fill="x", ipady=4)
        
        # Action Buttons
        self.btn_frame = tk.Frame(main_container, bg="#0d0d10")
        self.btn_frame.pack(fill="x", padx=20, pady=15)
        
        btn_save = tk.Button(self.btn_frame, text="✓ SAVE CHANGES", font=("Consolas", 9, "bold"), bg="#1e1b4b", fg="#00ffff",
                             activebackground="#312e81", activeforeground="#ffffff", borderwidth=0, command=self.save, cursor="hand2")
        btn_save.pack(side="right", padx=5, ipady=5, ipadx=10)
        
        btn_cancel = tk.Button(self.btn_frame, text="✕ CANCEL", font=("Consolas", 9, "bold"), bg="#27272a", fg="#ffffff",
                               activebackground="#3f3f46", activeforeground="#ffffff", borderwidth=0, command=self.win.destroy, cursor="hand2")
        btn_cancel.pack(side="right", ipady=5, ipadx=10)
        
        self.toggle_frames(None)
        
    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y
        
    def drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        x = self.win.winfo_x() + dx
        y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")
        
    def toggle_frames(self, event):
        provider = self.provider_var.get()
        if provider == "ElevenLabs":
            self.el_frame.pack(fill="x", padx=20, pady=5)
            self.tc_frame.pack_forget()
            self.win.geometry("400x530")
        elif provider == "Typecast":
            self.tc_frame.pack(fill="x", padx=20, pady=5)
            self.el_frame.pack_forget()
            self.win.geometry("400x440")
        else:
            self.el_frame.pack_forget()
            self.tc_frame.pack_forget()
            self.win.geometry("400x310")
            
    def save(self):
        app_settings["ai_provider"] = self.ai_var.get()
        app_settings["tts_provider"] = self.provider_var.get()
        app_settings["elevenlabs_key"] = self.el_key.get().strip()
        app_settings["elevenlabs_voice_id"] = self.el_voice.get().strip()
        app_settings["elevenlabs_model_id"] = self.el_model.get().strip()
        app_settings["typecast_key"] = self.tc_key.get().strip()
        app_settings["typecast_voice_id"] = self.tc_voice.get().strip()
        save_settings(app_settings)
        self.win.destroy()


class SecureApprovalWindow:
    def __init__(self, parent, tool_id, name, input_args):
        self.win = tk.Toplevel(parent)
        self.win.title("⚠️ SECURITY PROTOCOL CLEARANCE REQUIRED")
        self.win.geometry("400x320")
        self.win.overrideredirect(True) # Remove title bar border decoration
        self.win.configure(bg="#ef4444") # Glowing red border
        self.win.wm_attributes("-topmost", True)
        self.win.grab_set()
        
        main_container = tk.Frame(self.win, bg="#1c1616", borderwidth=0)
        main_container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # === Custom Header ===
        header = tk.Frame(main_container, bg="#271818", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        lbl_head = tk.Label(header, text="⚠️ SECURITY CLEARANCE REQUIRED", font=("Consolas", 10, "bold"), fg="#f87171", bg="#271818")
        lbl_head.pack(side="left", padx=15, pady=10)
        
        # Drag bindings
        header.bind("<Button-1>", self.start_drag)
        header.bind("<B1-Motion>", self.drag)
        lbl_head.bind("<Button-1>", self.start_drag)
        lbl_head.bind("<B1-Motion>", self.drag)
        
        lbl_info = tk.Label(main_container, text=f"Sylvis wants to run tool: {name}", font=("Consolas", 9), fg="#e2e8f0", bg="#1c1616")
        lbl_info.pack(pady=4)
        
        # Input args display box
        txt_box = scrolledtext.ScrolledText(main_container, font=("Consolas", 9), bg="#110d0d", fg="#fca5a5", highlightthickness=0, borderwidth=0, height=8)
        txt_box.pack(fill="both", expand=True, padx=20, pady=8)
        txt_box.insert("end", json.dumps(input_args, indent=2))
        txt_box.config(state="disabled")
        
        # Action Buttons
        btn_frame = tk.Frame(main_container, bg="#1c1616")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        btn_approve = tk.Button(btn_frame, text="✓ APPROVE RUN", font=("Consolas", 10, "bold"), bg="#15803d", fg="#ffffff", borderwidth=0, command=self.approve)
        btn_approve.pack(side="right", padx=5, ipady=5, ipadx=10)
        
        btn_abort = tk.Button(btn_frame, text="✕ ABORT ACTION", font=("Consolas", 10, "bold"), bg="#b91c1c", fg="#ffffff", borderwidth=0, command=self.abort)
        btn_abort.pack(side="left", ipady=5, ipadx=10)
        
        # Handle close as abort
        self.win.protocol("WM_DELETE_WINDOW", self.abort)
        
    def start_drag(self, event):
        self.drag_x = event.x
        self.win_y = event.y # dummy / mapping variable name
        
    def drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.win_y
        x = self.win.winfo_x() + dx
        y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")
        
    def approve(self):
        approval_result["approved"] = True
        approval_event.set()
        self.win.destroy()
        
    def abort(self):
        approval_result["approved"] = False
        approval_event.set()
        self.win.destroy()


# Thread communication queue processor
def check_gui_queue():
    try:
        while True:
            msg = gui_queue.get_nowait()
            m_type = msg.get("type")
            
            if m_type == "state":
                widget.set_state(msg.get("state"))
            elif m_type == "status":
                console.status_bar.config(text=msg.get("text"))
            elif m_type == "log":
                console.log(msg.get("text"), msg.get("tag", "system"))
            elif m_type == "speak":
                speech_queue.put(msg.get("text"))
            elif m_type == "prompt_approval":
                SecureApprovalWindow(console.root, msg.get("tool_id"), msg.get("name"), msg.get("input"))
                
            gui_queue.task_done()
    except queue.Empty:
        pass
    root.after(80, check_gui_queue)

# Toggle console log window visibility
def toggle_console():
    if console.root.winfo_viewable():
        console.root.withdraw()
    else:
        # Position Console relative to Widget
        wx = widget.root.winfo_x()
        wy = widget.root.winfo_y()
        # Position console just to the left of the widget
        cx = max(10, wx - 470)
        cy = wy
        console.root.geometry(f"450x600+{cx}+{cy}")
        console.root.deiconify()
        console.root.focus_force()

# --- AUDIO CAPTURING SPEECH-TO-TEXT ---
def start_voice_recording():
    if widget.state != "idle":
         return
    threading.Thread(target=voice_recording_thread, daemon=True).start()

def voice_recording_thread():
    if not winmm:
        gui_queue.put({"type": "log", "text": "[SYS] winmm.dll missing. Can't record.", "tag": "error"})
        return
        
    gui_queue.put({"type": "state", "state": "listening"})
    gui_queue.put({"type": "log", "text": "[SYS] Recording voice...", "tag": "system"})
    
    wav_path = os.path.join(tempfile.gettempdir(), "sylvis_voice.wav")
    if os.path.exists(wav_path):
        try: os.remove(wav_path)
        except Exception: pass
        
    try:
        winmm.mciSendStringW("open new type waveaudio alias recsound", None, 0, 0)
        winmm.mciSendStringW("set recsound bitspersample 16 channels 1 samplespersec 16000", None, 0, 0)
        winmm.mciSendStringW("record recsound", None, 0, 0)
        
        # Countdown 4 seconds
        for i in range(4, 0, -1):
            gui_queue.put({"type": "status", "text": f"Listening ({i}s)..."})
            time.sleep(1)
            
        gui_queue.put({"type": "status", "text": "Processing voice..."})
        
        winmm.mciSendStringW("stop recsound", None, 0, 0)
        winmm.mciSendStringW(f'save recsound "{wav_path}"', None, 0, 0)
        winmm.mciSendStringW("close recsound", None, 0, 0)
        
        gui_queue.put({"type": "state", "state": "processing"})
        
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
            
        try:
            text = r.recognize_google(audio)
            gui_queue.put({"type": "log", "text": f"[User] {text}", "tag": "user"})
            # Run query loop
            threading.Thread(target=agent_chat_thread, args=(text,), daemon=True).start()
        except sr.UnknownValueError:
            gui_queue.put({"type": "log", "text": "[SYS] Could not understand voice speech.", "tag": "error"})
            gui_queue.put({"type": "state", "state": "idle"})
            gui_queue.put({"type": "status", "text": "Ready"})
            gui_queue.put({"type": "speak", "text": "Sorry, I couldn't hear you clearly."})
        except sr.RequestError as e:
            gui_queue.put({"type": "log", "text": f"[SYS] Speech recognition request failed: {e}", "tag": "error"})
            gui_queue.put({"type": "state", "state": "idle"})
            gui_queue.put({"type": "status", "text": "Ready"})
            gui_queue.put({"type": "speak", "text": "Vocal recognition service unavailable."})
            
    except Exception as e:
        gui_queue.put({"type": "log", "text": f"[SYS] Vocal recording failed: {e}", "tag": "error"})
        gui_queue.put({"type": "state", "state": "idle"})
        gui_queue.put({"type": "status", "text": "Ready"})


# System hotkey callback
def on_hotkey_pressed():
    # Execute recording start in main GUI thread
    if is_minimized_to_tray:
        root.after(10, restore_from_tray)
        root.after(150, start_voice_recording)
    else:
        root.after(10, start_voice_recording)


if __name__ == "__main__":
    # Initialize background servers & configuration
    start_fcc_server()
    
    # First-run browser trigger check
    first_run = app_settings.get("first_run", True)
    if first_run:
        app_settings["first_run"] = False
        save_settings(app_settings)
        
        # Wait briefly for fcc-server to bind, then open admin settings and user manual
        def launch_first_run_browser():
            time.sleep(3)
            # Open admin page
            webbrowser.open("http://localhost:8082/admin")
            # Open user manual page
            manual_path = get_resource_path("manual.html")
            if os.path.exists(manual_path):
                webbrowser.open(f"file:///{os.path.abspath(manual_path)}")
        threading.Thread(target=launch_first_run_browser, daemon=True).start()
        
    # Main Tkinter App Setup
    root = tk.Tk()
    # root.withdraw() # Do NOT hide primary root window to make the SylvisWidget visible
    
    widget = SylvisWidget(root)
    console = SylvisConsole(root)
    
    # Register hotkeys
    try:
        keyboard.add_hotkey('scroll lock', on_hotkey_pressed)
        keyboard.add_hotkey('pause', on_hotkey_pressed)
        print("[SYS] Registered global Scroll Lock / Pause hotkeys.")
    except Exception as e:
        print(f"[WARN] Failed to register global hotkeys: {e}")
        
    # Start checking queue
    root.after(100, check_gui_queue)
    
    # Main GUI loop
    try:
        root.mainloop()
    finally:
        # Exit cleanups
        speech_queue.put(None)
        stop_fcc_server()
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        sys.exit(0)
