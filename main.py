import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel
import queue
import time
from commands import handle_command
from brain import ask_brain, speak

SAMPLE_RATE = 16000   
CHUNK_SIZE = 1280         
WAKE_THRESHOLD = 0.5     
RECORD_SECONDS = 4       
WHISPER_MODEL_SIZE = "tiny" 

print("Loading wake word model (local, one-time load)...")
oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

print("Loading local speech-to-text model (this may take a moment the first time)...")

whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

audio_queue = queue.Queue()


def audio_callback(indata, frames, time_info, status):
 
    if status:
        print(status)
    audio_queue.put(indata.copy())


def listen_for_wake_word():
 
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

    print(f"Listening for your command ({RECORD_SECONDS}s)...")
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                    channels=1, dtype="int16")
    sd.wait()
    return audio.flatten()


def transcribe(audio_int16):


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
                print("OSCAR is thinking...")
                reply = ask_brain(text)
                print(f"OSCAR: {reply}")
                speak(reply)
        else:
            print("(didn't catch anything - try again)")

        time.sleep(0.5) 


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down O.S.C.A.R. Stage 1. Bye!")
