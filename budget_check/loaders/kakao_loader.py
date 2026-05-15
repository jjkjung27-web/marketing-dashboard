import requests
import pandas as pd


def fetch_kakao_spend(access_token: str, ad_account_id: str, date: str) -> pd.DataFrame:
    """카카오 모먼트 API에서 캠페인+그룹별 당일 소진액(KRW) 조회."""
    url = f"https://apis.moment.kakao.com/openapi/v4/adAccounts/{ad_account_id}/adGroups/stats"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params = {
        "metricsGroups": "BASIC_PERFORMANCE",
        "startDate": date,
        "endDate": date,
        "dimensionGroups": "CAMPAIGN,AD_GROUP",
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    data = resp.json().get("data", [])

    if not data:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    rows = [
        {
            "매체": "Kakao",
            "캠페인": item["dimensions"]["campaignName"],
            "그룹": item["dimensions"]["adGroupName"],
            "api_소진": int(item["metrics"]["cost"]),
        }
        for item in data
    ]
    return pd.DataFrame(rows)[["매체", "캠페인", "그룹", "api_소진"]]
