import numpy as np
import scipy.spatial.distance as dist
import scipy.signal as signal
from fastdtw import fastdtw
import parselmouth
import os
import subprocess

class PronunciationAnalyzer:
    def __init__(self):
        pass

    def convert_to_wav(self, file_path):
        """Ensure file is wav for parselmouth"""
        if file_path.endswith('.wav'): return file_path
        out_file = file_path.rsplit('.', 1)[0] + '_conv.wav'
        try:
            subprocess.run(["ffmpeg", "-y", "-i", file_path, out_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_file
        except:
            return file_path

    def generate_reference(self, text, language):
        import uuid, asyncio, edge_tts
        temp_file = f"temp_ref_{uuid.uuid4().hex}.wav"
        voices = {
            "Japanese": "ja-JP-NanamiNeural",
            "Chinese": "zh-CN-XiaoxiaoNeural",
            "Korean": "ko-KR-SunHiNeural",
            "Spanish": "es-ES-ElviraNeural",
            "French": "fr-FR-DeniseNeural",
            "Italian": "it-IT-ElsaNeural"
        }
        voice = voices.get(language, "en-US-AriaNeural")
        
        async def _gen():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_file)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_gen())
        loop.close()
        
        return self.convert_to_wav(temp_file)

    def analyze(self, user_audio_np, sample_rate, text, language):
        """
        Analyze user audio against reference audio.
        user_audio_np: numpy array of user speech (int16)
        """
        import soundfile as sf
        import uuid
        user_file = f"temp_user_{uuid.uuid4().hex}.wav"
        sf.write(user_file, user_audio_np, sample_rate)
        
        ref_file = self.generate_reference(text, language)
        
        try:
            user_snd = parselmouth.Sound(user_file)
            ref_snd = parselmouth.Sound(ref_file)
            
            # Extract Pitch (F0)
            user_pitch = user_snd.to_pitch()
            ref_pitch = ref_snd.to_pitch()
            
            user_f0 = user_pitch.selected_array['frequency']
            ref_f0 = ref_pitch.selected_array['frequency']
            
            # Clean 0s (unvoiced)
            user_f0[user_f0 == 0] = np.nan
            ref_f0[ref_f0 == 0] = np.nan
            
            # Interpolate NaNs for DTW
            def interpolate_f0(f0):
                nans = np.isnan(f0)
                if np.all(nans): return np.zeros_like(f0)
                x = lambda z: z.nonzero()[0]
                f0[nans] = np.interp(x(nans), x(~nans), f0[~nans])
                return f0
                
            user_f0 = interpolate_f0(user_f0)
            ref_f0 = interpolate_f0(ref_f0)
            
            # Normalize Pitch (z-score) to compare intonation regardless of absolute pitch
            def normalize(arr):
                std = np.std(arr)
                if std == 0: return arr
                return (arr - np.mean(arr)) / std
                
            norm_user = normalize(user_f0)
            norm_ref = normalize(ref_f0)
            
            # DTW Alignment
            distance, path = fastdtw(norm_user.reshape(-1, 1), norm_ref.reshape(-1, 1), dist=dist.euclidean)
            
            # Calculate pitch similarity score (0-100)
            # Max expected distance per frame is roughly 2.0 (since z-scores mostly range -2 to 2)
            max_dist = len(path) * 2.0
            pitch_score = max(0, min(100, 100 * (1 - (distance / max_dist))))
            
            # Intensity (Stress) Analysis
            user_intensity = user_snd.to_intensity().values[0]
            ref_intensity = ref_snd.to_intensity().values[0]
            
            dist_int, _ = fastdtw(normalize(user_intensity).reshape(-1, 1), normalize(ref_intensity).reshape(-1, 1), dist=dist.euclidean)
            intensity_score = max(0, min(100, 100 * (1 - (dist_int / (len(user_intensity) * 2.0)))))
            
            # Rhythm (Duration) Analysis
            user_dur = user_snd.get_total_duration()
            ref_dur = ref_snd.get_total_duration()
            rhythm_ratio = min(user_dur, ref_dur) / max(user_dur, ref_dur)
            rhythm_score = rhythm_ratio * 100
            
            # Overall Score
            overall_score = (pitch_score * 0.4) + (intensity_score * 0.3) + (rhythm_score * 0.3)
            
            feedback_data = {
                "text": text,
                "language": language,
                "pitch_score": round(pitch_score, 1),
                "stress_score": round(intensity_score, 1),
                "rhythm_score": round(rhythm_score, 1),
                "overall_score": round(overall_score, 1),
                "user_duration": round(user_dur, 2),
                "ref_duration": round(ref_dur, 2)
            }
            
            return feedback_data
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return None
        finally:
            if os.path.exists(user_file): os.remove(user_file)
            if 'ref_file' in locals() and os.path.exists(ref_file): os.remove(ref_file)
