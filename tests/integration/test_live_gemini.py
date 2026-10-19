import asyncio
import pytest
from google import genai
from google.genai import types
from core.utils import _get_api_key, LIVE_MODEL
from core.tools import TOOL_DECLARATIONS


async def _run_live_test():
    client = genai.Client(api_key=_get_api_key(), http_options={"api_version": "v1beta"})
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="You are a test.",
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
        session_resumption=types.SessionResumptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
    )
    async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
        await session.send_realtime_input(media={"mime_type": "audio/pcm", "data": b"\x00" * 1024})
        async for response in session.receive():
            assert response is not None
            break


@pytest.mark.integration
def test_live_gemini_connection():
    """Opt-in integration test connecting to Gemini Live."""
    asyncio.run(_run_live_test())


if __name__ == "__main__":
    asyncio.run(_run_live_test())
