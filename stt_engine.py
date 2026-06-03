import speech_recognition as sr
import numpy as np
import io
import wave

class STTEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000
        self.last_audio = None

    def transcribe_audio(self, audio_bytes, target_language="en-US"):
        # audio_bytes is expected to be a valid WAV format from the frontend
        try:
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = self.recognizer.record(source)
                
            # Save the raw numpy array for pronunciation analysis
            # We assume 16kHz mono 16-bit PCM for analysis
            raw_data = audio.get_raw_data()
            self.last_audio = np.frombuffer(raw_data, dtype=np.int16)
            self.sample_rate = audio.sample_rate

            text = self.recognizer.recognize_google(audio, language=target_language)
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return f"ERROR: Could not request results; {e}"
        except Exception as e:
            return f"ERROR: {str(e)}"