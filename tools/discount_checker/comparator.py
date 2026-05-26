from dataclasses import dataclass


@dataclass
class AdRow:
    ad_name: str
    uids: list[str]


@dataclass
class CompareResult:
    ad_name: str
    creative_discount: int | None
    representative_uid: str | None
    actual_max_discount: int | None
    diff: int | None
    status: str  # "일치" | "불일치" | "조회실패" | "추출불가" | "스크래핑실패"


def compare(
    ad_name: str,
    creative_discount: int | None,
    uid_discounts: dict[str, int | None],
) -> CompareResult:
    if creative_discount is None:
        return CompareResult(ad_name, None, None, None, None, "추출불가")

    valid = {uid: rate for uid, rate in uid_discounts.items() if rate is not None}
    if not valid:
        return CompareResult(ad_name, creative_discount, None, None, None, "스크래핑실패")

    rep_uid = max(valid, key=lambda u: valid[u])
    actual_max = valid[rep_uid]
    diff = creative_discount - actual_max
    status = "일치" if diff == 0 else "불일치"
    return CompareResult(ad_name, creative_discount, rep_uid, actual_max, diff, status)
