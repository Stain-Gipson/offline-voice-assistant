"""Load a persona file and turn it into a Realtime `session.update` event."""

from dataclasses import dataclass
from pathlib import Path

import yaml

# The OpenAI Realtime protocol carries 16-bit mono PCM at 24 kHz by default.
SAMPLE_RATE = 24000


@dataclass(frozen=True)
class Persona:
    name: str
    instructions: str
    voice: str | None = None


def load_persona(path: str | Path) -> Persona:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [key for key in ("name", "instructions") if not data.get(key)]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")
    return Persona(
        name=str(data["name"]),
        instructions=str(data["instructions"]).strip(),
        voice=data.get("voice") or None,
    )


def session_update(persona: Persona) -> dict:
    """Build the first event the client sends after connecting."""
    audio = {
        "input": {
            "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
            # Server-side VAD decides when the user has finished speaking, and
            # interrupt_response lets the user cut the assistant off mid-reply.
            "turn_detection": {"type": "server_vad", "interrupt_response": True},
        },
        "output": {"format": {"type": "audio/pcm", "rate": SAMPLE_RATE}},
    }
    if persona.voice:
        audio["output"]["voice"] = persona.voice
    return {
        "type": "session.update",
        "session": {"type": "realtime", "instructions": persona.instructions, "audio": audio},
    }
