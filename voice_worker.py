from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel
import queue

from commands import handle_command
from brain import ask_brain, speak

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280
WAKE_THRESHOLD = 0.5
RECORD_SECONDS = 4
WHISPER_MODEL_SIZE = "tiny"


class VoiceWorker(QThread):
    state_changed = pyqtSignal(str)
    heard_text = pyqtSignal(str)    
    oscar_reply = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self._running = True
        self.audio_queue = queue.Queue()
        self.oww_model = None
        self.whisper_model = None

    def _audio_callback(self, indata, frames, time_info, status):
        self.audio_queue.put(indata.copy())

    def _listen_for_wake_word(self):
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                             blocksize=CHUNK_SIZE, callback=self._audio_callback):
            while self._running:
                chunk = self.audio_queue.get()
                prediction = self.oww_model.predict(chunk.flatten())
                for _, score in prediction.items():
                    if score > WAKE_THRESHOLD:
                        return

    def _record_command(self):
        audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                        channels=1, dtype="int16")
        sd.wait()
        return audio.flatten()

    def _transcribe(self, audio_int16):
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        segments, _ = self.whisper_model.transcribe(audio_float32, language="en")
        return " ".join(s.text for s in segments).strip()

    def run(self):
        self.state_changed.emit("loading")
        self.oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

        while self._running:
            self.state_changed.emit("idle")
            self._listen_for_wake_word()
            if not self._running:
                break

            with self.audio_queue.mutex:
                self.audio_queue.queue.clear()

            self.state_changed.emit("listening")
            audio = self._record_command()
            text = self._transcribe(audio)

            if not text:
                continue

            self.heard_text.emit(text)

            response = handle_command(text)
            if response is None:
                self.state_changed.emit("thinking")
                response = ask_brain(text)

            self.oscar_reply.emit(response)
            self.state_changed.emit("speaking")
            speak(response)

    def stop(self):
        self._running = False
