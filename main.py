"""
O.S.C.A.R. - Stage 1
=====================
This is the first building block: a voice loop that runs ENTIRELY on your PC.

What it does:
1. Listens to your microphone continuously (very low CPU - wake word models are tiny)
2. Waits for you to say the wake word ("Hey Jarvis" for now - we'll swap this for
   a custom "Hey Oscar" model later, that requires a short training step)
3. Once triggered, records a few seconds of what you say next
4. Transcribes it to text using a local Whisper model (nothing leaves your PC)
5. Prints the text to the console

Nothing here uses the internet. This is the "always-on, always-local" foundation.
In Stage 2, we'll take the printed text and send ONLY that text to a cloud AI
to get a smart reply - your files, screen, and audio never leave your machine.

HOW TO RUN THIS (Windows, beginner steps):
1. Install Python from https://python.org (check "Add to PATH" during install)
2. Open Command Prompt in this folder
3. Run: pip install -r requirements.txt
4. Run: python main.py
5. Say "Hey Jarvis" then speak a sentence - watch it appear in the console
"""

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel
import queue
import time
from commands import handle_command
from brain import ask_brain, speak

# ---------- SETTINGS (tweak these later) ----------
SAMPLE_RATE = 16000          # required sample rate for the wake word + whisper models
CHUNK_SIZE = 1280            # ~80ms of audio per chunk - openWakeWord's expected size
WAKE_THRESHOLD = 0.5         # confidence needed to trigger (0.0-1.0, raise if false triggers happen)
RECORD_SECONDS = 4           # how long to record your command after the wake word
WHISPER_MODEL_SIZE = "tiny"  # tiny = fastest/lightest, good starting point for weaker CPUs

# ---------- SETUP ----------
print("Loading wake word model (local, one-time load)...")
oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")  # built-in pretrained model to start

print("Loading local speech-to-text model (this may take a moment the first time)...")
# compute_type="int8" keeps this light on CPU - important for your hardware
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

audio_queue = queue.Queue()


def audio_callback(indata, frames, time_info, status):
    """Called automatically by sounddevice whenever new mic audio is available."""
    if status:
        print(status)
    audio_queue.put(indata.copy())


def listen_for_wake_word():
    """Continuously listens until the wake word is detected."""
    print("\nListening for 'Hey Jarvis'... (Ctrl+C to quit)")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                         blocksize=CHUNK_SIZE, callback=audio_callback):
        while True:
            chunk = audio_queue.get()
            audio_int16 = chunk.flatten()
            prediction = oww_model.predict(audio_int16)

            for wake_word, score in prediction.items():
                if score > WAKE_THRESHOLD:
                    print(f"\nWake word detected! (confidence: {score:.2f})")
                    return


def record_command():
    """Records a few seconds of audio right after the wake word triggers."""
    print(f"Listening for your command ({RECORD_SECONDS}s)...")
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                    channels=1, dtype="int16")
    sd.wait()
    return audio.flatten()


def transcribe(audio_int16):
    """Converts recorded audio to text using the local Whisper model."""
    # Whisper expects float32 audio normalized between -1 and 1
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(audio_float32, language="en")
    text = " ".join(segment.text for segment in segments).strip()
    return text


def main():
    print("=" * 50)
    print("  O.S.C.A.R. - Stage 1 (local voice loop)")
    print("=" * 50)

    while True:
        listen_for_wake_word()
        # Drain any queued audio so we start the recording fresh
        with audio_queue.mutex:
            audio_queue.queue.clear()

        command_audio = record_command()
        text = transcribe(command_audio)

        if text:
            print(f"You said: \"{text}\"")

            response = handle_command(text)
            if response:
                print(f"OSCAR: {response}")
                speak(response)
            else:
                # No known app command matched - let the cloud brain think
                print("OSCAR is thinking...")
                reply = ask_brain(text)
                print(f"OSCAR: {reply}")
                speak(reply)
        else:
            print("(didn't catch anything - try again)")

        time.sleep(0.5)  # brief pause before listening for wake word again


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down O.S.C.A.R. Stage 1. Bye!")
