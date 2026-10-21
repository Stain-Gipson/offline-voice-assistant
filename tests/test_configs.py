"""Structural checks on configs/*.yaml, following the speech-to-speech YAML rules."""

from pathlib import Path

import pytest
import yaml

CONFIGS = sorted((Path(__file__).resolve().parent.parent / "configs").glob("*.yaml"))
STAGES = ("vad", "stt", "llm", "tts")


def test_configs_exist():
    assert CONFIGS


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.name)
def test_config_structure(path):
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert config["schema_version"] == 1
    blocks, pipelines = config["blocks"], config["pipelines"]
    assert blocks and pipelines

    for block in blocks.values():
        assert block["kind"] in STAGES
        assert block["backend"]

    for pipeline in pipelines.values():
        stages = pipeline["stages"]
        assert set(stages) == set(STAGES), "all four stages are required"
        for stage, block_id in stages.items():
            assert blocks[block_id]["kind"] == stage
