import sys
import io
import os

# Streamlit Cloud에서 repo root를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from PIL import Image
from dotenv import load_dotenv

from image_variation_tool.core.presets import load_presets, get_channels, get_presets_by_channel
from image_variation_tool.core.analyzer import analyze_image
from image_variation_tool.core.layout_engine import generate_variation
from image_variation_tool.core.exporter import export_to_bytes, create_zip, ExportFormat
from image_variation_tool.core.models import SizePreset

load_dotenv()

st.set_page_config(page_title="이미지 배리에이션 툴", layout="wide")
st.title("이미지 배리에이션 툴")

# ── 사이드바: 입력 ──────────────────────────────────────────
with st.sidebar:
    st.header("1. 원본 이미지")
    original_file = st.file_uploader("시안 이미지 업로드", type=["png", "jpg", "jpeg"])

    st.header("2. 가이드 파일 (선택)")
    guide_file = st.file_uploader("가이드 업로드 (PNG/JPG/PDF)", type=["png", "jpg", "jpeg", "pdf"])

    st.header("3. 목표 사이즈 선택")
    channels = get_channels()
    selected_channels = st.multiselect("매체 선택", channels, default=["메타"])

    custom_sizes = st.text_area(
        "직접 입력 (선택, 한 줄에 하나: 이름,가로,세로)",
        placeholder="예: 커스텀_배너,640,100",
    )

    # API Key: Streamlit Secrets → 환경변수 → 사용자 입력 순으로 확인
    _secret_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    _env_key = os.getenv("GEMINI_API_KEY", "")
    _auto_key = _secret_key or _env_key

    if _auto_key:
        api_key = _auto_key
        st.success("API Key 연결됨 ✓", icon="🔑")
    else:
        api_key = st.text_input("Gemini API Key", type="password")

    if api_key and st.button("사용 가능한 모델 확인", type="secondary"):
        import requests as _req
        r = _req.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
            timeout=10,
        )
        if r.ok:
            names = [m["name"] for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
            st.info("사용 가능한 모델:\n" + "\n".join(names))
        else:
            st.error(f"모델 조회 실패: {r.text[:200]}")

    analyze_btn = st.button("분석 시작", type="primary", disabled=not original_file or not api_key)

# ── 메인 영역 ──────────────────────────────────────────────
if original_file:
    original_bytes = original_file.read()
    st.session_state["original_bytes"] = original_bytes
    st.session_state["original_mime"] = original_file.type
    original_image = Image.open(io.BytesIO(original_bytes)).convert("RGB")
    st.session_state["original_image_preview"] = original_image

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("원본 이미지")
        st.image(original_image, use_container_width=True)

    # 목표 사이즈 목록 수집
    target_presets = []
    for ch in selected_channels:
        target_presets.extend(get_presets_by_channel(ch))

    for line in custom_sizes.strip().splitlines():
        parts = line.strip().split(",")
        if len(parts) == 3:
            try:
                target_presets.append(SizePreset("커스텀", parts[0].strip(), int(parts[1]), int(parts[2])))
            except ValueError:
                st.warning(f"올바르지 않은 커스텀 사이즈: {line}")

    with col2:
        st.subheader("선택된 사이즈")
        if target_presets:
            for p in target_presets:
                st.write(f"- **{p.channel}** {p.label}")
        else:
            st.info("매체를 선택하거나 직접 사이즈를 입력하세요.")

if analyze_btn and api_key and "original_bytes" in st.session_state:
    with st.spinner("Gemini Vision으로 이미지 분석 중..."):
        original_bytes = st.session_state["original_bytes"]
        original_mime = st.session_state["original_mime"]
        guide_bytes = guide_file.read() if guide_file else None
        guide_mime = guide_file.type if guide_file else None

        try:
            analysis = analyze_image(
                image_bytes=original_bytes,
                api_key=api_key,
                image_mime=original_mime,
                guide_bytes=guide_bytes,
                guide_mime=guide_mime,
            )
            st.session_state["analysis"] = analysis
            st.session_state["original_image"] = st.session_state["original_image_preview"]
            st.session_state["target_presets"] = target_presets
        except Exception as e:
            st.error(f"분석 실패: {e}")

if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]

    st.divider()
    st.subheader("분석 결과 확인")

    with st.expander("감지된 요소 목록"):
        for el in analysis.elements:
            st.write(f"- **{el.name}** | 위치: ({el.x:.2f}, {el.y:.2f}) | 크기: {el.width:.2f}×{el.height:.2f} | 우선순위: {el.priority}")
        st.write(f"배경색: {analysis.background_color}")
        st.write(f"색상 팔레트: {', '.join(analysis.color_palette)}")

    presets = st.session_state["target_presets"]
    original_image = st.session_state["original_image"]

    st.subheader("배리에이션 미리보기")
    cols = st.columns(min(4, len(presets)) if presets else 1)

    variations = {}
    for i, preset in enumerate(presets):
        variation = generate_variation(original_image, analysis, preset.width, preset.height)
        variations[i] = variation
        col = cols[i % len(cols)]
        with col:
            st.image(variation, caption=preset.label, use_container_width=True)
            st.checkbox(f"{preset.label} 제외", key=f"exclude_{i}")

    st.session_state["variations"] = variations

    # Read actual checkbox states from session_state
    exclude_keys = [
        i for i in range(len(presets))
        if st.session_state.get(f"exclude_{i}", False)
    ]

    st.divider()
    st.subheader("다운로드")

    fmt_choice = st.radio("내보내기 형식", ["PNG", "JPG", "SVG (Figma 호환)"], horizontal=True)
    fmt_map = {"PNG": ExportFormat.PNG, "JPG": ExportFormat.JPG, "SVG (Figma 호환)": ExportFormat.SVG}
    export_fmt = fmt_map[fmt_choice]
    ext = export_fmt.value.lower() if export_fmt != ExportFormat.SVG else "svg"

    if st.button("ZIP 생성 및 다운로드", type="primary"):
        cached_variations = st.session_state.get("variations", {})
        files = {}
        for i, preset in enumerate(presets):
            if i in exclude_keys:
                continue
            variation = cached_variations.get(i) or generate_variation(original_image, analysis, preset.width, preset.height)
            filename = f"{preset.channel}_{preset.name}_{preset.width}x{preset.height}.{ext}"
            files[filename] = export_to_bytes(variation, export_fmt)

        zip_bytes = create_zip(files)
        st.download_button(
            label=f"ZIP 다운로드 ({len(files)}개 파일)",
            data=zip_bytes,
            file_name="variations.zip",
            mime="application/zip",
        )
