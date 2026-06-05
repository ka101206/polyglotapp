import os
import io
import re
import wave
import asyncio
import threading

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from misaki import ja


class TTSEngine:
    def __init__(self):
        self.engine = None
        self.ja_g2p = ja.JAG2P()
        self.lock = threading.Lock()
        self.cache = {}
        self.current_ja_voice = "jf_alpha"
        self.stop_flag = threading.Event()
        threading.Thread(target=self._init_engine, daemon=True).start()

    def _init_engine(self):
        import glob
        with self.lock:
            if self.engine:
                return self.engine
            target_model = "kokoro-v1.0.onnx"
            if not os.path.exists(target_model):
                found = glob.glob("*.onnx")
                target_model = found[0] if found else None
            if not target_model:
                print("❌ TTS Error: No .onnx file found!")
                return None
            try:
                self.engine = Kokoro(target_model, "voices.bin")
                print("✅ Japanese TTS Engine (Kokoro) loaded successfully!")
                return self.engine
            except Exception as e:
                print(f"❌ TTS Init Error: {e}")
                return None

    def set_voice(self, ja_voice):
        self.current_ja_voice = ja_voice

    def stop(self):
        self.stop_flag.set()

    def reset(self):
        self.stop_flag.clear()

    @staticmethod
    def _samples_to_wav(samples, sample_rate) -> bytes:
        """Convert float32 numpy array to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((samples * 32767).astype(np.int16).tobytes())
        return buf.getvalue()

    async def generate_audio_stream(self, text, speed=1.0, language="Japanese"):
        """Yields WAV bytes for the given text. The caller should already have
        split text at sentence boundaries; this method treats text as a single chunk."""

        if language != "Japanese":
            import edge_tts
            voice_map = {
                "Spanish": "es-ES-AlvaroNeural",
                "French": "fr-FR-HenriNeural",
                "Italian": "it-IT-DiegoNeural",
                "Chinese": "zh-CN-YunxiNeural",
                "Korean": "ko-KR-InJoonNeural",
                "English": "en-US-GuyNeural",
            }
            voice = voice_map.get(language, "en-US-GuyNeural")
            rate_str = f"+{int((speed - 1.0) * 100)}%" if speed >= 1.0 else f"{int((speed - 1.0) * 100)}%"
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if self.stop_flag.is_set():
                    break
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            if audio_data:
                yield bytes(audio_data)
            return

        # --- Japanese / Kokoro ---
        engine = self._init_engine()
        if not engine:
            return

        clean = text.strip()
        if not clean:
            return

        cache_key = (clean, self.current_ja_voice, speed)
        if cache_key in self.cache:
            samples, sr = self.cache[cache_key]
        else:
            phonemes, _ = self.ja_g2p(clean)
            samples, sr = await asyncio.to_thread(
                engine.create, phonemes,
                voice=self.current_ja_voice, speed=speed, lang="ja", is_phonemes=True,
            )
            self.cache[cache_key] = (samples, sr)

        yield self._samples_to_wav(samples, sr)
