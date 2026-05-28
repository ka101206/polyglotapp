# stt_engine.py
import sounddevice as sd
import speech_recognition as sr
import numpy as np
import io
import wave
import queue
import time

class STTEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000

    def get_rms(self, block):
        return np.sqrt(np.mean(np.square(block.astype(float))))

    def listen_and_transcribe(self, target_language, timeout=2.5, sensitivity=50.0, status_check=None):
        q = queue.Queue()

        def audio_callback(indata, frames, time_info, status):
            q.put(indata.copy())

        try:
            chunk_samples = int(self.sample_rate * 0.1)
            
            with sd.InputStream(samplerate=self.sample_rate, 
                                channels=1, 
                                dtype='int16', 
                                blocksize=chunk_samples,
                                callback=audio_callback):
                
                # Calibration (0.5 seconds of ambient room noise)
                calibration_chunks = []
                for _ in range(5):
                    calibration_chunks.append(q.get())
                ambient_rms = self.get_rms(np.concatenate(calibration_chunks))
                
                # Dynamic Thresholding
                sens_factor = max(0.01, 2.0 - (sensitivity / 50.0))
                threshold = max(ambient_rms * 1.5 * sens_factor, 150 * sens_factor)
                
                audio_data = []
                pre_speech_buffer = []
                silence_timer = 0.0
                has_spoken = False
                
                # THE MISSING LOOP: This keeps the mic open and processes audio
                while True:
                    # Kill switch if the user turns off conversation mode mid-listen
                    if status_check and not status_check():
                        return "ERROR: Cancelled"
                        
                    try:
                        chunk = q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                        
                    rms = self.get_rms(chunk)
                    
                    # If sound is louder than background noise (User is speaking)
                    if rms > threshold:
                        if not has_spoken:
                            has_spoken = True
                            # Keep 0.5s of audio from *before* the threshold was crossed so we don't clip the first letter
                            audio_data.extend(pre_speech_buffer)
                            
                        audio_data.append(chunk)
                        silence_timer = 0.0 # Reset silence timer while speaking
                        
                    # If sound is quiet (User is silent)
                    else:
                        if has_spoken:
                            audio_data.append(chunk)
                            silence_timer += 0.1 # chunk size is 0.1s
                            
                            # If we hit the timeout limit, break the loop and send to Google
                            if silence_timer >= timeout:
                                break
                        else:
                            # Maintain a rolling 0.5s buffer of background noise while waiting to speak
                            pre_speech_buffer.append(chunk)
                            if len(pre_speech_buffer) > 5:
                                pre_speech_buffer.pop(0)
            
            # Send the collected audio to speech recognition
            if not audio_data or not has_spoken:
                return "ERROR: No speech"
                
            recording = np.concatenate(audio_data, axis=0)
            byte_io = io.BytesIO()
            with wave.open(byte_io, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(recording.tobytes())
            
            byte_io.seek(0)
            with sr.AudioFile(byte_io) as source:
                audio = self.recognizer.record(source)
                try:
                    text = self.recognizer.recognize_google(audio, language=target_language)
                    if text and text.strip():
                        return text.strip()
                    return "ERROR: Empty result"
                except sr.UnknownValueError:
                    return "ERROR: Unrecognized"
                except sr.RequestError:
                    return "ERROR: API Unavailable"

        except Exception as e:
            return f"ERROR: {str(e)}"