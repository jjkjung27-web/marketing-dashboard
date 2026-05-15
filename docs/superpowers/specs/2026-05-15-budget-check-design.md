# 예산 점검 자동화 — 설계 스펙

## 목적

매체 집행 데이터와 엑스퍼트 RD 리포트, 예산 플랜 시트를 자동으로 비교해 과소진/미소진을 즉시 확인하고 슬랙으로 공유하는 팀 공용 툴.

## 확정 사항

| 항목 | 결정 |
|------|------|
| 비교 단위 | 매체 + 캠페인 + 그룹 레벨 |
| 예산 관리 단위 | 일별 예산 (daily budget) |
| RD 파일 입력 | Streamlit 파일 업로드 위젯 |
| 매체 데이터 | Meta API + 카카오 API 자동 수집 |
| 예산 플랜 입력 | Google Sheets URL 직접 입력 (공개 링크 CSV 변환) |
| 슬랙 발송 | 수동 트리거 (결과 확인 후 버튼 클릭) |
| 배포 | Streamlit Community Cloud (GitHub 연동) |
| 팀 접근 | URL 공유, API 키는 서버 Secrets에 한 번만 등록 |

---

## 아키텍처

### 전체 흐름

```
팀원 (브라우저)
    │  Streamlit Community Cloud URL 접속
    ▼
app.py
    ├── [1] 날짜 선택 + RD 파일 업로드 + Google Sheets URL 입력
    ├── [2] 데이터 수집 (조회 버튼 클릭 시)
    │         ├── rd_loader.py       : 업로드 CSV 파싱 → 매체+캠페인+그룹별 소진액 집계
    │         ├── meta_loader.py     : Meta Marketing API → 캠페인+그룹별 소진액
    │         ├── kakao_loader.py    : 카카오 모먼트 API → 캠페인+그룹별 소진액
    │         └── sheets_loader.py  : Sheets URL → CSV export → 일별 예산 플랜
    ├── [3] 비교 계산
    │         ├── validator.py       : RD 소진 vs 매체 API 소진 (정합성 검증)
    │         └── budget_checker.py : 매체 API 소진 vs 예산 플랜 (과소진/미소진)
    └── [4] 결과 테이블 표시 → [슬랙 발송] 버튼 → slack_sender.py
```

### 파일 구조

```
budget_check/
├── app.py
├── loaders/
│   ├── rd_loader.py
│   ├── meta_loader.py
│   ├── kakao_loader.py
│   └── sheets_loader.py
├── logic/
│   ├── validator.py
│   └── budget_checker.py
├── slack_sender.py
├── requirements.txt
└── .streamlit/
    └── secrets.toml        # git 제외
```

---

## 데이터 명세

### RD 파일 (엑스퍼트 CSV)

- 경로: 드롭박스 로컬 동기화 폴더에서 수동 업로드
- 파일명 패턴: `musinsa_Total_YYYYMMDD~YYYY-MM-DD.csv`
- 인코딩: utf-8-sig
- 사용 컬럼: `일`, `매체`, `캠페인 이름`, `광고 그룹 이름`, `비용 (KRW)`
- 집계 기준: 선택한 날짜 기준 필터 후 매체+캠페인+그룹 합산

### 매체 API 수집

**Meta Marketing API**
- 엔드포인트: `GET /v19.0/act_{AD_ACCOUNT_ID}/insights`
- 파라미터: `time_range`, `level=adset`, `fields=campaign_name,adset_name,spend`
- 집계: 캠페인+그룹(adset)별 spend 합산

**카카오 모먼트 API**
- 엔드포인트: `GET /openapi/v4/adAccounts/{adAccountId}/adGroups/stats`
- 파라미터: `metricsGroups=BASIC_PERFORMANCE`, `datePreset` 또는 `startDate/endDate`
- 집계: 캠페인+그룹별 spend 합산

### Google Sheets 예산 플랜

- 입력: 앱 UI에서 Google Sheets URL 붙여넣기
- 조건: 시트가 "링크 있는 사람 보기" 공개 설정
- 변환: `https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}`
- 필수 컬럼: `날짜`, `매체`, `캠페인`, `그룹`, `일예산`

---

## 비교 로직

### ① RD vs 매체 API 검증

```
조인 키: 날짜 + 매체 + 캠페인 + 그룹
차이 = RD 소진 - API 소진
표시 기준:
  - 차이 = 0          → ✅ 일치
  - |차이| ≤ 1%       → 🟢 허용 오차
  - |차이| > 1%       → 🔴 불일치 (확인 필요)
```

### ② 매체 API 소진 vs 예산 플랜

```
조인 키: 날짜 + 매체 + 캠페인 + 그룹
차이 = 소진 - 일예산
상태:
  - 차이 > 0          → 🟡 과소진
  - 차이 < -10%       → 🔴 미소진
  - -10% ≤ 차이 ≤ 0  → 🟢 정상
```

---

## UI 명세

```
┌──────────────────────────────────────────────────────┐
│  📊 예산 점검                                          │
│                                                      │
│  날짜: [2026-05-15]   RD 파일: [파일 선택 📎]          │
│  예산 시트 URL: [https://docs.google.com/...]  [조회] │
├──────────────────────────────────────────────────────┤
│  ① RD vs 매체 검증                                    │
│  매체   캠페인      그룹    RD소진     API소진    차이  │
│  Meta   캠페인A    그룹1   1,000,000   998,000  -2,000│
│  Kakao  캠페인B    그룹2     500,000   500,000       0│
├──────────────────────────────────────────────────────┤
│  ② 예산 플랜 대비                                      │
│  매체   캠페인   그룹   일예산     소진      차이    상태│
│  Meta   캠페인A  그룹1  1,200,000   998,000  -202,000 🔴│
│  Kakao  캠페인B  그룹2    400,000   500,000  +100,000 🟡│
│                                                      │
│  전체: 예산 1,600,000 / 소진 1,498,000 / 차이 -102,000│
├──────────────────────────────────────────────────────┤
│  [📤 슬랙으로 발송]                                    │
└──────────────────────────────────────────────────────┘
```

---

## 슬랙 메시지 포맷

```
📊 *예산 점검 | 2026-05-15*

*✅ RD vs 매체 검증*
• Meta / 캠페인A / 그룹1: RD 1,000,000 vs API 998,000 (△-2,000)
• Kakao / 캠페인B / 그룹2: 일치 ✓

*🟡 과소진*
• Kakao / 캠페인B / 그룹2: 예산 400,000 → 소진 500,000 (+100,000)

*🔴 미소진*
• Meta / 캠페인A / 그룹1: 예산 1,200,000 → 소진 998,000 (-202,000)

*전체: 예산 1,600,000 / 소진 1,498,000 / 차이 -102,000*
```

---

## Secrets (Streamlit Community Cloud 등록)

```toml
META_ACCESS_TOKEN = ""
META_AD_ACCOUNT_ID = ""
KAKAO_ACCESS_TOKEN = ""
KAKAO_AD_ACCOUNT_ID = ""
SLACK_WEBHOOK_URL = ""
```

Google Sheets URL과 RD 파일은 앱 UI에서 입력 → Secrets 불필요.

---

## 배포 절차

1. GitHub private repo 생성 (`budget-check`)
2. `budget_check/` 코드 push (`.streamlit/secrets.toml` 은 `.gitignore` 처리)
3. Streamlit Community Cloud → GitHub repo 연동 → `app.py` 지정
4. Secrets 탭에서 5개 키 등록
5. URL 팀 공유
