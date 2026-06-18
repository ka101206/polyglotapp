"""
MeloTTS wrapper – Spanish (ES) and French (FR) female voices.

Provides an async ``generate_audio`` method that returns mono, 16-bit WAV
bytes suitable for web playback.  Each language gets its own ``melo.api.TTS``
instance, lazily initialised on first request and protected by a lock so
concurrent callers never create duplicate models.
"""

import io
import wave
import asyncio
import logging
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported languages and their default speaker keys
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {
    "ES": "ES",   # Spanish
    "FR": "FR",   # French
}


class MeloTTSEngine:
    """Async-friendly wrapper around ``melo.api.TTS`` for ES / FR."""

    def __init__(self, device: str = "cpu"):
        """
        Parameters
        ----------
        device : str
            PyTorch device string, e.g. ``"cpu"``, ``"cuda"``, ``"auto"``.
        """
        self._device = device
        # Per-language model cache: {"ES": TTS, "FR": TTS}
        self._models: dict = {}
        # One lock per language so loading ES doesn't block FR and vice versa
        self._locks: dict[str, threading.Lock] = {
            lang: threading.Lock() for lang in SUPPORTED_LANGUAGES
        }

    # ------------------------------------------------------------------
    # Lazy model loading (thread-safe, per-language)
    # ------------------------------------------------------------------

    def _get_model(self, language: str):
        """Return the ``TTS`` instance for *language*, creating it if needed.

        Uses double-checked locking: the fast path (model already loaded)
        avoids acquiring the lock entirely.
        """
        if language in self._models:
            return self._models[language]

        lock = self._locks.get(language)
        if lock is None:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Choose from {list(SUPPORTED_LANGUAGES)}"
            )

        with lock:
            # Re-check after acquiring the lock (another thread may have
            # finished loading while we were waiting).
            if language in self._models:
                return self._models[language]

            logger.info("Loading MeloTTS model for language=%s …", language)
            try:
                from melo.api import TTS  # heavy import – only when needed

                model = TTS(language=language, device=self._device)
                self._models[language] = model
                logger.info(
                    "✅ MeloTTS model for %s loaded successfully.", language
                )
                return model
            except Exception:
                logger.exception(
                    "❌ Failed to load MeloTTS model for %s", language
                )
                raise

    # ------------------------------------------------------------------
    # WAV helper
    # ------------------------------------------------------------------

    @staticmethod
    def _samples_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
        """Convert a float32 numpy array to mono, 16-bit PCM WAV bytes.

        Parameters
        ----------
        samples : np.ndarray
            1-D float32 audio waveform, values in [-1.0, 1.0].
        sample_rate : int
            Sampling rate in Hz (e.g. 44100).

        Returns
        -------
        bytes
            Complete WAV file content (header + PCM data).
        """
        # Ensure mono
        if samples.ndim > 1:
            samples = samples.mean(axis=-1)

        # Clip and convert to int16
        samples = np.clip(samples, -1.0, 1.0)
        pcm = (samples * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)          # mono
            wf.setsampwidth(2)          # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_audio(
        self,
        text: str,
        language: str,
        speed: float = 1.0,
    ) -> Optional[bytes]:
        """Synthesise *text* and return WAV bytes.

        Parameters
        ----------
        text : str
            The text to speak.
        language : str
            ``"ES"`` for Spanish or ``"FR"`` for French.
        speed : float, optional
            Playback speed multiplier (default ``1.0``).

        Returns
        -------
        bytes or None
            Mono 16-bit WAV data, or ``None`` if the input was empty.

        Raises
        ------
        ValueError
            If *language* is not supported.
        RuntimeError
            If the underlying model fails to synthesise.
        """
        language = language.upper()
        lang_map = {"SPANISH": "ES", "FRENCH": "FR", "ES": "ES", "FR": "FR"}
        language = lang_map.get(language, language)
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Choose from {list(SUPPORTED_LANGUAGES)}"
            )

        import re
        clean = re.sub(r'[,.]', ' ', text).strip()
        if not clean:
            logger.warning("generate_audio called with empty text.")
            return None

        # Load or retrieve the model (blocking I/O → offload to thread)
        model = await asyncio.to_thread(self._get_model, language)

        # Determine speaker id
        speaker_key = SUPPORTED_LANGUAGES[language]
        speaker_ids = model.hps.data.spk2id
        speaker_id = speaker_ids[speaker_key]

        # Sample rate from model config
        sample_rate: int = model.hps.data.sampling_rate

        # Synthesise in a thread so we don't block the event loop.
        # Passing output_path=None makes tts_to_file return a numpy array
        # instead of writing to disk.
        logger.info(
            "Generating audio: lang=%s, speed=%.2f, text=%.60s…",
            language,
            speed,
            clean,
        )

        audio_np: np.ndarray = await asyncio.to_thread(
            model.tts_to_file,
            clean,
            speaker_id,
            None,          # output_path=None → return numpy array
            speed,
        )

        if audio_np is None or len(audio_np) == 0:
            logger.error("MeloTTS returned empty audio for text: %s", clean)
            return None

        wav_bytes = self._samples_to_wav(audio_np, sample_rate)
        logger.info(
            "Audio generated: %d bytes, %.2fs @ %d Hz",
            len(wav_bytes),
            len(audio_np) / sample_rate,
            sample_rate,
        )
        return wav_bytes
