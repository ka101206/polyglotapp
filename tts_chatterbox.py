"""
Chatterbox TTS Engine – voice-cloning wrapper for Italian (and other languages).

Uses chatterbox.tts.ChatterboxTTS with reference audio clips located in
the ``reference_voices/`` directory.  The model is lazily loaded on first
call and the heavy work is offloaded to a background thread so that the
async interface never blocks the event loop.
"""

import io
import os
import struct
import asyncio
import logging
import threading

import torch
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VOICES_DIR = os.path.join(_BASE_DIR, "reference_voices")

# Reference clips per gender (add more languages by extending these maps)
_VOICE_MAP = {
    "female": os.path.join(_VOICES_DIR, "it_female.wav"),
    "male":   os.path.join(_VOICES_DIR, "it_male.wav"),
}


class ChatterboxTTSEngine:
    """Async-friendly, thread-safe wrapper around ChatterboxTTS."""

    # ------------------------------------------------------------------
    # Construction & lazy initialisation
    # ------------------------------------------------------------------
    def __init__(self):
        self._model = None
        self._lock = threading.Lock()
        self._device: str | None = None
        # Kick off background model load so it's warm by first request.
        threading.Thread(target=self._init_model, daemon=True).start()

    def _init_model(self):
        """Download (if needed) and load the Chatterbox model.

        Thread-safe: uses a reentrant-safe double-check pattern so that
        concurrent callers don't duplicate work.
        """
        if self._model is not None:
            return self._model

        with self._lock:
            # Double-check after acquiring lock
            if self._model is not None:
                return self._model

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(
                "Loading ChatterboxTTS model on %s …", self._device,
            )
            try:
                from chatterbox.tts import ChatterboxTTS

                self._model = ChatterboxTTS.from_pretrained(
                    device=self._device,
                )
                logger.info(
                    "✅ ChatterboxTTS loaded (device=%s, sr=%s)",
                    self._device,
                    self._model.sr,
                )
                return self._model
            except Exception:
                logger.exception("❌ Failed to load ChatterboxTTS")
                return None

    # ------------------------------------------------------------------
    # WAV helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _samples_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
        """Convert a mono float32 numpy array to 16-bit WAV bytes.

        Parameters
        ----------
        samples : np.ndarray
            1-D float32 array with values in [-1.0, 1.0].
        sample_rate : int
            Samples per second (e.g. 24 000).

        Returns
        -------
        bytes
            Complete WAV file content (RIFF header + PCM data), mono,
            16-bit, suitable for web playback.
        """
        # Clip & quantise to int16
        pcm = np.clip(samples, -1.0, 1.0)
        pcm = (pcm * 32767).astype(np.int16)
        raw = pcm.tobytes()

        # Build a minimal WAV (RIFF) header manually so we have zero
        # dependency on the ``wave`` module at runtime.
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)
        data_size = len(raw)
        riff_size = 36 + data_size  # 36 = size of header minus 8

        header = struct.pack(
            "<4sI4s"        # RIFF chunk descriptor
            "4sIHHIIHH"     # fmt sub-chunk
            "4sI",          # data sub-chunk header
            b"RIFF", riff_size, b"WAVE",
            b"fmt ", 16, 1, num_channels,
            sample_rate, byte_rate, block_align, bits_per_sample,
            b"data", data_size,
        )
        return header + raw

    @staticmethod
    def _torch_to_numpy(tensor: torch.Tensor) -> np.ndarray:
        """Squeeze a Chatterbox output tensor to a 1-D float32 numpy array."""
        # model.generate() returns shape (1, N) or (N,)
        wav = tensor.detach().cpu()
        if wav.dim() > 1:
            wav = wav.squeeze(0)
        return wav.numpy().astype(np.float32)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def generate_audio(
        self,
        text: str,
        speed: float = 1.0,
        gender: str = "female",
    ) -> bytes | None:
        """Synthesise *text* and return complete WAV file bytes.

        Parameters
        ----------
        text : str
            The text to speak (typically Italian, but the model is
            multilingual).
        speed : float, optional
            Playback speed multiplier (default ``1.0``).
        gender : {"female", "male"}
            Selects the reference voice clip for voice cloning.

        Returns
        -------
        bytes or None
            WAV bytes (mono, 16-bit PCM) on success, ``None`` on failure.
        """
        model = self._init_model()
        if model is None:
            logger.error("ChatterboxTTS model is not available.")
            return None

        clean = text.strip()
        if not clean:
            return None

        # Resolve the reference audio clip for the requested gender.
        ref_path = _VOICE_MAP.get(gender)
        if ref_path is None or not os.path.isfile(ref_path):
            logger.warning(
                "Reference voice '%s' not found at %s – "
                "falling back to default female voice.",
                gender,
                ref_path,
            )
            ref_path = _VOICE_MAP.get("female")
            if ref_path is None or not os.path.isfile(ref_path):
                logger.error(
                    "No reference voice files found in %s. "
                    "Please add it_female.wav / it_male.wav.",
                    _VOICES_DIR,
                )
                return None

        sample_rate: int = model.sr

        try:
            # model.generate() is CPU/GPU-bound – offload to a thread.
            wav_tensor: torch.Tensor = await asyncio.to_thread(
                model.generate,
                clean,
                audio_prompt_path=ref_path,
            )

            samples = self._torch_to_numpy(wav_tensor)

            # ----- optional speed adjustment -----
            if speed != 1.0 and speed > 0:
                try:
                    import torchaudio.functional as F

                    # Resample to simulate speed change (pitch-preserving
                    # would require a vocoder; simple resample is fine for
                    # small deltas).
                    orig_sr = sample_rate
                    new_sr = int(sample_rate * speed)
                    t = torch.from_numpy(samples).unsqueeze(0)
                    t = F.resample(t, orig_sr, new_sr)
                    samples = t.squeeze(0).numpy().astype(np.float32)
                except ImportError:
                    logger.warning(
                        "torchaudio not available – ignoring speed parameter."
                    )

            return self._samples_to_wav(samples, sample_rate)

        except Exception:
            logger.exception("ChatterboxTTS generation failed for: %s", clean)
            return None

    async def generate_audio_stream(
        self,
        text: str,
        speed: float = 1.0,
        gender: str = "female",
    ):
        """Async generator that yields WAV bytes.

        Chatterbox produces the entire utterance in one shot, so this
        yields a single chunk.  The generator interface keeps the API
        consistent with streaming TTS engines (e.g. Kokoro).
        """
        wav_bytes = await self.generate_audio(text, speed=speed, gender=gender)
        if wav_bytes:
            yield wav_bytes
