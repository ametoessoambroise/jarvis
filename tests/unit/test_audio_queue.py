"""Unit tests for BoundedAudioQueue and AudioIO (P4 / RISKS.md R-O14)."""

import asyncio
import pytest

from core.audio_io import BoundedAudioQueue, AudioIO, AudioDeviceError


@pytest.mark.asyncio
async def test_bounded_queue_eviction_when_full():
    """Vérifie que la file bornée évince le plus ancien élément quand elle atteint maxsize."""
    loop = asyncio.get_running_loop()
    bq = BoundedAudioQueue(maxsize=3, loop=loop)

    # Remplir la file
    bq.push_evict_oldest({"id": 1})
    bq.push_evict_oldest({"id": 2})
    bq.push_evict_oldest({"id": 3})
    assert bq.qsize() == 3

    # Insérer un 4e élément : l'élément 1 doit être évincé
    bq.push_evict_oldest({"id": 4})
    assert bq.qsize() == 3

    # Dépiler : on doit obtenir 2, 3, 4
    item1 = await bq.get()
    item2 = await bq.get()
    item3 = await bq.get()
    assert item1["id"] == 2
    assert item2["id"] == 3
    assert item3["id"] == 4
    assert bq.empty()


@pytest.mark.asyncio
async def test_audio_io_reset_queues():
    """Vérifie la réinitialisation propre des files pour une nouvelle boucle."""
    loop = asyncio.get_running_loop()
    audio = AudioIO(max_out_queue=5)
    audio.reset_queues(loop)

    assert audio.out_queue.maxsize == 5
    assert audio.out_queue.empty()
    assert audio.audio_in_queue.empty()
