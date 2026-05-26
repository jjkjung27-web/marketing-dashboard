# 광고 소재 할인율 검수 자동화

메타 광고 소재 이미지에 노출된 할인율과 무신사 상품 페이지의 실제 최대 할인율을 자동으로 비교합니다.

## 동작 방식

```
소재관리 시트 URL 입력
       ↓
Meta API → 광고명으로 소재 이미지 URL 조회
       ↓
Claude Vision → 이미지에서 할인율(%) 추출
       ↓
Playwright → musinsa.com/products/{UID} 스크래핑 → 실제 최대 할인율
       ↓
비교 (오차 0% 기준)
       ↓
output/discount_check_YYYY-MM-DD.csv 저장 + Slack 불일치 알림
```

## 사전 준비 (최초 1회)

### 1. Python 의존성 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Sheets 공유 설정

검수할 소재관리 시트를 **"링크가 있는 사용자 보기 가능"** 으로 설정합니다.
(이미 팀 내 공유된 시트라면 별도 설정 불필요)

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
META_ACCESS_TOKEN=your_meta_access_token
META_AD_ACCOUNT_ID=act_XXXXXXXXX
ANTHROPIC_API_KEY=your_anthropic_api_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

| 변수 | 설명 | 필수 |
|------|------|------|
| `META_ACCESS_TOKEN` | Meta 마케팅 API 액세스 토큰 | ✅ |
| `META_AD_ACCOUNT_ID` | Meta 광고 계정 ID (`act_` 포함) | ✅ |
| `ANTHROPIC_API_KEY` | Claude Vision API 키 | ✅ |
| `SLACK_WEBHOOK_URL` | Slack 웹훅 URL (불일치 알림) | 선택 |

**Meta 액세스 토큰 발급:**
Meta Business → 설정 → 시스템 사용자 → 액세스 토큰 생성 (`ads_read` 권한 필요)

**Anthropic API 키 발급:**
[console.anthropic.com](https://console.anthropic.com) → API Keys

## 사용법

### 기본 실행

```bash
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}"
```

### 컬럼명이 다른 시트

```bash
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}" \
  --ad-col "광고명" \
  --uid-col "상품UID"
```

### 특정 범위만

```bash
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}&range=A1:Z100"
```

## 결과물

### CSV 파일 (`output/discount_check_YYYY-MM-DD.csv`)

| 검수일시 | 광고명 | 소재_할인율 | 대표_UID | 실제_최대_할인율 | 오차 | 상태 |
|---------|--------|-----------|---------|--------------|------|------|
| 2026-05-26 09:00 | 260420_…_70%이상_CPC | 70 | 5877083 | 68 | 2 | 불일치 |
| 2026-05-26 09:00 | 260420_…_아울렛_CPC | 30 | 4944027 | 30 | 0 | 일치 |

**상태 값:**
- `일치` — 소재 할인율 = 실제 최대 할인율
- `불일치` — 오차 발생 (Slack 알림 전송)
- `조회실패` — Meta API에서 광고명 미발견
- `추출불가` — 이미지에서 할인율 추출 실패
- `스크래핑실패` — 모든 UID 상품 페이지 스크래핑 실패

### Slack 알림 (불일치 건만)

```
⚠️ [할인율 불일치] 260420_…_70%이상_CPC
소재: 70% → 실제 최대: 68% (오차 +2%)
UID: 5877083
```

## 캐시

- **이미지 할인율:** 영구 캐시 (`image:{creative_id}:{image_hash}`)  
  소재 이미지가 변경되면 자동으로 재추출
- **상품 할인율:** 24시간 캐시 (`uid:{UID}`)  
  가격 변동 반영을 위해 24시간마다 갱신
- **스크래핑 실패:** 1시간 캐시 (재시도 과다 방지)

캐시 파일 위치: `cache/discount_check_cache.json`  
초기화: 파일 삭제 후 재실행

## 주의사항

- **무신사 CSS 선택자:** 첫 실행 후 `실제_최대_할인율` 컬럼이 대부분 비어 있으면, `tools/discount_checker/product_scraper.py`의 `query_selector` 인자를 실제 페이지 HTML에 맞게 수정 필요
- **`.env`와 `service_account.json`은 절대 커밋하지 마세요** (`.gitignore`에 포함됨)
- 소재 1건당 Claude Vision 호출 비용 약 $0.005 발생 (캐시 적중 시 무료)
