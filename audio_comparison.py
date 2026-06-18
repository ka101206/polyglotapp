import numpy as np
import librosa
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
import io
import soundfile as sf

def compare_audio(user_audio_np, user_sr, tts_wav_bytes):
    """
    Compares the user's audio (numpy array) with the TTS audio (WAV bytes)
    using Dynamic Time Warping (DTW) on their MFCCs.
    Returns a score between 0 and 100.
    """
    try:
        # Convert user audio to float32 if it's not already
        if user_audio_np.dtype != np.float32:
            user_audio = user_audio_np.astype(np.float32)
            # If it was 16-bit PCM, normalize it
            if np.max(np.abs(user_audio)) > 1.0:
                user_audio = user_audio / 32768.0
        else:
            user_audio = user_audio_np

        # Ensure consistent sample rate for comparison (16000 Hz is standard)
        target_sr = 16000
        
        # Resample user audio if necessary
        if user_sr != target_sr:
            user_audio = librosa.resample(user_audio, orig_sr=user_sr, target_sr=target_sr)
            
        # Load TTS audio
        tts_audio, tts_sr = sf.read(io.BytesIO(tts_wav_bytes))
        
        # Convert TTS to mono if stereo
        if tts_audio.ndim > 1:
            tts_audio = np.mean(tts_audio, axis=1)
            
        # Resample TTS audio if necessary
        if tts_sr != target_sr:
            tts_audio = librosa.resample(tts_audio, orig_sr=tts_sr, target_sr=target_sr)

        # Trim silence from both audios
        user_audio, _ = librosa.effects.trim(user_audio, top_db=20)
        tts_audio, _ = librosa.effects.trim(tts_audio, top_db=20)

        # Extract MFCC features
        # We use standard 13 MFCCs
        mfcc_user = librosa.feature.mfcc(y=user_audio, sr=target_sr, n_mfcc=13)
        mfcc_tts = librosa.feature.mfcc(y=tts_audio, sr=target_sr, n_mfcc=13)

        # Transpose for DTW (it expects shape: seq_len x features)
        mfcc_user = mfcc_user.T
        mfcc_tts = mfcc_tts.T

        # Calculate DTW distance
        distance, path = fastdtw(mfcc_user, mfcc_tts, dist=euclidean)
        
        # Normalize the distance by the length of the alignment path
        # A typical normalized distance for identical audios is 0. 
        # For completely different it can be 100-200.
        normalized_distance = distance / len(path)
        
        # Map distance to a 0-100 score
        # These thresholds might need tuning, but typically:
        # Distance < 30 is excellent (90-100)
        # Distance > 90 is poor (50-60)
        # Let's use an exponential decay or linear mapping
        score = max(0, min(100, 100 - (normalized_distance - 20) * 1.5))
        
        return int(score)
        
    except Exception as e:
        print(f"Error comparing audio: {e}")
        return 80 # Fallback score
