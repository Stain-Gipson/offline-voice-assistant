from pathlib import Path

import pytest

from assistant.persona import SAMPLE_RATE, Persona, load_persona, session_update

ROOT = Path(__file__).resolve().parent.parent


def test_bundled_persona_loads():
    persona = load_persona(ROOT / "personas" / "college_helpdesk.yaml")
    assert persona.name
    assert persona.instructions
    assert persona.voice is None  # empty in the file means "backend default"


def test_missing_instructions_is_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("name: Nobody\n", encoding="utf-8")
    with pytest.raises(ValueError, match="instructions"):
        load_persona(path)


def test_session_update_shape():
    event = session_update(Persona(name="t", instructions="Be brief."))
    session = event["session"]
    assert event["type"] == "session.update"
    assert session["instructions"] == "Be brief."
    assert session["audio"]["input"]["format"] == {"type": "audio/pcm", "rate": SAMPLE_RATE}
    assert session["audio"]["input"]["turn_detection"]["interrupt_response"] is True
    assert "voice" not in session["audio"]["output"]


def test_voice_is_sent_when_set():
    event = session_update(Persona(name="t", instructions="x", voice="af_heart"))
    assert event["session"]["audio"]["output"]["voice"] == "af_heart"
