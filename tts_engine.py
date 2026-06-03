import os
import glob
import soundfile as sf
import threading
import re 

from kokoro_onnx import Kokoro
from misaki import ja 

class TTSEngine:
    def __init__(self, audio_player=None):
        self.engine = None
        self.ja_g2p = ja.JAG2P()
        self.lock = threading.Lock()
        self.cache = {}
        self.current_ja_voice = "jf_alpha"
        self.audio_player = audio_player  # callback: play_audio(filepath) -> blocks until done
        self.stop_flag = threading.Event()
        threading.Thread(target=self._init_engine, daemon=True).start()

    def _init_engine(self):
        with self.lock:
            if self.engine: return self.engine
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

    def generate_audio_stream(self, text, speed=1.0):
        engine = self._init_engine()
        if not engine: return

        # Split text strictly by Japanese punctuation
        chunks = re.split(r'(?<=[。！？])', text)

        for chunk in chunks:
            if self.stop_flag.is_set():
                print("🛑 TTS interrupted (Japanese)")
                break

            clean_chunk = chunk.strip()
            if not clean_chunk:
                continue 
                
            cache_key = (clean_chunk, self.current_ja_voice, speed)
            if cache_key in self.cache:
                samples, sample_rate = self.cache[cache_key]
            else:
                phonemes = self.ja_g2p(clean_chunk)
                samples, sample_rate = engine.create(
                    phonemes, voice=self.current_ja_voice, speed=speed, lang="ja"
                )
                self.cache[cache_key] = (samples, sample_rate)

            # Convert numpy array to WAV bytes
            import io, wave
            import numpy as np
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                # Convert float32 [-1, 1] to int16
                audio_int16 = (samples * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            yield wav_io.getvalue()
