"""Utilities for generating and converting audio for send_message.

Functions:
- generate_tts(text, out_path, lang='fr', format='mp3') -> path
- convert_audio(input_path, out_path, format) -> path
- download_file(url, out_path) -> path

This module prefers `pydub` + `gtts` if available, otherwise tries `pyttsx3`.
"""
from __future__ import annotations
import os
import tempfile
import shutil
from typing import Optional


def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def download_file(url: str, out_path: str) -> str:
    """Download a remote file to out_path using requests."""
    try:
        import requests
    except Exception as e:
        raise RuntimeError("requests is required to download files") from e
    _ensure_parent(out_path)
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        shutil.copyfileobj(r.raw, f)
    return out_path


def convert_audio(input_path: str, out_path: str, format: str = "mp3") -> str:
    """Convert audio to target format using pydub if available.

    If pydub/ffmpeg is not available the function will raise RuntimeError with guidance.
    """
    try:
        from pydub import AudioSegment
    except Exception as e:
        raise RuntimeError(
            "pydub (and ffmpeg) are required for audio conversion. Install with `pip install pydub` and ensure ffmpeg is available in PATH."
        ) from e

    _ensure_parent(out_path)
    audio = AudioSegment.from_file(input_path)
    audio.export(out_path, format=format)
    return out_path


def generate_tts(text: str, out_path: str, lang: str = "fr", format: str = "mp3") -> str:
    """Generate TTS audio from text.

    Tries gTTS first, then pyttsx3 as fallback. Returns path to generated file.
    """
    _ensure_parent(out_path)

    # Try gTTS -> saves mp3
    try:
        from gtts import gTTS
        tmp = out_path
        if format != "mp3":
            # generate mp3 first then convert
            tmp = out_path + ".tmp.mp3"
        tts = gTTS(text=text, lang=lang)
        tts.save(tmp)
        if format != "mp3":
            return convert_audio(tmp, out_path, format=format)
        return tmp
    except Exception:
        pass

    # Fallback to pyttsx3 (offline)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Try to save to file using say+save_to_file if available
        try:
            engine.save_to_file(text, out_path)
            engine.runAndWait()
            return out_path
        except Exception:
            # As a final fallback, write a WAV via temporary system approach
            tmp = out_path + ".tmp.wav"
            engine.save_to_file(text, tmp)
            engine.runAndWait()
            if format != "wav":
                return convert_audio(tmp, out_path, format=format)
            return tmp
    except Exception:
        pass

    raise RuntimeError(
        "No TTS engine available. Install `gTTS` (`pip install gTTS`) or `pyttsx3` for offline TTS."
    )
