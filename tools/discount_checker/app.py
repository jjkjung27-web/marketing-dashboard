import sys
from pathlib import Path

# Streamlit Cloud에서 repo 루트가 sys.path에 없을 수 있어 명시적으로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st

from tools.discount_checker import config
from tools.discount_checker.cache import Cache
from tools.discount_checker.comparator import CompareResult, compare
from tools.discount_checker.image_analyzer import ImageAnalyzer
from tools.discount_checker.meta_client import MetaClient
from tools.discount_checker.product_scraper import ProductScraper
from tools.discount_checker.reporter import send_slack, write_csv
from tools.discount_checker.sheet_reader import read_ad_rows

st.set_page_config(page_title="할인율 검수", page_icon="🔍", layout="wide")
st.title("🔍 광고 소재 할인율 검수")

# ── 입력 영역 ──────────────────────────────────────────────────────────────────
with st.form("input_form"):
    sheet_url = st.text_input(
        "소재관리 시트 URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
    )
    col1, col2 = st.columns(2)
    with col1:
        ad_col = st.text_input("광고명 컬럼", value="광고명")
    with col2:
        uid_col = st.text_input("UID 컬럼", value="UID")
    submitted = st.form_submit_button(
        "🔍 검수 시작", type="primary", disabled=not sheet_url
    )

# ── 파이프라인 실행 ─────────────────────────────────────────────────────────────
if submitted:
    cache = Cache(config.CACHE_PATH)
    meta = MetaClient(config.META_ACCESS_TOKEN, config.META_AD_ACCOUNT_ID)
    analyzer = ImageAnalyzer(config.ANTHROPIC_API_KEY, cache)
    scraper = ProductScraper(cache)

    with st.spinner("시트 읽는 중..."):
        try:
            ad_rows = read_ad_rows(sheet_url, ad_col=ad_col, uid_col=uid_col)
        except Exception as e:
            st.error(f"시트 읽기 실패: {e}")
            st.stop()

    results: list[CompareResult] = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, row in enumerate(ad_rows):
        status_text.text(f"처리 중 ({i + 1}/{len(ad_rows)}): {row.ad_name}")
        try:
            creative = meta.get_creative(row.ad_name)
            if creative is None:
                results.append(CompareResult(row.ad_name, None, None, None, None, "조회실패"))
            else:
                creative_id, image_url = creative
                creative_discount = analyzer.extract_discount(creative_id, image_url)
                uid_discounts = scraper.get_max_discount(row.uids)
                results.append(compare(row.ad_name, creative_discount, uid_discounts))
        except Exception as e:
            results.append(CompareResult(row.ad_name, None, None, None, None, "조회실패"))
            st.warning(f"오류 ({row.ad_name}): {e}")
        progress_bar.progress((i + 1) / len(ad_rows))

    status_text.empty()
    progress_bar.empty()

    csv_path = write_csv(results, config.OUTPUT_DIR)
    st.session_state["results"] = results
    st.session_state["csv_bytes"] = csv_path.read_bytes()
    st.session_state["csv_name"] = csv_path.name

# ── 결과 표시 ──────────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.stop()

results: list[CompareResult] = st.session_state["results"]

df = pd.DataFrame([
    {
        "광고명": r.ad_name,
        "소재_할인율": r.creative_discount,
        "대표_UID": r.representative_uid,
        "실제_최대_할인율": r.actual_max_discount,
        "오차": r.diff,
        "상태": r.status,
    }
    for r in results
])

total = len(results)
match_cnt = sum(1 for r in results if r.status == "일치")
mismatch_cnt = sum(1 for r in results if r.status == "불일치")
error_cnt = total - match_cnt - mismatch_cnt

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체", total)
c2.metric("일치 ✅", match_cnt)
c3.metric("불일치 🔴", mismatch_cnt)
c4.metric("오류", error_cnt)


def _color_status(val: str) -> str:
    if val == "불일치":
        return "background-color: #ffd7d7"
    if val == "일치":
        return "background-color: #d4edda"
    if val != "":
        return "background-color: #fff3cd"
    return ""


st.dataframe(
    df.style.map(_color_status, subset=["상태"]),
    use_container_width=True,
    hide_index=True,
)

# ── 하단 액션 ──────────────────────────────────────────────────────────────────
st.divider()
col_dl, col_slack = st.columns(2)

with col_dl:
    st.download_button(
        "📥 CSV 다운로드",
        data=st.session_state["csv_bytes"],
        file_name=st.session_state["csv_name"],
        mime="text/csv",
    )

with col_slack:
    if st.button("📤 Slack 발송 (불일치 건만)"):
        if not config.SLACK_WEBHOOK_URL:
            st.warning(".env에 SLACK_WEBHOOK_URL을 설정해주세요.")
        else:
            try:
                send_slack(results, config.SLACK_WEBHOOK_URL)
                st.success(f"Slack 발송 완료! ({mismatch_cnt}건)")
            except Exception as e:
                st.error(f"Slack 발송 실패: {e}")
