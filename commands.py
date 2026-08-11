
APP_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "spotify": "spotify.exe",
    "vscode": "code.exe",
    "vs code": "code.exe",
    "visual studio code": "code.exe",
    "paint": "mspaint.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "task manager": "taskmgr.exe",
}

CLOSE_NAME_OVERRIDES = {
    "calc.exe": ["CalculatorApp.exe", "Calculator.exe", "calc.exe"],
}


def open_app(exe_name):
    try:
        subprocess.Popen(["start", "", exe_name], shell=True)
        return True
    except Exception as e:
        print(f"Error opening {exe_name}: {e}")
        return False


def close_app(exe_name):
    candidates = CLOSE_NAME_OVERRIDES.get(exe_name, [exe_name])
    for candidate in candidates:
        try:
            result = subprocess.run(["taskkill", "/F", "/IM", candidate],
                                     capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except Exception as e:
            print(f"Error closing {candidate}: {e}")
    return False


def find_app_in_text(text):
    text_lower = text.lower()
    for alias, exe in APP_MAP.items():
        if alias in text_lower:
            return alias, exe
    return None, None


def handle_command(text):

    Returns:
        A short response string if it handled the command,
        or None if it didn't recognize anything (so Stage 2's
        cloud brain can take over and try to answer instead).
    text_lower = text.lower()
    alias, exe = find_app_in_text(text)

    if alias is None:
        return None

    if any(word in text_lower for word in ["open", "launch", "start"]):
        if open_app(exe):
            return f"Opening {alias}"
        return f"Sorry, I couldn't open {alias}"

    if any(word in text_lower for word in ["close", "quit", "exit", "kill"]):
        if close_app(exe):
            return f"Closing {alias}"
        return f"Sorry, I couldn't close {alias}. Maybe it wasn't running."

    return None
