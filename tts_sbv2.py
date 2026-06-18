"""
Style-Bert-VITS2 TTS wrapper for Japanese voices.

Models are downloaded from HuggingFace on first use:
  - Female: litagin/sbv2_koharune_ami
  - Male:   litagin/style_bert_vits2_jvnv  (multi-speaker, uses jvnv-M1-jp)

Usage:
    engine = StyleBertVITS2Engine()
    wav_bytes = await engine.generate_audio("こんにちは", speed=1.0, gender="female")
"""

import io
import os
import wave
import asyncio
import logging
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory where model snapshots are stored
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _BASE_DIR / "model_assets"

# HuggingFace repo IDs and local directory names
_VOICE_CONFIG = {
    "female": {
        "repo_id": "litagin/style_bert_vits2_jvnv",
        "local_dir": "jvnv",
        "model_file": "jvnv-F1-jp/jvnv-F1-jp_e160_s14000.safetensors",
        "config_file": "jvnv-F1-jp/config.json",
        "style_file": "jvnv-F1-jp/style_vectors.npy",
        "speaker": "jvnv-F1-jp",  # female speaker in multi-speaker model
    },
    "male": {
        "repo_id": "litagin/style_bert_vits2_jvnv",
        "local_dir": "jvnv",
        "model_file": "jvnv-M1-jp/jvnv-M1-jp_e158_s14000.safetensors",
        "config_file": "jvnv-M1-jp/config.json",
        "style_file": "jvnv-M1-jp/style_vectors.npy",
        "speaker": "jvnv-M1-jp",  # male speaker in multi-speaker model
    },
}


