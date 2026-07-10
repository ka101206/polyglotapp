"""Lightweight speech metrics for the Fluency statistic.

Derives two speaker-independent-ish signals from a user's recorded utterance:

  * confidence — vocal assertiveness: loudness adequacy + steadiness of the voice
  * flow       — fluidity: how choppy the delivery is (long hesitation pauses,
                 overall silence ratio)

It also locates where those signals drop and maps the drop to the nearest word
(by proportional timing against the transcript, since the STT gives no word
timestamps). Any single attribution is approximate, but aggregated into the
weak_points counters over many turns it becomes reliable.

All computation is a couple of librosa RMS passes over a few seconds of audio —
cheap enough to run inline on the transcription request.
"""
import numpy as np
import librosa

_TARGET_SR = 16000


def _tokens(transcript: str, language: str):
    """Split the transcript into 'words' for drop attribution.

    CJK languages aren't space-delimited, so we fall back to per-character
    (i.e. per-sound) tokens there.
    """
    if not transcript:
        return []
    if language in ("Japanese", "Chinese", "Korean"):
        return [c for c in transcript if not c.isspace()]
    return [w for w in transcript.split() if w.strip()]


def analyze_speech(user_audio_np, sr, transcript: str = "", language: str = "Japanese") -> dict:
    """Return {confidence, flow, drops:[{type, word, score}]} — all 0/empty on failure."""
    empty = {"confidence": 0, "flow": 0, "drops": []}
    try:
        audio = np.asarray(user_audio_np).astype(np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if np.max(np.abs(audio)) > 1.0:  # 16-bit PCM -> [-1, 1]
            audio = audio / 32768.0

        if sr != _TARGET_SR:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=_TARGET_SR)
        sr = _TARGET_SR

        audio, _ = librosa.effects.trim(audio, top_db=25)
        if audio.size < sr * 0.2:  # < 0.2s of speech — not enough to judge
            return empty

        hop = 512
        rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=hop)[0]
        if rms.size == 0:
            return empty
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
        total_dur = len(audio) / sr

        peak = float(np.max(rms))
        if peak <= 0:
            return empty
        thresh = max(peak * 0.15, 1e-4)
        speech = rms > thresh
        if not speech.any():
            return empty
        speech_ratio = float(np.mean(speech))

        n = len(speech)
        first = int(np.argmax(speech))
        last = n - 1 - int(np.argmax(speech[::-1]))

        # A "bit more forgiving" final curve: lifts middling scores without
        # letting genuinely poor delivery reach the top.
        def _forgive(v):
            return int(max(0, min(100, round(v * 1.08 + 8))))

        # --- Internal long pauses (hesitations between speech) ---
        # Only clearly hesitant pauses (>= 0.55s) count against flow.
        long_pauses = []
        i = first
        while i <= last:
            if not speech[i]:
                j = i
                while j <= last and not speech[j]:
                    j += 1
                pause_dur = float(times[min(j, n - 1)] - times[i])
                if pause_dur >= 0.55:
                    long_pauses.append((float(times[i]), pause_dur))
                i = j
            else:
                i += 1

        # --- Flow: penalize hesitation pauses and excessive silence (gently) ---
        flow = 100.0 - len(long_pauses) * 8.0 - max(0.0, 0.4 - speech_ratio) * 80.0
        flow = _forgive(max(0.0, min(100.0, flow)))

        # --- Confidence: loudness adequacy + steadiness of the voice ---
        voiced = rms[speech]
        mean_rms = float(np.mean(voiced))
        loud = min(1.0, mean_rms / 0.05)                       # easier to reach "loud enough"
        cv = float(np.std(voiced) / (mean_rms + 1e-6))         # wavering -> high
        steady = max(0.0, 1.0 - cv * 0.7)                      # soften the wavering penalty
        confidence = _forgive((0.55 * loud + 0.45 * steady) * 100)

        # --- Locate drops and map to the nearest word ---
        toks = _tokens(transcript, language)

        def word_at(t):
            if not toks or total_dur <= 0:
                return None
            idx = int((t / total_dur) * len(toks))
            return toks[max(0, min(len(toks) - 1, idx))]

        drops = []
        for (t, dur) in long_pauses:  # flow drops -> the word resumed after the pause
            w = word_at(min(t + dur, total_dur - 1e-3))
            if w:
                drops.append({"type": "flow", "word": w, "score": int(max(0, 60 - dur * 30))})

        low_thr = max(peak * 0.25, thresh)  # confidence drops -> quiet/trailing regions
        i = first
        while i <= last:
            if speech[i] and rms[i] < low_thr:
                j = i
                while j <= last and speech[j] and rms[j] < low_thr:
                    j += 1
                if float(times[min(j, n - 1)] - times[i]) >= 0.25:
                    w = word_at(float(times[i]))
                    if w:
                        drops.append({"type": "confidence", "word": w, "score": 50})
                i = j
            else:
                i += 1

        return {"confidence": confidence, "flow": flow, "drops": drops}
    except Exception as e:
        print(f"[audio_metrics] error: {e}")
        return empty
