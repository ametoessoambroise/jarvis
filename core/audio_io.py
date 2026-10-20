"""Audio I/O manager — capture micro, diffusion haut-parleur, file bornée.

Ce module isole la gestion matérielle et asynchrone du son (sounddevice),
avec une politique de file bornée garantissant qu'aucun callback audio
ne lève QueueFull ni ne bloque le thread audio PortAudio.

Références :
    TRD.md §1.4, §5.1 (modèle de threads et files)
    DEVELOPMENT_PHASES.md P4 (isolation audio_io)
    RISKS.md R-O14 (politique de file bornée)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

try:
    import sounddevice as sd

    _HAS_SOUNDDEVICE = True
except (ImportError, OSError):
    sd = None
    _HAS_SOUNDDEVICE = False

from core.utils import (
    CHANNELS,
    CHUNK_SIZE,
    RECEIVE_SAMPLE_RATE,
    SEND_SAMPLE_RATE,
)

logger = logging.getLogger("jarvis.audio")


class AudioDeviceError(RuntimeError):
    """Levée lorsqu'un périphérique audio (micro ou haut-parleur) est indisponible."""


class BoundedAudioQueue:
    """File asynchrone bornée avec politique d'éviction du plus ancien.

    Garantit que push_nowait() n'échoue jamais avec QueueFull,
    même en cas de rafale depuis le callback PortAudio.
    """

    def __init__(
        self, maxsize: int = 10, loop: asyncio.AbstractEventLoop | None = None
    ):
        self.maxsize = maxsize
        self._loop = loop
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=self.maxsize)

    @property
    def queue(self) -> asyncio.Queue:
        return self._queue

    def push_evict_oldest(self, item: dict) -> None:
        """Insère un élément ; si la file est pleine, éjecte le plus ancien."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            # Très rare double course : on réessaye une fois
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(item)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    async def get(self) -> dict:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()

    def qsize(self) -> int:
        return self._queue.qsize()


class AudioIO:
    """Gestionnaire des flux audio micro et haut-parleur pour la session temps réel."""

    def __init__(self, max_out_queue: int = 10):
        self.max_out_queue = max_out_queue
        self.out_queue = BoundedAudioQueue(maxsize=max_out_queue)
        self.audio_in_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def reset_queues(self, loop: asyncio.AbstractEventLoop) -> None:
        """Réinitialise les files d'entrée et de sortie pour une nouvelle boucle."""
        self.out_queue.set_loop(loop)
        self.audio_in_queue = asyncio.Queue()

    async def send_realtime_loop(self, session) -> None:
        """Consomme la out_queue et transmet les fragments PCM au provider."""
        while True:
            msg = await self.out_queue.get()
            await session.send_realtime_input(media=msg)

    async def listen_mic_loop(
        self,
        loop: asyncio.AbstractEventLoop,
        is_speaking_fn: Callable[[], bool],
        is_muted_fn: Callable[[], bool],
    ) -> None:
        """Capture le micro et alimente la out_queue."""
        if not _HAS_SOUNDDEVICE:
            raise AudioDeviceError(
                "Le module 'sounddevice' n'est pas disponible ou PortAudio est manquant."
            )

        print("[JARVIS] 🎤 Mic started")

        def callback(indata, frames, time_info, status):
            if status:
                logger.debug("Microphone stream status: %s", status)
            if not is_speaking_fn() and not is_muted_fn():
                data = indata.tobytes()
                # Threadsafe push avec éviction si la file est pleine
                loop.call_soon_threadsafe(
                    self.out_queue.push_evict_oldest,
                    {"data": data, "mime_type": "audio/pcm"},
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic error: {e}")
            raise AudioDeviceError(f"Périphérique microphone inaccessible: {e}") from e

    async def play_audio_loop(
        self,
        set_speaking_fn: Callable[[bool], None],
        turn_done_event: asyncio.Event | None,
    ) -> None:
        """Consomme la audio_in_queue et joue les fragments PCM reçus."""
        if not _HAS_SOUNDDEVICE:
            raise AudioDeviceError(
                "Le module 'sounddevice' est manquant pour la lecture audio."
            )

        print("[JARVIS] 🔊 Play started")
        stream = None
        try:
            stream = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            )
            stream.start()

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        turn_done_event
                        and turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        set_speaking_fn(False)
                        turn_done_event.clear()
                    continue

                set_speaking_fn(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] ❌ Play error: {e}")
            raise AudioDeviceError(f"Erreur lors de la lecture audio: {e}") from e
        finally:
            set_speaking_fn(False)
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
