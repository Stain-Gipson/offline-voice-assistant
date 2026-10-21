from assistant.latency import TurnTracker


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_latency_runs_from_speech_stop_to_first_audio():
    clock = FakeClock()
    tracker = TurnTracker(clock=clock)

    tracker.handle({"type": "input_audio_buffer.speech_stopped"})
    clock.now = 0.85
    line = tracker.handle({"type": "response.output_audio.delta", "delta": ""})
    clock.now = 1.5
    later = tracker.handle({"type": "response.output_audio.delta", "delta": ""})

    assert line == "[latency] 850 ms from end of speech to first audio"
    assert later is None  # only the first chunk of a reply is timed
    assert tracker.latencies_ms == [850.0]


def test_audio_without_a_user_turn_is_not_timed():
    tracker = TurnTracker(clock=FakeClock())
    assert tracker.handle({"type": "response.output_audio.delta", "delta": ""}) is None
    assert tracker.latencies_ms == []


def test_transcripts_are_printed():
    tracker = TurnTracker()
    user = {"type": "conversation.item.input_audio_transcription.completed", "transcript": " hi "}
    bot = {"type": "response.output_audio_transcript.done", "transcript": "Hello!"}
    assert tracker.handle(user) == "you: hi"
    assert tracker.handle(bot) == "assistant: Hello!"


def test_summary():
    clock = FakeClock()
    tracker = TurnTracker(clock=clock)
    for latency in (0.5, 0.9, 0.7):
        clock.now = 0.0
        tracker.handle({"type": "input_audio_buffer.speech_stopped"})
        clock.now = latency
        tracker.handle({"type": "response.output_audio.delta"})
    assert tracker.summary() == "3 turns | median 700 ms | min 500 ms | max 900 ms"
    assert TurnTracker().summary() == "No complete turns measured."
