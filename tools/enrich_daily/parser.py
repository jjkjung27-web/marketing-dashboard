import re

PARSED_COLS = ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
_CHANNEL_RE = re.compile(r"^\[([^\]]+)\](.*)")


def parse_campaign_name(name: str) -> dict[str, str]:
    """캠페인명에서 6개 컬럼 추출. 파싱 불가 시 빈 dict 반환."""
    parts = name.split("_")
    if len(parts) < 6:
        return {}

    channel_event = parts[2]
    ch_match = _CHANNEL_RE.match(channel_event)

    return {
        "brand": parts[1].strip(),
        "판매채널": ch_match.group(1).strip() if ch_match else "",
        "기획전명": ch_match.group(2).strip() if ch_match else channel_event.strip(),
        "광고목표": parts[3].strip(),
        "소재유형": parts[4].strip(),
        "타겟구분": "_".join(parts[5:]).strip(),
    }
