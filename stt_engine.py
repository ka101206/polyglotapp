import speech_recognition as sr
import numpy as np
import io
import wave

class STTEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000
        self.last_audio = None

    def transcribe_audio(self, audio_bytes, target_language="ja-JP"):
        import subprocess
        # Convert webm to wav via ffmpeg
        try:
            process = subprocess.Popen(
                ['ffmpeg', '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            wav_bytes, err = process.communicate(input=audio_bytes)
            if process.returncode != 0:
                print(f"FFMPEG Error: {err.decode('utf-8')}")
                return "ERROR: Audio conversion failed.", 0.0
        except Exception as e:
            print(f"Subprocess Error: {e}")
            return f"ERROR: Subprocess {str(e)}", 0.0
            
        try:
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio = self.recognizer.record(source)
                
            # Save the raw numpy array for pronunciation analysis
            # We assume 16kHz mono 16-bit PCM for analysis
            raw_data = audio.get_raw_data()
            self.last_audio = np.frombuffer(raw_data, dtype=np.int16)
            self.sample_rate = audio.sample_rate

            response = self.recognizer.recognize_google(audio, language=target_language, show_all=True)
            if not response or not isinstance(response, dict) or 'alternative' not in response:
                return "", 0.0
                
            alternatives = response['alternative']
            if not alternatives:
                return "", 0.0
                
            best_alt = alternatives[0]
            text = best_alt.get('transcript', "")
            confidence = best_alt.get('confidence', 0.85)
            
            return text, confidence
        except sr.UnknownValueError:
            return "", 0.0
        except sr.RequestError as e:
            return f"ERROR: Could not request results; {e}", 0.0
        except Exception as e:
            return f"ERROR: {str(e)}", 0.0