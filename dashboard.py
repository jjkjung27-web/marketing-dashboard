import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

DATA_DIR = Path(__file__).parent

CHANNEL_MAP = {
    "구글": "googleadwords_int",
    "메타": "Facebook Ads",
    "네이버": "naver_search",
}

st.set_page_config(page_title="마케팅 대시보드", page_icon="📊", layout="wide")

# ── 데이터 로드 & 전처리 ──────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    ch_files = sorted((DATA_DIR / "data" / "channel").glob("*_channel.csv"))
    af_files = sorted((DATA_DIR / "data" / "appsflyer").glob("*_appsflyer.csv"))
    if not ch_files:
        return None, []

    ch = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in ch_files], ignore_index=True)
    ch["일"] = pd.to_datetime(ch["일"])
    ch["미디어소스"] = ch["채널"].map(CHANNEL_MAP)

    if af_files:
        af = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in af_files], ignore_index=True)
        af["일"] = pd.to_datetime(af["일"])
        af = af.rename(columns={"클릭": "AF_클릭", "회원가입": "AF_회원가입",
                                 "구매": "AF_구매", "구매매출": "AF_구매매출"})
        df = ch.merge(af, on=["일", "미디어소스", "캠페인", "그룹", "소재"], how="left")
    else:
        df = ch.copy()

    df["CTR"]  = (df["클릭"]  / df["노출"].replace(0, float("nan")) * 100).round(2)
    df["CPC"]  = (df["비용"]  / df["클릭"].replace(0, float("nan"))).round(0)
    if "AF_구매" in df.columns:
        df["CPA"]  = (df["비용"]       / df["AF_구매"].replace(0, float("nan"))).round(0)
        df["ROAS"] = (df["AF_구매매출"] / df["비용"].replace(0, float("nan")) * 100).round(1)

    # 소재명 파싱: [포맷]_[카테고리]_[시즌]_[변형]_[버전]
    parts = df["소재"].str.split("_", expand=True).reindex(columns=range(5))
    df["소재_포맷"]    = parts[0].fillna("")
    df["소재_카테고리"] = parts[1].fillna("")
    df["소재_시즌"]    = parts[2].fillna("")
    df["소재_변형"]    = parts[3].fillna("")
    df["소재_버전"]    = parts[4].fillna("")

    return df, ch_files

df_full, loaded_files = load_data()
if df_full is None:
    st.error("채널 데이터가 없습니다. data/channel/ 폴더에 *_channel.csv 를 넣어주세요.")
    st.stop()

