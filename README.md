# Offline Voice Assistant

A voice assistant that runs fully on your own machine: you speak, pause, and it answers out loud. No API key, no cloud service.

The speech pipeline is [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech) (Apache-2.0). This repo adds the parts around it:

- **Backend configs** (`configs/`): YAML pipelines that swap the speech-to-text and text-to-speech models with no code changes, so they can be compared.
- **Persona** (`personas/`): the assistant's role and rules, sent to the server as the session instructions.
- **Realtime client** (`assistant/`): streams the microphone to the server over the OpenAI Realtime WebSocket protocol, plays the reply, stops playback when you talk over it, and times every turn.

## How it works

```
mic ──► client ──WebSocket (OpenAI Realtime events)──► speech-to-speech server
                                                       │
                                     Silero VAD ──► STT ──► LLM ──► TTS
                                                       │
speaker ◄── client ◄────────── audio deltas ◄──────────┘
```

The server runs four stages (VAD, STT, LLM, TTS), each in its own thread and connected by queues, so it can be transcribing, generating and speaking at the same time. Silero VAD v5 finds where speech starts and stops. The LLM streams its reply into TTS, so audio starts before the full answer is written.

The client measures **end-of-speech to first audio**: the time from the server deciding you stopped talking to the first chunk of the reply arriving. That single number includes STT, the LLM's first tokens and TTS's first audio.

## Setup

Python 3.11 is recommended (Kokoro on macOS needs 3.11 or 3.12).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install "speech-to-speech[kokoro]"   # only for the configs that use Kokoro
```

On Ubuntu, install the audio libraries first: `sudo apt-get install libportaudio2 libsndfile1`.

## Run

Terminal 1, start the server with a config (the first run downloads the models):

```bash
speech-to-speech serve -f configs/mac.yaml      # Apple Silicon
speech-to-speech serve -f configs/linux.yaml    # Linux / Windows with NVIDIA
```

Terminal 2, start the client:

```bash
python -m assistant.client --persona personas/college_helpdesk.yaml
```

Use headphones so the microphone does not hear the assistant. Press Ctrl+C to stop; the client prints a latency summary.

## Comparing backends

| Config | VAD | STT | LLM | TTS |
|---|---|---|---|---|
| `mac.yaml` | Silero | Parakeet TDT | Qwen3.5-4B (MLX, 4-bit) | Qwen3-TTS |
| `mac-whisper-kokoro.yaml` | Silero | Whisper (MLX Audio) | Qwen3.5-4B (MLX, 4-bit) | Kokoro-82M |
| `linux.yaml` | Silero | Parakeet TDT | Qwen3.5-4B (Transformers) | Kokoro-82M |

Run the same few questions against each config and note the client's summary line:

| Config | Machine | Turns | Median latency | Notes |
|---|---|---|---|---|
| | | | | |

## Tests

```bash
pytest
```

The tests cover the persona loader, the `session.update` event, the turn timer and the config structure. They do not load any models.

## Credits

- [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech): the VAD, STT, LLM and TTS pipeline and the Realtime server.
- [Silero VAD](https://github.com/snakers4/silero-vad), [NVIDIA Parakeet TDT](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), [Qwen3.5](https://huggingface.co/Qwen), [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M).

## License

MIT for the code in this repo. Upstream projects and models keep their own licenses.
