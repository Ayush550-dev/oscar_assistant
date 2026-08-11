import os
import asyncio
import tempfile
from google import genai
from google.genai import types
import edge_tts
import pygame

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
    if chat is None:
        return ("I can't think right now - the GEMINI_API_KEY environment "
                "variable isn't set. Check the setup steps in brain.py.")

    try:
        response = chat.send_message(text)
        return response.text
    except Exception as e:
        return f"I ran into an error trying to think: {e}"


def speak(text):
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

