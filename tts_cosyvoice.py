"""
CosyVoice2 TTS wrapper for Chinese and Korean voices.

Uses zero-shot voice cloning via reference audio clips in `reference_voices/`.
Falls back to Edge TTS if CosyVoice2 is not installed.

Model: FunAudioLLM/CosyVoice2-0.5B (auto-downloaded from HuggingFace on first use)
"""

import os
import io
import sys
import wave
import asyncio
import logging
import threading
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Attempt to import CosyVoice2 dependencies.  The library is not pip-
# installable; it requires cloning the repo and adding its paths manually.
# If unavailable we fall back to Edge TTS at generation time.
# ---------------------------------------------------------------------------
_COSYVOICE_AVAILABLE = False
try:
    # CosyVoice2 expects Matcha-TTS on the path
    _project_root = Path(__file__).resolve().parent
    _matcha_path = str(_project_root / "third_party" / "Matcha-TTS")
    if _matcha_path not in sys.path:
        sys.path.insert(0, _matcha_path)

    from cosyvoice.cli.cosyvoice import CosyVoice2  # type: ignore
    from cosyvoice.utils.file_utils import load_wav  # type: ignore
    import torchaudio  # type: ignore

    _COSYVOICE_AVAILABLE = True
except ImportError:
    CosyVoice2 = None  # type: ignore
    load_wav = None     # type: ignore
    torchaudio = None   # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MODEL_ID = "FunAudioLLM/CosyVoice2-0.5B"
_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pretrained_models",
    "CosyVoice2-0.5B",
)
_REFERENCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_voices")

# Reference audio files + prompt text per (language, gender)
_VOICE_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("Chinese", "female"): {
        "ref_audio": os.path.join(_REFERENCE_DIR, "zh_female.wav"),
        "prompt_text": "你好，欢迎使用语音合成系统。",
    },
    ("Chinese", "male"): {
        "ref_audio": os.path.join(_REFERENCE_DIR, "zh_male.wav"),
        "prompt_text": "你好，欢迎使用语音合成系统。",
    },
    ("Korean", "female"): {
        "ref_audio": os.path.join(_REFERENCE_DIR, "ko_female.wav"),
        "prompt_text": "안녕하세요, 음성 합성 시스템에 오신 것을 환영합니다.",
    },
    ("Korean", "male"): {
        "ref_audio": os.path.join(_REFERENCE_DIR, "ko_male.wav"),
        "prompt_text": "안녕하세요, 음성 합성 시스템에 오신 것을 환영합니다.",
    },
}

# Edge TTS fallback voice mapping
_EDGE_VOICE_MAP: dict[tuple[str, str], str] = {
    ("Chinese", "female"): "zh-CN-XiaoxiaoNeural",
    ("Chinese", "male"):   "zh-CN-YunxiNeural",
    ("Korean", "female"):  "ko-KR-SunHiNeural",
    ("Korean", "male"):    "ko-KR-InJoonNeural",
}


