import json
from functools import lru_cache
from pathlib import Path
from image_variation_tool.core.models import SizePreset

_SIZES_PATH = Path(__file__).parent.parent / "presets" / "sizes.json"


@lru_cache(maxsize=1)
def load_presets() -> list[SizePreset]:
    try:
        data = json.loads(_SIZES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Presets file not found at {_SIZES_PATH}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {_SIZES_PATH}: {e}")
    result = []
    for channel, sizes in data.items():
        for s in sizes:
            required = {"name", "width", "height"}
            if not required.issubset(s.keys()):
                raise ValueError(f"Missing keys in {channel}: {required - s.keys()}")
            result.append(SizePreset(channel=channel, name=s["name"], width=s["width"], height=s["height"]))
    return result


def get_channels() -> list[str]:
    return sorted({p.channel for p in load_presets()})


def get_presets_by_channel(channel: str) -> list[SizePreset]:
    return [p for p in load_presets() if p.channel == channel]
