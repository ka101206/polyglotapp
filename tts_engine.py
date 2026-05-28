import os
import glob
import soundfile as sf
import threading
import platform 
import re 

if platform.system() == "Windows":
    import winsound
else:
    winsound = None 

from kokoro_onnx import Kokoro
from misaki import ja 

class TTSEngine:
    def __init__(self):
        self.engine = None
        self.ja_g2p = ja.JAG2P()
        self.lock = threading.Lock()
        self.current_ja_voice = "jf_alpha"

    def _init_engine(self):
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
            return self.engine
        except Exception as e:
            print(f"❌ TTS Init Error: {e}")
            return None

    def set_voice(self, ja_voice):
        self.current_ja_voice = ja_voice

    def speak(self, text, speed=1.0, is_japanese=True, on_start=None, on_done=None):
        threading.Thread(target=self._run_speak, args=(text, speed, on_start, on_done)).start()
        
    def _run_speak(self, text, speed, on_start, on_done):
        engine = self._init_engine()
        if not engine: return

        with self.lock:
            try:
                if on_start: on_start()
                
                # Split text strictly by Japanese punctuation
                chunks = re.split(r'(?<=[。！？])', text)

                for chunk in chunks:
                    clean_chunk = chunk.strip()
                    if not clean_chunk:
                        continue 
                        
                    print(f"🔊 Generating audio for chunk: {clean_chunk}")
                    
                    phonemes, _ = self.ja_g2p(clean_chunk)
                    # Use the dynamically passed speed here
                    samples, sample_rate = engine.create(
                        phonemes, voice=self.current_ja_voice, speed=speed, lang="j", is_phonemes=True
                    )

                    sf.write('temp_audio.wav', samples, sample_rate)

                    # Smart Playback: Check OS before playing
                    if platform.system() == "Windows":
                        winsound.PlaySound('temp_audio.wav', winsound.SND_FILENAME)
                    else:
                        os.system("afplay temp_audio.wav")

            except Exception as e:
                print(f"❌ Audio Error: {e}")
            finally:
                if on_done: on_done()
