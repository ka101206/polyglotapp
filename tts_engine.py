# tts_engine.py — Router that delegates to per-language TTS sub-engines
import os
import io
import re
import wave
import asyncio
import threading

import numpy as np


class TTSEngine:
    """Routes TTS requests to the appropriate sub-engine based on language and gender."""

    def __init__(self):
        self.stop_flag = threading.Event()

        # Lazy-loaded sub-engines
        self._sbv2 = None       # Japanese (Style-Bert-VITS2)
        self._melo = None       # Spanish/French (MeloTTS)
        self._chatterbox = None  # Italian (Chatterbox)
        self._cosyvoice = None   # Chinese/Korean (CosyVoice2)

        # Legacy Kokoro engine (kept as fallback for JP male if JVNV unavailable)
        self._kokoro = None
        self._ja_g2p = None
        self._kokoro_lock = threading.Lock()

    def _get_sbv2(self):
        if self._sbv2 is None:
            try:
                from tts_sbv2 import StyleBertVITS2Engine
                self._sbv2 = StyleBertVITS2Engine()
                print("✅ Style-Bert-VITS2 engine loaded")
            except Exception as e:
                print(f"⚠️ Style-Bert-VITS2 not available: {e}")
        return self._sbv2

    def _get_melo(self):
        if self._melo is None:
            try:
                from tts_melo import MeloTTSEngine
                self._melo = MeloTTSEngine()
                print("✅ MeloTTS engine loaded")
            except Exception as e:
                print(f"⚠️ MeloTTS not available: {e}")
        return self._melo

    def _get_chatterbox(self):
        if self._chatterbox is None:
            try:
                from tts_chatterbox import ChatterboxTTSEngine
                self._chatterbox = ChatterboxTTSEngine()
                print("✅ Chatterbox engine loaded")
            except Exception as e:
                print(f"⚠️ Chatterbox not available: {e}")
        return self._chatterbox

    def _get_cosyvoice(self):
        if self._cosyvoice is None:
            try:
                from tts_cosyvoice import CosyVoiceTTS
                self._cosyvoice = CosyVoiceTTS()
                print("✅ CosyVoice2 engine loaded")
            except Exception as e:
                print(f"⚠️ CosyVoice2 not available: {e}")
        return self._cosyvoice

    def stop(self):
        self.stop_flag.set()

    def reset(self):
        self.stop_flag.clear()

    @staticmethod
    def _samples_to_wav(samples, sample_rate) -> bytes:
        """Convert float32 numpy array to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((samples * 32767).astype(np.int16).tobytes())
        return buf.getvalue()

    async def _edge_tts_fallback(self, text, speed=1.0, language="Japanese", gender="female"):
        """Edge TTS fallback for any language/gender combo without a dedicated engine."""
        import edge_tts

        voice_map_male = {
            "Spanish": "es-ES-AlvaroNeural",
            "French": "fr-FR-HenriNeural",
            "Italian": "it-IT-DiegoNeural",
            "Chinese": "zh-CN-YunxiNeural",
            "Korean": "ko-KR-InJoonNeural",
            "Japanese": "ja-JP-KeitaNeural",
            "English": "en-US-GuyNeural",
        }
        voice_map_female = {
            "Spanish": "es-ES-ElviraNeural",
            "French": "fr-FR-DeniseNeural",
            "Italian": "it-IT-ElsaNeural",
            "Chinese": "zh-CN-XiaoxiaoNeural",
            "Korean": "ko-KR-SunHiNeural",
            "Japanese": "ja-JP-NanamiNeural",
            "English": "en-US-JennyNeural",
        }

        vmap = voice_map_male if gender == "male" else voice_map_female
        voice = vmap.get(language, "en-US-GuyNeural")
        rate_str = f"+{int((speed - 1.0) * 100)}%" if speed >= 1.0 else f"{int((speed - 1.0) * 100)}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if self.stop_flag.is_set():
                break
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        if audio_data:
            yield bytes(audio_data)

    async def generate_audio_stream(self, text, speed=1.0, language="Japanese", gender="female"):
        """Main entry point. Routes to the appropriate engine based on language + gender."""

        if self.stop_flag.is_set():
            return

        # --- Japanese → Style-Bert-VITS2 ---
        if language == "Japanese":
            engine = self._get_sbv2()
            if engine:
                try:
                    wav_bytes = await engine.generate_audio(text, speed=speed, gender=gender)
                    if wav_bytes:
                        yield wav_bytes
                        return
                except Exception as e:
                    print(f"⚠️ SBVITS2 error: {e}")
                    raise e
            return

        # --- Chinese / Korean → CosyVoice2 ---
        if language in ("Chinese", "Korean"):
            engine = self._get_cosyvoice()
            if engine:
                try:
                    wav_bytes = await engine.generate_audio(text, language=language, speed=speed, gender=gender)
                    if wav_bytes:
                        yield wav_bytes
                        return
                except Exception as e:
                    print(f"⚠️ Primary engine failed: {e}")
                    raise e
            return

        # --- Spanish / French → MeloTTS (female) or Edge TTS (male) ---
        if language in ("Spanish", "French"):
            if gender == "female":
                engine = self._get_melo()
                if engine:
                    try:
                        wav_bytes = await engine.generate_audio(text, language=language, speed=speed)
                        if wav_bytes:
                            yield wav_bytes
                            return
                    except Exception as e:
                        print(f"⚠️ Primary engine failed: {e}")
                        raise e
            # Fallback for male or if engine missing
            async for chunk in self._edge_tts_fallback(text, speed, language, gender):
                yield chunk
            return

        # --- Italian → Chatterbox ---
        if language == "Italian":
            engine = self._get_chatterbox()
            if engine:
                try:
                    wav_bytes = await engine.generate_audio(text, speed=speed, gender=gender)
                    if wav_bytes:
                        yield wav_bytes
                        return
                except Exception as e:
                    print(f"⚠️ Chatterbox error, falling back to Edge TTS: {e}")
            # Fallback
            async for chunk in self._edge_tts_fallback(text, speed, language, gender):
                yield chunk
            return

        # --- Any other language → Edge TTS ---
        async for chunk in self._edge_tts_fallback(text, speed, language, gender):
            yield chunk
