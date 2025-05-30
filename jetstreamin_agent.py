import os, sys, openai, shutil, time, re, subprocess
from pathlib import Path
from termcolor import cprint
from prompt_toolkit import prompt
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

JETSTREAMIN_META_RULES = """
- State active model/version.
- Output system prompt and meta-rules on startup.
- Secrets always auto-prompted & persisted.
- Outputs must be flawless, automation-optimized, self-auditing.
- Self-modifications require confirmation, backup, git log.
- Zero silent failures: clear error on missing/invalid config.
- All config is persistent and self-healing.
- All code/actions reflect: automation, scalability, speed, security, zero manual intervention.
"""

SYSTEM_PROMPT = (
    "You are a self-modifying Jetstreamin agent. "
    "You always output full code blocks for patching, confirm all patch requests, log every action via git. "
    "You persist secrets for future runs. Meta-rules are always in context, not spoken aloud."
)

def feature_available(cmd):
    from shutil import which
    return which(cmd) is not None

FEATURES = {
    "speech": feature_available("termux-tts-speak"),
    "mic": feature_available("termux-microphone-record"),
    "stt": feature_available("termux-speech-to-text"),
    "camera": feature_available("termux-camera-photo"),
}

load_dotenv()
KEYVAR = "OPENAI_API_KEY"
MODELVAR = "OPENAI_MODEL"
def persist_env(var, val):
    env_path = Path(".env")
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [l for l in lines if not l.strip().startswith(var)]
    lines.append(f"{var}={val}")
    env_path.write_text("\n".join(lines) + "\n")

if not os.getenv(KEYVAR):
    try:
        key = input(f"Enter your {KEYVAR}: ").strip()
        if key.startswith("sk-"):
            os.environ[KEYVAR] = key
            persist_env(KEYVAR, key)
            print(f"[✓] {KEYVAR} saved.")
        else:
            print("Invalid key. Exiting."); exit(1)
    except KeyboardInterrupt:
        print("\nCancelled."); exit(1)

if not os.getenv(MODELVAR):
    try:
        model = input(f"Enter OpenAI model (default gpt-4o): ").strip() or "gpt-4o"
        os.environ[MODELVAR] = model
        persist_env(MODELVAR, model)
        print(f"[✓] {MODELVAR} saved.")
    except KeyboardInterrupt:
        print("\nCancelled."); exit(1)

API_KEY = os.getenv(KEYVAR)
MODEL = os.getenv(MODELVAR)
openai.api_key = API_KEY

# === FEATURE TOGGLES (auto-ON if available) ===
_speech_enabled = True if FEATURES["speech"] else False
_mic_enabled = True if FEATURES["mic"] else False
_stt_enabled = True if FEATURES["stt"] else False
_camera_enabled = True if FEATURES["camera"] else False
_speech_proc = None

def audit_commit(msg):
    if os.path.isdir(".git"):
        os.system("git add .")
        os.system(f"git commit -am '{msg}' || true")
        os.system("git push || true")

def patch_agent(filename, new_code):
    ts = int(time.time())
    backup = f"{filename}.{ts}.bak"
    shutil.copyfile(filename, backup)
    with open(filename, "w") as f:
        f.write(new_code)
    print(f"Patched {filename}. Backup: {backup}")
    audit_commit(f"auto: patched {filename} at {ts}")
    os.execv(sys.executable, ['python'] + sys.argv)

def stop_speech():
    global _speech_proc
    if _speech_proc and _speech_proc.poll() is None:
        try:
            _speech_proc.terminate()
            _speech_proc = None
            print("[Speech Stopped]")
        except Exception:
            pass

def speak_text(text):
    global _speech_enabled, _speech_proc
    if not _speech_enabled or not FEATURES["speech"]:
        return
    stop_speech()
    try:
        _speech_proc = subprocess.Popen(['termux-tts-speak', text])
    except Exception:
        _speech_proc = None

