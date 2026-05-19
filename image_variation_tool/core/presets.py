import json
from pathlib import Path
from image_variation_tool.core.models import SizePreset

_SIZES_PATH = Path(__file__).parent.parent / "presets" / "sizes.json"


def load_presets() -> list[SizePreset]:
    data = json.loads(_SIZES_PATH.read_text(encoding="utf-8"))
    result = []
    for channel, sizes in data.items():
        for s in sizes:
            result.append(SizePreset(channel=channel, name=s["name"], width=s["width"], height=s["height"]))
    return result


def get_channels() -> list[str]:
    return sorted({p.channel for p in load_presets()})


def get_presets_by_channel(channel: str) -> list[SizePreset]:
    return [p for p in load_presets() if p.channel == channel]
