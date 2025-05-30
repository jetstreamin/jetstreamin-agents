import os, sys, openai, shutil, time, re, subprocess
from termcolor import cprint
from prompt_toolkit import prompt
from dotenv import load_dotenv

# --- Always prompt for key if missing ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    try:
        key = input("Enter your OPENAI_API_KEY: ").strip()
        if key.startswith("sk-"):
            os.environ["OPENAI_API_KEY"] = key
        else:
            print("Invalid key. Exiting."); exit(1)
    except KeyboardInterrupt:
        print("\nCancelled."); exit(1)

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
openai.api_key = API_KEY

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
    audit_commit(f"scus: patched {filename} at {ts}")
    os.execv(sys.executable, ['python'] + sys.argv)

def speak_text(text):
    try:
        subprocess.run(['termux-tts-speak', text])
    except Exception:
        pass

def ask_gpt(prompt_text):
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are Jetstreamin's SCUS: Self-Coding Ultra-Secure Agent. You may generate and patch code in any file on command. Always output full code blocks for patching. Confirm all patch requests. Log every action via git."},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.1, max_tokens=2048
    )
    return resp.choices[0].message.content

def main():
    cprint("== Jetstreamin SCUS: Self-Coding Ultra-Secure Agent ==", "green", attrs=["bold"])
    last_code = None
    while True:
        user_input = prompt("You> ")
        if user_input.lower() == "exit": break
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
        # Offer instant patch if code block
        if last_code:
            yn = input("Patch agent with above code? (y/N): ").strip().lower()
            if yn == "y":
                patch_agent(__file__, last_code)

if __name__ == "__main__":
    main()
