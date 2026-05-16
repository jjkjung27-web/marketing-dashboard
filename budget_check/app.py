import streamlit as st
import pandas as pd
from loaders.rd_loader import load_rd
from loaders.meta_loader import fetch_meta_spend
from loaders.kakao_loader import fetch_kakao_spend
from loaders.sheets_loader import load_budget_plan
from logic.validator import validate_rd_vs_api
from logic.budget_checker import check_budget
from slack_sender import format_message, send_to_slack

st.set_page_config(page_title="예산 점검", page_icon="📊", layout="wide")
st.title("📊 예산 점검")

# ── 입력 영역 ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2])
with col1:
    selected_date = st.date_input("날짜").strftime("%Y-%m-%d")
    rd_file = st.file_uploader("RD 파일 업로드 (엑스퍼트 CSV)", type=["csv"])

with col2:
    sheets_url = st.text_input(
        "예산 플랜 Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
    )

run = st.button("🔍 조회", type="primary", disabled=(rd_file is None or not sheets_url))

if not run:
    st.stop()

# ── 데이터 수집 ────────────────────────────────────────────────────────────────
meta_token = st.secrets["META_ACCESS_TOKEN"]
meta_account = st.secrets["META_AD_ACCOUNT_ID"]
kakao_token = st.secrets["KAKAO_ACCESS_TOKEN"]
kakao_account = st.secrets["KAKAO_AD_ACCOUNT_ID"]

with st.spinner("데이터 수집 중..."):
    rd_df = load_rd(rd_file, date=selected_date)

    try:
        meta_df = fetch_meta_spend(meta_token, meta_account, selected_date)
    except Exception as e:
        st.warning(f"Meta API 오류: {e}")
        meta_df = pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    try:
        kakao_df = fetch_kakao_spend(kakao_token, kakao_account, selected_date)
    except Exception as e:
        st.warning(f"카카오 API 오류: {e}")
        kakao_df = pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    try:
        plan_df = load_budget_plan(sheets_url, date=selected_date)
    except Exception as e:
        st.error(f"예산 시트 로드 실패: {e}")
        st.stop()

# Meta 소진에 VAT+수수료 1.079 적용
if not meta_df.empty:
    meta_df["api_소진"] = (meta_df["api_소진"] * 1.079).round().astype(int)

api_df = pd.concat([meta_df, kakao_df], ignore_index=True)

with st.expander("🔍 데이터 수집 결과 (진단용)", expanded=False):
    st.write(f"RD: {len(rd_df)}행 | Meta API: {len(meta_df)}행 | Kakao API: {len(kakao_df)}행 | 예산 플랜: {len(plan_df)}행")
    if not meta_df.empty:
        st.dataframe(meta_df.head(5))
    else:
        st.warning(f"Meta API가 {selected_date} 기준 0행을 반환했습니다. 날짜/토큰/계정ID를 확인하세요.")

# ── 비교 계산 ──────────────────────────────────────────────────────────────────
validation_df = validate_rd_vs_api(rd_df, api_df)
budget_df = check_budget(api_df, plan_df)

# ── 테이블 표시 ────────────────────────────────────────────────────────────────
NUM_COLS_VAL = ["rd_소진", "api_소진", "차이"]
NUM_COLS_BUD = ["일예산", "소진", "차이"]

st.subheader("① RD vs 매체 API 검증")
st.dataframe(
    validation_df.style
    .map(lambda v: "color: red" if v == "🔴 불일치" else "", subset=["상태"])
    .format("{:,.0f}", subset=NUM_COLS_VAL),
    use_container_width=True,
    hide_index=True,
)

st.subheader("② 예산 플랜 대비")

def _color_status(val):
    if val == "🔴 미소진":
        return "background-color: #ffd7d7"
    if val == "🟡 과소진":
        return "background-color: #fff3cd"
    return ""

st.dataframe(
    budget_df.style
    .map(_color_status, subset=["상태"])
    .format("{:,.0f}", subset=NUM_COLS_BUD),
    use_container_width=True,
    hide_index=True,
)

col_a, col_b, col_c = st.columns(3)
col_a.metric("전체 예산", f"{budget_df['일예산'].sum():,.0f}원")
col_b.metric("전체 소진", f"{budget_df['소진'].sum():,.0f}원")
total_diff = budget_df['소진'].sum() - budget_df['일예산'].sum()
col_c.metric("차이", f"{total_diff:+,.0f}원", delta_color="inverse")

# ── 슬랙 발송 ──────────────────────────────────────────────────────────────────
st.divider()
if st.button("📤 슬랙으로 발송"):
    message = format_message(selected_date, validation_df, budget_df)
    try:
        send_to_slack(st.secrets["SLACK_WEBHOOK_URL"], message)
        st.success("슬랙 발송 완료!")
    except Exception as e:
        st.error(f"슬랙 발송 실패: {e}")
