import requests
import pandas as pd


def fetch_meta_spend(access_token: str, ad_account_id: str, date: str) -> pd.DataFrame:
    """Meta Marketing API에서 캠페인+adset별 당일 소진액(KRW) 조회."""
    url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}/insights"
    params = {
        "access_token": access_token,
        "time_range": f'{{"since":"{date}","until":"{date}"}}',
        "level": "adset",
        "fields": "campaign_name,adset_name,spend",
        "limit": 500,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL에 파라미터 포함됨

    if not rows:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    df = pd.DataFrame(rows)
    df["매체"] = "Meta"
    df = df.rename(columns={"campaign_name": "캠페인", "adset_name": "그룹", "spend": "api_소진"})
    df["api_소진"] = pd.to_numeric(df["api_소진"]).astype(int)
    return df[["매체", "캠페인", "그룹", "api_소진"]]
