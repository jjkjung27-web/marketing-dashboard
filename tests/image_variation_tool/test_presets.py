import pytest
from image_variation_tool.core.presets import load_presets, get_channels, get_presets_by_channel


def test_load_presets_returns_all_channels():
    presets = load_presets()
    channels = {p.channel for p in presets}
    assert channels == {"구글", "메타", "카카오", "네이버 GFA", "SNS"}


def test_load_presets_naver_gfa_has_4_sizes():
    presets = load_presets()
    naver = [p for p in presets if p.channel == "네이버 GFA"]
    assert len(naver) == 4


def test_get_channels_returns_sorted_list():
    channels = get_channels()
    assert isinstance(channels, list)
    assert "네이버 GFA" in channels


def test_get_presets_by_channel_filters_correctly():
    presets = get_presets_by_channel("메타")
    assert all(p.channel == "메타" for p in presets)
    assert len(presets) == 3


def test_preset_label_format():
    presets = get_presets_by_channel("메타")
    feed = next(p for p in presets if p.name == "피드 (정사각형)")
    assert feed.label == "피드 (정사각형) (1080×1080)"
