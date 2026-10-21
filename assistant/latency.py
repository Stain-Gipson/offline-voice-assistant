"""Follow Realtime server events, print the conversation and time each turn."""

import statistics
import time
from collections.abc import Callable


class TurnTracker:
    """Measures the delay the user actually feels on every turn.

    The clock starts when the server reports `input_audio_buffer.speech_stopped`
    (its VAD decided the user finished talking) and stops at the first
    `response.output_audio.delta` of the reply. That one number covers STT,
    the LLM's first tokens and TTS's first audio chunk together.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._speech_stopped_at: float | None = None
        self.latencies_ms: list[float] = []

    def handle(self, event: dict) -> str | None:
        """Update timing from one server event; return a line to print, if any."""
        kind = event.get("type")
        if kind == "input_audio_buffer.speech_stopped":
            self._speech_stopped_at = self._clock()
        elif kind == "response.output_audio.delta" and self._speech_stopped_at is not None:
            latency_ms = (self._clock() - self._speech_stopped_at) * 1000
            self._speech_stopped_at = None  # only the first audio chunk counts
            self.latencies_ms.append(latency_ms)
            return f"[latency] {latency_ms:.0f} ms from end of speech to first audio"
        elif kind == "conversation.item.input_audio_transcription.completed":
            return f"you: {event.get('transcript', '').strip()}"
        elif kind == "response.output_audio_transcript.done":
            return f"assistant: {event.get('transcript', '').strip()}"
        elif kind == "error":
            error = event.get("error") or {}
            return f"[error] {error.get('message', error)}"
        return None

    def summary(self) -> str:
        if not self.latencies_ms:
            return "No complete turns measured."
        return (
            f"{len(self.latencies_ms)} turns | "
            f"median {statistics.median(self.latencies_ms):.0f} ms | "
            f"min {min(self.latencies_ms):.0f} ms | "
            f"max {max(self.latencies_ms):.0f} ms"
        )