class StyleBertVITS2Engine:
    """Async-friendly, thread-safe wrapper around Style-Bert-VITS2."""

    def __init__(self):
        self._models: dict = {}          # gender -> TTSModel
        self._lock = threading.Lock()    # guards lazy init
        self._download_lock = threading.Lock()

    # ------------------------------------------------------------------
    # WAV conversion helper
    # ------------------------------------------------------------------
    @staticmethod
    def _samples_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
        """Convert a numpy audio array to mono 16-bit WAV bytes.

        Handles both float and int arrays produced by Style-Bert-VITS2 /
        scipy.io.wavfile output.
        """
        buf = io.BytesIO()

        # Ensure mono
        if samples.ndim > 1:
            samples = samples[:, 0]

        # Normalise to int16
        if np.issubdtype(samples.dtype, np.floating):
            peak = np.max(np.abs(samples)) or 1.0
            if peak > 1.0:
                samples = samples / peak
            int_samples = (samples * 32767).astype(np.int16)
        elif samples.dtype != np.int16:
            int_samples = samples.astype(np.int16)
        else:
            int_samples = samples

        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(int_samples.tobytes())

        return buf.getvalue()

    # ------------------------------------------------------------------
    # Model download
    # ------------------------------------------------------------------
    def _ensure_downloaded(self, gender: str) -> Path:
        """Download model snapshot from HuggingFace if not already present.

        Returns the local directory containing the model files.
        """
        cfg = _VOICE_CONFIG[gender]
        local_dir = _ASSETS_DIR / cfg["local_dir"]

        # Quick check – avoid acquiring the lock if files already exist
        if self._model_files_exist(local_dir, cfg):
            return local_dir

        with self._download_lock:
            # Re-check after acquiring lock (another thread may have downloaded)
            if self._model_files_exist(local_dir, cfg):
                return local_dir

            logger.info(
                "Downloading Style-Bert-VITS2 model '%s' from HuggingFace…",
                cfg["repo_id"],
            )
            try:
                from huggingface_hub import snapshot_download

                snapshot_download(
                    repo_id=cfg["repo_id"],
                    local_dir=str(local_dir),
                    local_dir_use_symlinks=False,
                )
                logger.info("✅ Model downloaded to %s", local_dir)
            except Exception as e:
                logger.error("❌ Failed to download model %s: %s", cfg["repo_id"], e)
                raise

        return local_dir

    @staticmethod
    def _model_files_exist(local_dir: Path, cfg: dict) -> bool:
        """Return True if the essential model files are already present."""
        if not local_dir.is_dir():
            return False
        # Check for config and style vectors
        if not (local_dir / cfg["config_file"]).is_file():
            return False
        if not (local_dir / cfg["style_file"]).is_file():
            return False
        # Check for model weights (.safetensors or .pth)
        has_weights = (
            (local_dir / cfg["model_file"]).is_file()
            or any(local_dir.glob("*.safetensors"))
            or any(local_dir.glob("*.pth"))
        )
        return has_weights

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def _find_model_file(self, local_dir: Path, cfg: dict) -> Path:
        """Locate the model weights file, trying multiple extensions."""
        # Try the configured filename first
        preferred = local_dir / cfg["model_file"]
        if preferred.is_file():
            return preferred

        # Fall back to any .safetensors
        safetensors = list(local_dir.glob("*.safetensors"))
        if safetensors:
            return safetensors[0]

        # Fall back to any .pth
        pth_files = list(local_dir.glob("*.pth"))
        if pth_files:
            return pth_files[0]

        raise FileNotFoundError(
            f"No model weights (.safetensors / .pth) found in {local_dir}"
        )

    def _load_model(self, gender: str):
        """Load a TTSModel instance for the given gender.

        Must be called while holding ``self._lock``.
        """
        from style_bert_vits2.tts_model import TTSModel

        cfg = _VOICE_CONFIG[gender]
        local_dir = self._ensure_downloaded(gender)

        model_path = self._find_model_file(local_dir, cfg)
        config_path = local_dir / cfg["config_file"]
        style_path = local_dir / cfg["style_file"]

        logger.info("Loading SBV2 model (%s) from %s …", gender, model_path)

        model = TTSModel(
            model_path=model_path,
            config_path=config_path,
            style_vec_path=style_path,
            device="cpu",
        )
        
        model.load()
        
        # Preload the BERT model and tokenizer for Japanese to cache them and avoid path assertions
        try:
            from style_bert_vits2.nlp.bert_models import load_model, load_tokenizer
            from style_bert_vits2.constants import Languages
            logger.info("Preloading Japanese BERT tokenizer and model from Hugging Face...")
            load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            bert_model = load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            bert_model.float()
        except Exception as e:
            logger.warning(f"Failed to preload BERT model: {e}")

        # Force PyTorch TTS model weights to float32 on CPU to avoid Half precision crashes
        if hasattr(model, "_TTSModel__net_g") and getattr(model, "_TTSModel__net_g") is not None:
            getattr(model, "_TTSModel__net_g").float()

        # For multi-speaker models, log available speakers for debugging
        if hasattr(model, "spk2id") and model.spk2id:
            logger.info(
                "Available speakers for %s: %s", gender, list(model.spk2id.keys())
            )
        elif hasattr(model, "config") and hasattr(model.config, "spk2id"):
            logger.info(
                "Available speakers for %s: %s",
                gender,
                list(model.config.spk2id.keys()),
            )

        self._models[gender] = model
        logger.info("✅ SBV2 model (%s) loaded successfully!", gender)

    def _get_model(self, gender: str):
        """Return a TTSModel for *gender*, initialising lazily if needed."""
        if gender in self._models:
            return self._models[gender]

        with self._lock:
            # Double-checked locking
            if gender in self._models:
                return self._models[gender]
            self._load_model(gender)
            return self._models[gender]

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------
    def _infer_sync(self, text: str, speed: float, gender: str):
        """Run TTS inference synchronously (blocking). Returns (sr, audio)."""
        from style_bert_vits2.constants import Languages

        model = self._get_model(gender)
        cfg = _VOICE_CONFIG[gender]

        kwargs: dict = {
            "text": text,
            "language": Languages.JP,
            "style": "Neutral",
            "style_weight": 5.0,
            "length": 1.0 / speed if speed > 0 else 1.0,
        }

        # Pass speaker name for multi-speaker models
        if cfg["speaker"]:
            # Try to find a valid male speaker name
            speaker = cfg["speaker"]
            available_speakers = []

            if hasattr(model, "spk2id") and model.spk2id:
                available_speakers = list(model.spk2id.keys())
            elif hasattr(model, "config") and hasattr(model.config, "spk2id"):
                available_speakers = list(model.config.spk2id.keys())

            if available_speakers:
                if speaker not in available_speakers:
                    # Try to find a male speaker by pattern matching
                    male_speakers = [
                        s for s in available_speakers if "M1" in s or "male" in s.lower()
                    ]
                    if male_speakers:
                        speaker = male_speakers[0]
                    else:
                        speaker = available_speakers[0]
                    logger.info(
                        "Speaker '%s' not found; using '%s' (available: %s)",
                        cfg["speaker"],
                        speaker,
                        available_speakers,
                    )

            kwargs["speaker_id"] = (
                model.spk2id.get(speaker, 0)
                if hasattr(model, "spk2id") and model.spk2id
                else 0
            )

        sr, audio = model.infer(**kwargs)
        return sr, np.asarray(audio, dtype=np.float32)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------
    async def generate_audio(
        self, text: str, speed: float = 1.0, gender: str = "female"
    ) -> bytes:
        """Generate WAV bytes for the given Japanese *text*.

        Parameters
        ----------
        text : str
            Japanese text to synthesise.
        speed : float
            Playback speed multiplier (1.0 = normal).
        gender : str
            ``"female"`` (Koharune Ami) or ``"male"`` (JVNV-M1).

        Returns
        -------
        bytes
            Mono 16-bit WAV audio.
        """
        gender = gender.lower()
        if gender not in _VOICE_CONFIG:
            raise ValueError(
                f"Unknown gender '{gender}'. Choose from: {list(_VOICE_CONFIG.keys())}"
            )

        clean = text.strip()
        if not clean:
            return b""

        # Run the blocking inference on a worker thread
        sr, audio = await asyncio.to_thread(self._infer_sync, clean, speed, gender)
        return self._samples_to_wav(audio, sr)

    async def generate_audio_stream(
        self, text: str, speed: float = 1.0, gender: str = "female"
    ):
        """Async generator that yields a single WAV bytes chunk.

        Provided for interface compatibility with the Kokoro TTSEngine.
        """
        wav_bytes = await self.generate_audio(text, speed=speed, gender=gender)
        if wav_bytes:
            yield wav_bytes