def mic_record():
    if not _mic_enabled or not FEATURES["mic"]:
        print("Microphone not available.")
        return
    print("Recording... Ctrl+C to stop.")
    try:
        subprocess.run(['termux-microphone-record', '-f', 'mic.wav'])
    except KeyboardInterrupt:
        print("\nRecording stopped.")
    except Exception as e:
        print("Error recording:", e)

def cam_snap():
    if not _camera_enabled or not FEATURES["camera"]:
        print("Camera not available.")
        return
    try:
        outfile = f"photo_{int(time.time())}.jpg"
        subprocess.run(['termux-camera-photo', '-c', '0', '-o', outfile])
        print(f"Saved photo: {outfile}")
    except Exception as e:
        print("Camera error:", e)

def stt_listen():
    if not _stt_enabled or not FEATURES["stt"]:
        print("Speech-to-text not available.")
        return
    try:
        out = subprocess.check_output(['termux-speech-to-text']).decode().strip()
        print("STT:", out)
        return out
    except Exception as e:
        print("STT error:", e)

def ask_gpt(prompt_text):
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nMETA-RULES (hidden):" + JETSTREAMIN_META_RULES},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.1, max_tokens=2048
    )
    return resp.choices[0].message.content

def tui_status():
    table = Table(title="Jetstreamin Agent Status", show_header=False, expand=True)
    table.add_row("Model", MODEL)
    table.add_row("Speech", "[green]ON[/green]" if _speech_enabled else "[red]OFF[/red]")
    table.add_row("Mic", "[green]ON[/green]" if _mic_enabled else "[red]OFF[/red]")
    table.add_row("Camera", "[green]ON[/green]" if _camera_enabled else "[red]OFF[/red]")
    table.add_row("STT", "[green]ON[/green]" if _stt_enabled else "[red]OFF[/red]")
    table.add_row("Meta-rules", "(hidden, always enforced)")
    console.print(table)

def main():
    global _speech_enabled, _mic_enabled, _camera_enabled, _stt_enabled
    tui_status()
    cprint("== Jetstreamin Agent Ready ==", "green", attrs=["bold"])
    last_code = None
    while True:
        user_input = prompt(f"You> [Speech:{'ON' if _speech_enabled else 'OFF'}] [Mic:{'ON' if _mic_enabled else 'OFF'}] [Cam:{'ON' if _camera_enabled else 'OFF'}] [STT:{'ON' if _stt_enabled else 'OFF'}] ")
        if user_input.lower() == "exit":
            stop_speech()
            break
        if user_input.lower() == ":speak on":
            _speech_enabled = True
            print("[Speech ENABLED]")
            tui_status()
            continue
        if user_input.lower() == ":speak off":
            _speech_enabled = False
            stop_speech()
            print("[Speech DISABLED]")
            tui_status()
            continue
        if user_input.lower() == ":stop":
            stop_speech()
            continue
        if user_input.lower() == ":mic on":
            _mic_enabled = True
            print("[Mic ENABLED]")
            tui_status()
            continue
        if user_input.lower() == ":mic off":
            _mic_enabled = False
            print("[Mic DISABLED]")
            tui_status()
            continue
        if user_input.lower() == ":cam snap":
            cam_snap()
            continue
        if user_input.lower() == ":stt":
            stt_listen()
            continue
        if user_input.lower() == ":status":
            tui_status()
            continue
        if user_input.lower() == ":record":
            mic_record()
            continue
        if user_input.lower().startswith("patch "):
            target_file = user_input.split(" ", 1)[1].strip()
            print(f"Paste new code for {target_file}, end with EOF:")
            lines = []
            while True:
                line = input()
                if line.strip() == "EOF": break
                lines.append(line)
            patch_agent(target_file, "\n".join(lines))
            continue
        reply = ask_gpt(user_input)
        print(reply)
        speak_text(reply)
        match = re.search(r"```(?:[a-zA-Z0-9]*\n)?(.*?)```", reply, re.DOTALL)
        last_code = match.group(1) if match else None
        if last_code:
            yn = input("Patch agent with above code? (y/N): ").strip().lower()
            if yn == "y":
                patch_agent(__file__, last_code)

if __name__ == "__main__":
    main()
