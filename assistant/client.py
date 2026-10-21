"""Talk to a local speech-to-speech server over the OpenAI Realtime WebSocket protocol.

    speech-to-speech serve -f configs/mac.yaml           # terminal 1
    python -m assistant.client                           # terminal 2

Use headphones so the microphone does not pick up the assistant's own voice.
"""

import argparse
import asyncio
import base64
import json
import threading

import websockets

from assistant.latency import TurnTracker
from assistant.persona import SAMPLE_RATE, load_persona, session_update

CHUNK_MS = 100  # how much microphone audio goes into each append event


class Player:
    """Plays PCM16 audio as it arrives and can be flushed when the user barges in."""

    def __init__(self, rate: int = SAMPLE_RATE):
        import sounddevice as sd

        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stream = sd.RawOutputStream(
            samplerate=rate, channels=1, dtype="int16", callback=self._fill
        )
        self._stream.start()

    def _fill(self, outdata, frames, time_info, status):
        size = len(outdata)
        with self._lock:
            chunk = bytes(self._buffer[:size])
            del self._buffer[:size]
        outdata[: len(chunk)] = chunk
        outdata[len(chunk) :] = b"\x00" * (size - len(chunk))

    def play(self, pcm: bytes) -> None:
        with self._lock:
            self._buffer.extend(pcm)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


async def stream_microphone(ws, rate: int = SAMPLE_RATE) -> None:
    """Send microphone audio to the server as `input_audio_buffer.append` events."""
    import sounddevice as sd

    loop = asyncio.get_running_loop()
    chunks: asyncio.Queue[bytes] = asyncio.Queue()

    def on_audio(indata, frames, time_info, status):
        loop.call_soon_threadsafe(chunks.put_nowait, bytes(indata))

    blocksize = rate * CHUNK_MS // 1000
    with sd.RawInputStream(
        samplerate=rate, channels=1, dtype="int16", blocksize=blocksize, callback=on_audio
    ):
        while True:
            pcm = await chunks.get()
            await ws.send(
                json.dumps(
                    {"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm).decode()}
                )
            )


async def run(url: str, persona_path: str) -> None:
    persona = load_persona(persona_path)
    tracker = TurnTracker()
    player = Player()
    print(f"Connecting to {url} as '{persona.name}'. Start speaking; Ctrl+C to stop.")
    try:
        async with websockets.connect(url, max_size=None) as ws:
            await ws.send(json.dumps(session_update(persona)))
            mic = asyncio.create_task(stream_microphone(ws))
            try:
                async for message in ws:
                    event = json.loads(message)
                    kind = event.get("type")
                    if kind == "response.output_audio.delta":
                        player.play(base64.b64decode(event["delta"]))
                    elif kind == "input_audio_buffer.speech_started":
                        player.clear()  # user is talking over the assistant: stop playback now
                    line = tracker.handle(event)
                    if line:
                        print(line, flush=True)
            finally:
                mic.cancel()
    finally:
        player.close()
        print(tracker.summary())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="ws://127.0.0.1:8765/v1/realtime")
    parser.add_argument("--persona", default="personas/college_helpdesk.yaml")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.url, args.persona))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
