# 광고 소재 할인율 검수 자동화 설계

**작성일:** 2026-05-26  
**도구 위치:** `tools/discount_checker/`

---

## 목적

메타 광고 소재 이미지에 노출된 할인율과 랜딩 상품 페이지의 실제 최대 할인율을 자동으로 비교하여 불일치 건을 검출한다. 광고 소재 내 할인율 기준으로 집행이 가능하기 때문에 오차 없는 검수가 필수다.

---

## 범위

- **지원 매체:** 메타(Facebook/Instagram) — 카카오는 추후 확장
- **입력:** Google Sheets URL (담당자별 소재관리시트)
- **출력:** CSV 파일 + Slack 알림 (불일치 건만)
- **허용 오차:** 0% (정확 일치만 통과)

---

## 데이터 흐름

```
[CLI 실행: --sheet-url + 옵션]
        ↓
1. sheet_reader     Google Sheets URL 파싱 → 지정 컬럼으로 광고명·UID 목록 추출
        ↓
2. meta_client      Meta Marketing API → 광고명으로 creative 이미지 URL 조회
        ↓
3. image_analyzer   Claude Vision API → 이미지 내 할인율(%) 숫자 추출
        ↓
4. product_scraper  Playwright → musinsa.com/products/{UID} 스크래핑
                    여러 UID 중 최대 할인율 선택
        ↓
5. comparator       소재 할인율 == 실제 최대 할인율 비교 (오차 0%)
        ↓
6. reporter         output/discount_check_YYYY-MM-DD.csv 저장
                    불일치 건 → Slack 알림
```

---

## 사용법

```bash
# 기본 (컬럼명 자동 탐색: "광고명", "UID")
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}"

# 컬럼명 직접 지정
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}" \
  --ad-col "광고명" \
  --uid-col "상품UID"

# 특정 범위 지정
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}&range=A1:Z100"
```

---

## 파일 구조

```
tools/discount_checker/
  __init__.py
  check.py            # CLI 진입점 (argparse)
  sheet_reader.py     # URL 파싱 + 컬럼 탐색 + 데이터 추출
  meta_client.py      # Meta Marketing API 연동
  image_analyzer.py   # Claude Vision으로 할인율 추출
  product_scraper.py  # Playwright로 musinsa 상품 페이지 스크래핑
  comparator.py       # 할인율 비교 + 최대값 선택 로직
  reporter.py         # CSV 저장 + Slack 웹훅 알림
  cache.py            # JSON 파일 기반 캐시 (TTL 지원)
  config.py           # 환경변수 로딩

output/
  discount_check_2026-05-26.csv
cache/
  discount_check_cache.json
```

---

## 모듈별 상세

### sheet_reader.py

- URL에서 `spreadsheet_id`, `gid`, `range` 파싱
- gid → 시트명 변환 (Sheets API `spreadsheets.get` 호출)
- 헤더 행 스캔으로 `--ad-col`, `--uid-col` 값과 일치하는 컬럼 인덱스 탐색
- 기본값: `--ad-col "광고명"`, `--uid-col "UID"`
- UID 값은 쉼표 구분 문자열 → 리스트로 파싱
- 반환: `list[AdRow]` (광고명, uid_list)

### meta_client.py

- Meta Marketing API v19 사용
- 광고명(ad name)으로 ad object 조회 → creative → image URL
- 인증: `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` 환경변수
- 캐시: creative_id + image_hash → 이미지 URL (영구, 이미지 변경 시 무효화)

### image_analyzer.py

- 이미지 URL 다운로드 → base64 인코딩
- Claude Vision 프롬프트: "이 광고 이미지에서 할인율(%)을 숫자만 추출해줘. 없으면 null 반환"
- 반환: `int | None` (예: 70, 30, None)
- 캐시 키: `creative_id + image_hash`

### product_scraper.py

- Playwright (headless) → `https://www.musinsa.com/products/{UID}`
- JS 렌더링 대기 후 할인율 요소 파싱
- 여러 UID → 각각 스크래핑 → `max()` 선택
- 캐시 키: `UID`, TTL: 24시간

### comparator.py

- `소재_할인율 == 실제_최대_할인율` → 일치/불일치 판정
- 허용 오차: 0% (정확 일치)
- 반환: `CompareResult` (광고명, 소재율, 최대율, 오차, 상태)

### reporter.py

**CSV 출력** (`output/discount_check_YYYY-MM-DD.csv`):
```
검수일시,광고명,소재_할인율,대표_UID,실제_최대_할인율,오차,상태
2026-05-26 09:00,260420_…_70%이상_CPC,70,5877083,68,-2,불일치
2026-05-26 09:00,260420_…_아울렛_CPC,30,4944027,30,0,일치
```

**Slack 알림** (불일치 건만, `SLACK_WEBHOOK_URL` 환경변수):
```
⚠️ [할인율 불일치] 260420_…_70%이상_CPC
소재: 70% → 실제 최대: 68% (오차 -2%)
UID: 5877083
```

### cache.py

- 저장소: `cache/discount_check_cache.json`
- TTL 지원: 키별 만료 시각 저장
- 인터페이스: `get(key)`, `set(key, value, ttl_seconds=None)`

### config.py

```
META_ACCESS_TOKEN      Meta API 액세스 토큰
META_AD_ACCOUNT_ID     광고 계정 ID (act_XXXXXXXXX)
ANTHROPIC_API_KEY      Claude Vision 호출용
SLACK_WEBHOOK_URL      Slack 웹훅 (불일치 알림)
```

---

## 캐시 전략

| 대상 | 캐시 키 | TTL | 무효화 조건 |
|------|--------|-----|-----------|
| 이미지 할인율 | `creative_id:image_hash` | 영구 | 이미지 hash 변경 시 |
| 상품 할인율 | `uid:{UID}` | 24시간 | TTL 만료 |

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| 광고명이 Meta API에서 조회 안 됨 | 해당 행 `상태=조회실패` 로 CSV 기록, 스킵 |
| 이미지에서 할인율 추출 실패 | `소재_할인율=추출불가` 로 기록, 스킵 |
| 상품 페이지 스크래핑 실패 | `실제_최대_할인율=스크래핑실패` 로 기록, 스킵 |
| 컬럼명 미발견 | CLI 에러 종료 + 안내 메시지 출력 |

---

## 의존성

```
anthropic          Claude Vision API
facebook-business  Meta Marketing API SDK
playwright         musinsa 페이지 스크래핑
google-auth        Google Sheets MCP 또는 직접 API 인증
python-dotenv      환경변수 로딩
```

---

## 테스트 범위

- `sheet_reader`: URL 파싱, gid→시트명, 컬럼 탐색, UID 파싱
- `comparator`: 일치/불일치 판정, 최대값 선택
- `cache`: TTL 만료, hit/miss
- `image_analyzer`: Claude Vision 응답 파싱 (mock)
- `product_scraper`: 할인율 파싱 (HTML fixture)