class CosyVoiceTTS:
    """Async wrapper around CosyVoice2 for Chinese / Korean TTS.

    Thread-safe.  The model is lazily loaded on first use and downloaded
    from HuggingFace if not already present locally.
    """

    def __init__(self) -> None:
        self._model: "CosyVoice2 | None" = None  # type: ignore[name-defined]
        self._lock = threading.Lock()
        self._ref_cache: dict[str, object] = {}  # path -> loaded 16 kHz tensor
        self._init_started = False

        if not _COSYVOICE_AVAILABLE:
            logger.warning(
                "CosyVoice2 is not installed. "
                "Chinese/Korean TTS will fall back to Edge TTS.  "
                "To enable CosyVoice2, clone the repo and add it to sys.path."
            )

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------
    def _ensure_model(self) -> "CosyVoice2 | None":  # type: ignore[name-defined]
        """Download (if needed) and load CosyVoice2.  Thread-safe."""
        if self._model is not None:
            return self._model

        with self._lock:
            # Double-checked locking
            if self._model is not None:
                return self._model

            if not _COSYVOICE_AVAILABLE:
                return None

            model_path = _MODEL_DIR

            # Auto-download from HuggingFace when the local dir is missing
            if not os.path.isdir(model_path):
                logger.info("Downloading CosyVoice2 model from HuggingFace (%s) …", _MODEL_ID)
                try:
                    from modelscope import snapshot_download  # type: ignore
                    model_path = snapshot_download(
                        _MODEL_ID,
                        local_dir=_MODEL_DIR,
                    )
                    logger.info("Model downloaded to %s", model_path)
                except ImportError:
                    try:
                        from huggingface_hub import snapshot_download  # type: ignore
                        model_path = snapshot_download(
                            repo_id=_MODEL_ID,
                            local_dir=_MODEL_DIR,
                        )
                        logger.info("Model downloaded to %s", model_path)
                    except ImportError:
                        logger.error(
                            "Neither modelscope nor huggingface_hub is installed. "
                            "Cannot auto-download the model."
                        )
                        return None
                except Exception as exc:
                    logger.error("Failed to download CosyVoice2 model: %s", exc)
                    return None

            try:
                self._model = CosyVoice2(
                    model_path,
                    load_jit=False,
                    load_trt=False,
                    fp16=False,
                )
                logger.info("✅ CosyVoice2 model loaded successfully!")
                return self._model
            except Exception as exc:
                logger.error("Failed to load CosyVoice2 model: %s", exc)
                return None

    # ------------------------------------------------------------------
    # Reference audio helpers
    # ------------------------------------------------------------------
    def _load_reference(self, path: str):
        """Load a reference WAV at 16 kHz.  Cached after first load."""
        if path in self._ref_cache:
            return self._ref_cache[path]

        if not os.path.isfile(path):
            raise FileNotFoundError(f"Reference audio not found: {path}")

        ref = load_wav(path, 16000)
        self._ref_cache[path] = ref
        return ref

    # ------------------------------------------------------------------
    # WAV encoding
    # ------------------------------------------------------------------
    @staticmethod
    def _samples_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
        """Convert a float32 numpy array (or torch tensor) to mono 16-bit WAV bytes."""
        # Handle torch tensors transparently
        if hasattr(samples, "cpu"):
            samples = samples.cpu().numpy()

        # Ensure 1-D (mono)
        if samples.ndim > 1:
            samples = samples.squeeze()

        # Normalise into int16 range
        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes((samples * 32767).astype(np.int16).tobytes())
        return buf.getvalue()

    @staticmethod
    def _torch_tensor_to_wav(tensor, sample_rate: int) -> bytes:
        """Convert a torch tensor (from CosyVoice2 output) to mono 16-bit WAV bytes."""
        buf = io.BytesIO()
        # torchaudio expects (channels, samples); ensure shape
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)
        # Normalise
        peak = tensor.abs().max()
        if peak > 0:
            tensor = tensor / peak
        # Convert to int16 via numpy for the wave module
        samples_np = (tensor.squeeze().cpu().numpy() * 32767).astype(np.int16)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples_np.tobytes())
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Edge TTS fallback
    # ------------------------------------------------------------------
    async def _generate_edge_fallback(
        self,
        text: str,
        language: str,
        speed: float = 1.0,
        gender: str = "female",
    ) -> bytes:
        """Generate audio via Edge TTS as a fallback."""
        import edge_tts  # type: ignore

        voice = _EDGE_VOICE_MAP.get((language, gender))
        if voice is None:
            # Default fallback
            voice = "zh-CN-XiaoxiaoNeural" if language == "Chinese" else "ko-KR-SunHiNeural"
            logger.warning("No Edge TTS voice for (%s, %s); using %s", language, gender, voice)

        rate_str = (
            f"+{int((speed - 1.0) * 100)}%"
            if speed >= 1.0
            else f"{int((speed - 1.0) * 100)}%"
        )

        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        if not audio_data:
            logger.warning("Edge TTS returned empty audio for text: %s…", text[:40])
        return bytes(audio_data)

    # ------------------------------------------------------------------
    # Main public API
    # ------------------------------------------------------------------
    async def generate_audio(
        self,
        text: str,
        language: str,
        speed: float = 1.0,
        gender: str = "female",
    ) -> bytes:
        """Generate speech for *text* and return WAV bytes (mono, 16-bit).

        Parameters
        ----------
        text : str
            The text to synthesise.
        language : str
            ``"Chinese"`` or ``"Korean"``.
        speed : float, optional
            Playback speed multiplier (default ``1.0``).
        gender : str, optional
            ``"female"`` or ``"male"`` (default ``"female"``).

        Returns
        -------
        bytes
            Complete WAV file content (mono, 16-bit PCM).
        """
        text = text.strip()
        if not text:
            logger.warning("generate_audio called with empty text")
            return b""

        language = language.capitalize()
        gender = gender.lower()

        if language not in ("Chinese", "Korean"):
            logger.warning("Unsupported language '%s'; falling back to Edge TTS", language)
            return await self._generate_edge_fallback(text, language, speed, gender)

        # ------ Try CosyVoice2 ------
        model = await asyncio.to_thread(self._ensure_model)
        if model is None:
            logger.info("CosyVoice2 unavailable – using Edge TTS fallback")
            return await self._generate_edge_fallback(text, language, speed, gender)

        voice_cfg = _VOICE_MAP.get((language, gender))
        if voice_cfg is None:
            logger.error("No voice config for (%s, %s)", language, gender)
            return await self._generate_edge_fallback(text, language, speed, gender)

        ref_audio_path = voice_cfg["ref_audio"]
        prompt_text = voice_cfg["prompt_text"]

        try:
            prompt_speech = await asyncio.to_thread(self._load_reference, ref_audio_path)
        except FileNotFoundError:
            logger.warning(
                "Reference audio %s not found – falling back to Edge TTS", ref_audio_path
            )
            return await self._generate_edge_fallback(text, language, speed, gender)

        # Run the (blocking) CosyVoice2 inference in a thread
        try:
            wav_bytes = await asyncio.to_thread(
                self._run_inference, model, text, prompt_text, prompt_speech, speed
            )
            return wav_bytes
        except Exception as exc:
            logger.error("CosyVoice2 inference failed: %s – falling back to Edge TTS", exc)
            return await self._generate_edge_fallback(text, language, speed, gender)

    def _run_inference(
        self,
        model,
        tts_text: str,
        prompt_text: str,
        prompt_speech,
        speed: float,
    ) -> bytes:
        """Blocking helper that runs CosyVoice2 zero-shot inference."""
        import torch  # type: ignore

        all_segments: list = []
        sample_rate: int = 22050  # default; overridden from model

        for output in model.inference_zero_shot(
            tts_text,
            prompt_text,
            prompt_speech,
            stream=False,
            speed=speed,
        ):
            speech = output["tts_speech"]
            sample_rate = model.sample_rate
            all_segments.append(speech)

        if not all_segments:
            logger.warning("CosyVoice2 produced no audio segments")
            return b""

        # Concatenate all segments
        combined = torch.cat(all_segments, dim=-1)
        return self._torch_tensor_to_wav(combined, sample_rate)

    # ------------------------------------------------------------------
    # Streaming variant (async generator)
    # ------------------------------------------------------------------
    async def generate_audio_stream(
        self,
        text: str,
        language: str,
        speed: float = 1.0,
        gender: str = "female",
    ):
        """Async generator that yields WAV bytes chunk by chunk.

        For CosyVoice2 this yields one chunk per inference segment.
        For the Edge TTS fallback it yields a single chunk.
        """
        text = text.strip()
        if not text:
            return

        language = language.capitalize()
        gender = gender.lower()

        if language not in ("Chinese", "Korean"):
            wav = await self._generate_edge_fallback(text, language, speed, gender)
            if wav:
                yield wav
            return

        model = await asyncio.to_thread(self._ensure_model)
        if model is None:
            wav = await self._generate_edge_fallback(text, language, speed, gender)
            if wav:
                yield wav
            return

        voice_cfg = _VOICE_MAP.get((language, gender))
        if voice_cfg is None:
            wav = await self._generate_edge_fallback(text, language, speed, gender)
            if wav:
                yield wav
            return

        ref_audio_path = voice_cfg["ref_audio"]
        prompt_text = voice_cfg["prompt_text"]

        try:
            prompt_speech = await asyncio.to_thread(self._load_reference, ref_audio_path)
        except FileNotFoundError:
            wav = await self._generate_edge_fallback(text, language, speed, gender)
            if wav:
                yield wav
            return

        # Stream segments from CosyVoice2
        try:
            segments = await asyncio.to_thread(
                self._collect_segments, model, text, prompt_text, prompt_speech, speed
            )
            for speech_tensor, sr in segments:
                yield self._torch_tensor_to_wav(speech_tensor, sr)
        except Exception as exc:
            logger.error("CosyVoice2 streaming failed: %s – falling back to Edge TTS", exc)
            wav = await self._generate_edge_fallback(text, language, speed, gender)
            if wav:
                yield wav

    def _collect_segments(
        self,
        model,
        tts_text: str,
        prompt_text: str,
        prompt_speech,
        speed: float,
    ) -> list[tuple]:
        """Collect all inference segments (blocking)."""
        results = []
        for output in model.inference_zero_shot(
            tts_text,
            prompt_text,
            prompt_speech,
            stream=False,
            speed=speed,
        ):
            results.append((output["tts_speech"], model.sample_rate))
        return results
