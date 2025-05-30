import os, openai, tempfile, subprocess, re
from termcolor import cprint
from prompt_toolkit import prompt
from dotenv import load_dotenv; load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
openai.api_key = API_KEY or ""
def speak_text(text):
    try: subprocess.run(['termux-tts-speak', text])
    except: pass
def ask_gpt(prompt_text):
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are Jetstreamin's voice coding agent. Output executable code. No explanations unless asked. All responses also spoken out loud. Auto-update and self-repair as needed."},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.1, max_tokens=2048
    )
    return resp.choices[0].message.content
def run_code(code):
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as f:
        f.write(code); fname = f.name
    cprint(f"[RUNNING]: {fname}", "cyan")
    os.chmod(fname, 0o755)
    out = subprocess.getoutput(f"bash {fname}")
    print(out); os.unlink(fname)
def check_update():
    if os.path.exists(".git"): os.system("git pull || true")
def auto_commit_push(msg):
    if os.path.exists(".git"):
        os.system("git add .")
        os.system(f"git commit -am '{msg}' || true")
        os.system("git push || true")
def main():
    cprint("== Jetstreamin GPT-4.1 AUTO AGENT ==", "green", attrs=["bold"])
    last_code = None
    check_update()
    while True:
        user_input = prompt("You> ")
        if user_input.lower() == "exit": break
        if user_input.lower() == "run" and last_code: run_code(last_code); continue
        reply = ask_gpt(user_input)
        print(reply)
        speak_text(reply)
        match = re.search(r"```(?:[a-zA-Z0-9]*\n)?(.*?)```", reply, re.DOTALL)
        last_code = match.group(1) if match else None
        auto_commit_push(f"auto: {user_input[:40]}")
if __name__ == "__main__": main()
