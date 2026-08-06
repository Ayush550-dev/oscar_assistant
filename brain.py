"""
brain.py - the "thinking" part of O.S.C.A.R.

This is the ONLY piece that talks to the internet. It sends the short text
of what you said (never your files, screen, or raw audio) to Google's
Gemini API (free tier, no credit card needed), gets back a reply written
in a Jarvis/EDITH-style personality, and speaks it out loud using a free
local text-to-speech engine.

Setup needed:
1. Go to https://aistudio.google.com, sign in with a Google account
2. Click "Get API key" -> "Create API key" (no credit card required)
3. Set it as an environment variable called GEMINI_API_KEY
   (Windows: search "Environment Variables" in Start menu -> Edit the
   system environment variables -> Environment Variables -> New -> under
   "User variables" add Name: GEMINI_API_KEY, Value: your key)
4. Restart Command Prompt after setting it so it picks up the change
"""

import os
import asyncio
import tempfile
from google import genai
from google.genai import types
import edge_tts
import pygame

# ---------- PERSONALITY (edit this to change how OSCAR talks) ----------
SYSTEM_PROMPT = """You are O.S.C.A.R., a witty, calm, highly capable AI assistant
in the style of Jarvis or EDITH from the Marvel films. You help your user while
they work or code on their PC. Keep replies short and conversational (1-3
sentences) since they will be spoken out loud - never use lists, markdown,
or long explanations unless specifically asked for detail. You can be a
little dry and witty, but always genuinely helpful, quick, and clear."""

client = None
chat = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(
            model="gemini-3.5-flash",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
except Exception as e:
    print(f"Could not set up Gemini client: {e}")


def ask_brain(text):
    """Sends text to Gemini and returns a short spoken-style reply."""
    if chat is None:
        return ("I can't think right now - the GEMINI_API_KEY environment "
                "variable isn't set. Check the setup steps in brain.py.")

    try:
        response = chat.send_message(text)
        return response.text
    except Exception as e:
        return f"I ran into an error trying to think: {e}"


def speak(text):
    """Converts text to speech (edge-tts) and plays it out loud."""
    async def _generate():
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        await communicate.save(temp_path)
        return temp_path

    try:
        audio_path = asyncio.run(_generate())

        pygame.mixer.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()

        os.remove(audio_path)
    except Exception as e:
        print(f"(couldn't speak the reply out loud: {e})")