# ── 사이드바 ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("필터")
    date_min, date_max = df_full["일"].min(), df_full["일"].max()
    date_range = st.date_input("날짜 범위", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    sel_channel  = st.multiselect("채널",   sorted(df_full["채널"].unique()),
                                  default=sorted(df_full["채널"].unique()))
    sel_campaign = st.multiselect("캠페인", sorted(df_full["캠페인"].unique()),
                                  default=sorted(df_full["캠페인"].unique()))

    st.divider()
    st.subheader("이상치 기준")
    threshold_cpa  = st.number_input("CPA 경고 (전일 대비 +%)", value=30, min_value=1, max_value=200)
    threshold_roas = st.number_input("ROAS 경고 (전일 대비 -%)", value=20, min_value=1, max_value=100)
    st.caption("목표값 설정 (선택)")
    target_cpa  = st.number_input("목표 CPA (원, 0=미설정)", value=0, min_value=0, step=100)
    target_roas = st.number_input("목표 ROAS (%, 0=미설정)", value=0, min_value=0, step=10)

start = date_range[0] if len(date_range) >= 1 else date_min
end   = date_range[1] if len(date_range) == 2 else date_max

mask = (
    (df_full["일"] >= pd.Timestamp(start)) &
    (df_full["일"] <= pd.Timestamp(end)) &
    (df_full["채널"].isin(sel_channel) if sel_channel else True) &
    (df_full["캠페인"].isin(sel_campaign) if sel_campaign else True)
)
df = df_full[mask].copy()

# ── 헬퍼: 전일 대비 delta 계산 ────────────────────────────────────────────────

def day_agg(d: pd.DataFrame, date, group=None) -> pd.Series:
    sub = d[d["일"] == pd.Timestamp(date)]
    if group:
        sub = sub[sub["채널"] == group]
    cols = ["비용", "노출", "클릭"]
    af_cols = [c for c in ["AF_구매", "AF_구매매출"] if c in d.columns]
    agg = sub[cols + af_cols].sum()
    agg["CTR"]  = (agg["클릭"] / agg["노출"] * 100) if agg["노출"] else 0
    agg["CPC"]  = (agg["비용"] / agg["클릭"]) if agg["클릭"] else 0
    if "AF_구매" in agg:
        agg["CPA"]  = (agg["비용"] / agg["AF_구매"]) if agg["AF_구매"] else 0
        agg["ROAS"] = (agg["AF_구매매출"] / agg["비용"] * 100) if agg["비용"] else 0
    return agg

def delta_pct(new, old):
    if old == 0 or pd.isna(old):
        return None
    return round((new - old) / abs(old) * 100, 1)

def fmt_delta(pct, invert=False):
    if pct is None:
        return "—"
    good = pct > 0 if not invert else pct < 0
    arrow = "▲" if pct > 0 else "▼"
    color = "normal" if good else "inverse"
    return f"{arrow} {abs(pct):.1f}%"

# ── 이상치 감지 ───────────────────────────────────────────────────────────────

def detect_anomalies(d, latest, prev):
    alerts = []
    if prev is None:
        return alerts
    for ch in d["채널"].unique():
        cur  = day_agg(d, latest, ch)
        prv  = day_agg(d, prev,   ch)
        if "CPA" in cur and cur["CPA"] > 0 and prv["CPA"] > 0:
            chg = delta_pct(cur["CPA"], prv["CPA"])
            if chg and chg > threshold_cpa:
                alerts.append(("🔴", f"{ch} CPA ₩{cur['CPA']:,.0f} → 전일 대비 +{chg:.0f}%"))
            if target_cpa > 0 and cur["CPA"] > target_cpa:
                alerts.append(("🔴", f"{ch} CPA ₩{cur['CPA']:,.0f} → 목표(₩{target_cpa:,}) 초과"))
        if "ROAS" in cur and cur["ROAS"] > 0 and prv["ROAS"] > 0:
            chg = delta_pct(cur["ROAS"], prv["ROAS"])
            if chg and chg < -threshold_roas:
                alerts.append(("🟡", f"{ch} ROAS {cur['ROAS']:.0f}% → 전일 대비 {chg:.0f}%"))
            if target_roas > 0 and cur["ROAS"] < target_roas:
                alerts.append(("🟡", f"{ch} ROAS {cur['ROAS']:.0f}% → 목표({target_roas}%) 미달"))
        cur_ctr = day_agg(d, latest, ch)["CTR"]
        prv_ctr = day_agg(d, prev,   ch)["CTR"]
        if prv_ctr > 0:
            chg = delta_pct(cur_ctr, prv_ctr)
            if chg and chg < -20:
                alerts.append(("🟡", f"{ch} CTR {cur_ctr:.2f}% → 전일 대비 {chg:.0f}%"))
    return alerts

sorted_dates = sorted(df["일"].unique())
latest_date  = sorted_dates[-1] if sorted_dates else None
prev_date    = sorted_dates[-2] if len(sorted_dates) >= 2 else None

# ── 헤더 ─────────────────────────────────────────────────────────────────────

st.title("📊 마케팅 성과 대시보드")
st.caption(
    f"파일 {len(loaded_files)}개 로드 · 최신 날짜 {date_max.date()} · "
    "새 파일 추가 후 F5 새로고침하면 자동 반영"
)

tab1, tab2, tab3 = st.tabs(["📊 오늘 현황", "📡 채널 분석", "🎨 소재 분석"])

# ════════════════════════════════════════════════════════════════════════════
# 탭1: 오늘 현황
# ════════════════════════════════════════════════════════════════════════════
with tab1:

    # 이상치 배너
    if latest_date:
        anomalies = detect_anomalies(df, latest_date, prev_date)
        if anomalies:
            reds   = [msg for lvl, msg in anomalies if lvl == "🔴"]
            yellows = [msg for lvl, msg in anomalies if lvl == "🟡"]
            if reds:
                st.error("🔴 **이상치 감지** — " + "  |  ".join(reds))
            if yellows:
                st.warning("🟡 **주의** — " + "  |  ".join(yellows))
        else:
            st.success("✅ 이상치 없음 — 모든 지표 정상 범위")

    st.divider()

    # 전체 기간 집계
    cur  = day_agg(df, latest_date)  if latest_date else pd.Series(dtype=float)
    prv  = day_agg(df, prev_date)    if prev_date   else pd.Series(dtype=float)
    has_af = "AF_구매" in df.columns

    # KPI 카드 행1: 비용, 노출, 클릭, CTR, CPC
    c1, c2, c3, c4, c5 = st.columns(5)
    def kpi(col, label, val, pct, invert=False, flag=False):
        d = fmt_delta(pct, invert)
        color = "normal"
        if pct is not None:
            good = (pct > 0) if not invert else (pct < 0)
            color = "normal" if good else "inverse"
        col.metric(label, val, d, delta_color=color,
                   border=True if flag else False)

    d_cost  = delta_pct(cur.get("비용",0),  prv.get("비용",0))
    d_imp   = delta_pct(cur.get("노출",0),  prv.get("노출",0))
    d_click = delta_pct(cur.get("클릭",0),  prv.get("클릭",0))
    d_ctr   = delta_pct(cur.get("CTR",0),   prv.get("CTR",0))
    d_cpc   = delta_pct(cur.get("CPC",0),   prv.get("CPC",0))

    total_cost  = df["비용"].sum()
    total_imp   = df["노출"].sum()
    total_click = df["클릭"].sum()
    avg_ctr     = total_click / total_imp * 100 if total_imp else 0
    avg_cpc     = total_cost  / total_click      if total_click else 0

    c1.metric("총 비용",  f"₩{total_cost:,.0f}",  fmt_delta(d_cost,  invert=True), delta_color="inverse" if d_cost and d_cost>0 else "normal")
    c2.metric("총 노출",  f"{total_imp:,.0f}",     fmt_delta(d_imp))
    c3.metric("총 클릭",  f"{total_click:,.0f}",   fmt_delta(d_click))
    c4.metric("평균 CTR", f"{avg_ctr:.2f}%",        fmt_delta(d_ctr))
    c5.metric("평균 CPC", f"₩{avg_cpc:,.0f}",      fmt_delta(d_cpc,  invert=True), delta_color="inverse" if d_cpc and d_cpc>0 else "normal")

    # KPI 카드 행2: 구매, 매출, CPA, ROAS (AF 있을 때만)
    if has_af:
        total_purchase = df["AF_구매"].sum()
        total_revenue  = df["AF_구매매출"].sum()
        avg_cpa  = total_cost     / total_purchase if total_purchase else 0
        avg_roas = total_revenue  / total_cost * 100 if total_cost else 0

        d_pur  = delta_pct(cur.get("AF_구매",0),      prv.get("AF_구매",0))
        d_rev  = delta_pct(cur.get("AF_구매매출",0),   prv.get("AF_구매매출",0))
        d_cpa  = delta_pct(cur.get("CPA",0),           prv.get("CPA",0))
        d_roas = delta_pct(cur.get("ROAS",0),          prv.get("ROAS",0))

        cpa_flag  = (d_cpa  and d_cpa  >  threshold_cpa)  or (target_cpa  > 0 and avg_cpa  > target_cpa)
        roas_flag = (d_roas and d_roas < -threshold_roas) or (target_roas > 0 and avg_roas < target_roas)

        st.markdown("")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("총 구매",   f"{total_purchase:,.0f}건", fmt_delta(d_pur))
        r2.metric("구매 매출", f"₩{total_revenue:,.0f}",  fmt_delta(d_rev))
        r3.metric("CPA",  f"₩{avg_cpa:,.0f}",  fmt_delta(d_cpa,  invert=True),
                  delta_color="inverse" if (d_cpa and d_cpa>0) else "normal")
        r4.metric("ROAS", f"{avg_roas:.1f}%",   fmt_delta(d_roas),
                  delta_color="inverse" if (d_roas and d_roas<0) else "normal")

        if cpa_flag:
            st.caption("⚠️ CPA가 경고 기준을 초과했습니다.")
        if roas_flag:
            st.caption("⚠️ ROAS가 경고 기준 미달입니다.")

    st.divider()

    # 채널별 요약 테이블
    st.subheader("채널별 요약")

    agg_cols = {"비용": "sum", "노출": "sum", "클릭": "sum"}
    if has_af:
        agg_cols.update({"AF_구매": "sum", "AF_구매매출": "sum"})

    by_ch = df.groupby("채널").agg(**{k: (k, v) for k, v in agg_cols.items()}).reset_index()
    by_ch["CTR"] = (by_ch["클릭"] / by_ch["노출"] * 100).round(2)
    by_ch["CPC"] = (by_ch["비용"] / by_ch["클릭"]).round(0)
    if has_af:
        by_ch["CPA"]  = (by_ch["비용"] / by_ch["AF_구매"]).round(0)
        by_ch["ROAS"] = (by_ch["AF_구매매출"] / by_ch["비용"] * 100).round(1)

    # 전일 대비 ROAS delta per 채널
    if latest_date and prev_date:
        def ch_delta(ch_name, metric):
            c = day_agg(df, latest_date, ch_name)
            p = day_agg(df, prev_date,   ch_name)
            return delta_pct(c.get(metric, 0), p.get(metric, 0))

        by_ch["ROAS_delta"] = by_ch["채널"].apply(lambda c: ch_delta(c, "ROAS"))
        by_ch["CPA_delta"]  = by_ch["채널"].apply(lambda c: ch_delta(c, "CPA"))

        def signal(row):
            cpa_bad  = row.get("CPA_delta")  and row["CPA_delta"]  > threshold_cpa
            roas_bad = row.get("ROAS_delta") and row["ROAS_delta"] < -threshold_roas
            if cpa_bad or roas_bad:
                return "🔴"
            if (row.get("CPA_delta") and row["CPA_delta"] > 10) or \
               (row.get("ROAS_delta") and row["ROAS_delta"] < -10):
                return "🟡"
            return "🟢"

        by_ch["상태"] = by_ch.apply(signal, axis=1)
        display_cols = ["채널", "비용", "CTR", "CPC"]
        if has_af:
            display_cols += ["CPA", "ROAS", "CPA_delta", "ROAS_delta", "상태"]
    else:
        display_cols = ["채널", "비용", "CTR", "CPC"] + (["CPA", "ROAS"] if has_af else [])

    show = by_ch[display_cols].copy()
    if "비용" in show.columns:
        show["비용"] = show["비용"].apply(lambda x: f"₩{x:,.0f}")
    if "CPC" in show.columns:
        show["CPC"]  = show["CPC"].apply(lambda x: f"₩{x:,.0f}")
    if "CPA" in show.columns:
        show["CPA"]  = show["CPA"].apply(lambda x: f"₩{x:,.0f}")
    if "CTR" in show.columns:
        show["CTR"]  = show["CTR"].apply(lambda x: f"{x:.2f}%")
    if "ROAS" in show.columns:
        show["ROAS"] = show["ROAS"].apply(lambda x: f"{x:.1f}%")
    if "CPA_delta" in show.columns:
        show["CPA_delta"]  = show["CPA_delta"].apply(
            lambda x: f"▲{x:.1f}%" if (x and x>0) else (f"▼{abs(x):.1f}%" if x else "—"))
    if "ROAS_delta" in show.columns:
        show["ROAS_delta"] = show["ROAS_delta"].apply(
            lambda x: f"▲{x:.1f}%" if (x and x>0) else (f"▼{abs(x):.1f}%" if x else "—"))

    st.dataframe(show, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# 탭2: 채널 분석
# ════════════════════════════════════════════════════════════════════════════
with tab2:

    sel_ch2 = st.selectbox("채널 선택", sorted(df["채널"].unique()), key="tab2_ch")
    df2 = df[df["채널"] == sel_ch2]

    df2 = df2.copy()
    df2["날짜"] = df2["일"].dt.strftime("%Y-%m-%d")
    daily = df2.groupby("날짜").agg(비용=("비용","sum"), 노출=("노출","sum"), 클릭=("클릭","sum")).reset_index()
    daily["CTR"] = (daily["클릭"] / daily["노출"] * 100).round(2)
    daily["CPC"] = (daily["비용"] / daily["클릭"]).round(0)

    t1, t2, t3 = st.tabs(["비용", "노출 / 클릭", "CTR / CPC"])
    with t1:
        fig = px.bar(daily, x="날짜", y="비용", color_discrete_sequence=["#5C7AEA"])
        fig.update_layout(margin=dict(t=20, b=20), xaxis_type="category")
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        fig = go.Figure()
        fig.add_bar(x=daily["날짜"], y=daily["노출"], name="노출", marker_color="#B8CFE8")
        fig.add_scatter(x=daily["날짜"], y=daily["클릭"], name="클릭", yaxis="y2",
                        mode="lines+markers", marker_color="#E84855")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right"),
                          xaxis_type="category",
                          margin=dict(t=20,b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
    with t3:
        fig = go.Figure()
        fig.add_scatter(x=daily["날짜"], y=daily["CTR"], name="CTR (%)",
                        mode="lines+markers", marker_color="#5C7AEA")
        fig.add_scatter(x=daily["날짜"], y=daily["CPC"], name="CPC (₩)", yaxis="y2",
                        mode="lines+markers", marker_color="#F4A261")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right"),
                          xaxis_type="category",
                          margin=dict(t=20,b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("캠페인 드릴다운")

    grp_cols = ["캠페인", "그룹"]
    agg2 = {"비용": ("비용","sum"), "노출": ("노출","sum"), "클릭": ("클릭","sum")}
    if "AF_구매" in df2.columns:
        agg2.update({"AF_구매": ("AF_구매","sum"), "AF_구매매출": ("AF_구매매출","sum")})

    by_cmp = df2.groupby(grp_cols).agg(**agg2).reset_index()
    by_cmp["CTR"] = (by_cmp["클릭"] / by_cmp["노출"] * 100).round(2)
    by_cmp["CPC"] = (by_cmp["비용"] / by_cmp["클릭"]).round(0)
    if "AF_구매" in by_cmp.columns:
        by_cmp["CPA"]  = (by_cmp["비용"] / by_cmp["AF_구매"]).round(0)
        by_cmp["ROAS"] = (by_cmp["AF_구매매출"] / by_cmp["비용"] * 100).round(1)

    sort2 = st.selectbox("정렬 기준", ["비용","클릭","CTR","CPC"] +
                         (["CPA","ROAS"] if "AF_구매" in by_cmp.columns else []), key="sort2")
    st.dataframe(by_cmp.sort_values(sort2, ascending=(sort2 in ["CPC","CPA"])),
                 use_container_width=True, height=380, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# 탭3: 소재 분석
# ════════════════════════════════════════════════════════════════════════════
with tab3:

    has_af3 = "AF_구매" in df.columns

    # ── 섹션1: 포맷별 성과 ──────────────────────────────────────────────────
    st.subheader("포맷별 성과 (VID / IMG / CRS / TXT)")

    agg3 = {"비용": ("비용","sum"), "노출": ("노출","sum"), "클릭": ("클릭","sum")}
    if has_af3:
        agg3.update({"AF_구매": ("AF_구매","sum"), "AF_구매매출": ("AF_구매매출","sum")})

    by_fmt = df[df["소재_포맷"] != ""].groupby("소재_포맷").agg(**agg3).reset_index()
    by_fmt["CTR"] = (by_fmt["클릭"] / by_fmt["노출"] * 100).round(2)
    by_fmt["CPC"] = (by_fmt["비용"] / by_fmt["클릭"]).round(0)
    if has_af3:
        by_fmt["CPA"]  = (by_fmt["비용"] / by_fmt["AF_구매"]).round(0)
        by_fmt["ROAS"] = (by_fmt["AF_구매매출"] / by_fmt["비용"] * 100).round(1)

    fmt_metric = st.radio("지표 선택", ["CTR", "CPC"] + (["CPA", "ROAS"] if has_af3 else []),
                          horizontal=True, key="fmt_metric")
    invert_fmt = fmt_metric in ["CPA", "CPC"]
    fig_fmt = px.bar(
        by_fmt.sort_values(fmt_metric, ascending=invert_fmt),
        x="소재_포맷", y=fmt_metric, color="소재_포맷", text=fmt_metric,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_fmt.update_traces(textposition="outside")
    fig_fmt.update_layout(showlegend=False, margin=dict(t=20,b=20))
    st.plotly_chart(fig_fmt, use_container_width=True)

    st.divider()

    # ── 섹션2: A/B 테스트 결과 ──────────────────────────────────────────────
    st.subheader("A/B 테스트 결과")

    ab_df = df[df["소재_변형"].isin(["A","B"])].copy()
    if ab_df.empty:
        st.info("A/B 변형 소재 데이터가 없습니다.")
    else:
        ab_metric = st.radio("비교 지표", ["CTR", "CPC"] + (["CPA","ROAS"] if has_af3 else []),
                             horizontal=True, key="ab_metric")

        agg_ab = {"비용": ("비용","sum"), "노출": ("노출","sum"), "클릭": ("클릭","sum")}
        if has_af3:
            agg_ab.update({"AF_구매": ("AF_구매","sum"), "AF_구매매출": ("AF_구매매출","sum")})

        group_key = ["소재_포맷", "소재_카테고리", "소재_시즌", "소재_버전", "소재_변형"]
        ab_agg = ab_df.groupby(group_key).agg(**agg_ab).reset_index()
        ab_agg["CTR"] = (ab_agg["클릭"] / ab_agg["노출"] * 100).round(2)
        ab_agg["CPC"] = (ab_agg["비용"] / ab_agg["클릭"]).round(0)
        if has_af3:
            ab_agg["CPA"]  = (ab_agg["비용"] / ab_agg["AF_구매"]).round(0)
            ab_agg["ROAS"] = (ab_agg["AF_구매매출"] / ab_agg["비용"] * 100).round(1)

        # 피벗: A vs B 나란히
        pivot_cols = ["소재_포맷", "소재_카테고리", "소재_시즌", "소재_버전"]
        pivot = ab_agg.pivot_table(index=pivot_cols, columns="소재_변형",
                                   values=ab_metric, aggfunc="mean").reset_index()
        pivot.columns.name = None

        if "A" in pivot.columns and "B" in pivot.columns:
            lower_is_better = ab_metric in ["CPA", "CPC"]
            def winner(row):
                a, b = row.get("A"), row.get("B")
                if pd.isna(a) or pd.isna(b):
                    return "—"
                if lower_is_better:
                    return "🏆 A" if a < b else "🏆 B"
                return "🏆 A" if a > b else "🏆 B"
            pivot["승자"] = pivot.apply(winner, axis=1)

            # 소재명 라벨
            pivot["소재"] = (pivot["소재_포맷"] + "_" + pivot["소재_카테고리"] +
                             "_" + pivot["소재_시즌"] + "_" + pivot["소재_버전"])

            # 차트
            fig_ab = go.Figure()
            fig_ab.add_bar(name="A (기존)", x=pivot["소재"], y=pivot["A"],
                           marker_color="#5C7AEA", text=pivot["A"].round(1),
                           textposition="outside")
            fig_ab.add_bar(name="B (테스트)", x=pivot["소재"], y=pivot["B"],
                           marker_color="#F4A261", text=pivot["B"].round(1),
                           textposition="outside")
            fig_ab.update_layout(
                barmode="group", margin=dict(t=20,b=60),
                legend=dict(orientation="h"),
                xaxis_tickangle=-30,
            )
            st.plotly_chart(fig_ab, use_container_width=True)

            # 결과 테이블
            show_cols = ["소재", "A", "B", "승자"]
            st.dataframe(pivot[show_cols].rename(columns={"A": f"A_{ab_metric}", "B": f"B_{ab_metric}"}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("A와 B 변형이 모두 있는 소재가 없습니다.")

    st.divider()

    # 원본 데이터 (접기)
    with st.expander("📄 전체 소재 원본 데이터"):
        st.dataframe(df, use_container_width=True, height=350)
        st.download_button("CSV 다운로드",
                           data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                           file_name="joined_full.csv", mime="text/csv")
