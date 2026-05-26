import argparse
import sys

from tools.discount_checker import config
from tools.discount_checker.cache import Cache
from tools.discount_checker.comparator import CompareResult, compare
from tools.discount_checker.image_analyzer import ImageAnalyzer
from tools.discount_checker.meta_client import MetaClient
from tools.discount_checker.product_scraper import ProductScraper
from tools.discount_checker.reporter import send_slack, write_csv
from tools.discount_checker.sheet_reader import read_ad_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="광고 소재 할인율 검수")
    parser.add_argument("--sheet-url", required=True, help="Google Sheets URL")
    parser.add_argument("--ad-col", default="광고명", help="광고명 컬럼 헤더 (기본: 광고명)")
    parser.add_argument("--uid-col", default="UID", help="UID 컬럼 헤더 (기본: UID)")
    args = parser.parse_args()

    cache = Cache(config.CACHE_PATH)
    meta = MetaClient(config.META_ACCESS_TOKEN, config.META_AD_ACCOUNT_ID, cache)
    analyzer = ImageAnalyzer(config.ANTHROPIC_API_KEY, cache)
    scraper = ProductScraper(cache)

    try:
        ad_rows = read_ad_rows(
            args.sheet_url,
            config.GOOGLE_SERVICE_ACCOUNT_JSON,
            ad_col=args.ad_col,
            uid_col=args.uid_col,
        )
    except ValueError as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"총 {len(ad_rows)}개 광고 검수 시작")
    results: list[CompareResult] = []

    for row in ad_rows:
        print(f"  처리 중: {row.ad_name}")
        creative = meta.get_creative(row.ad_name)
        if creative is None:
            results.append(
                CompareResult(row.ad_name, None, None, None, None, "조회실패")
            )
            continue

        creative_id, image_url = creative
        creative_discount = analyzer.extract_discount(creative_id, image_url)
        uid_discounts = scraper.get_max_discount(row.uids)
        results.append(compare(row.ad_name, creative_discount, uid_discounts))

    csv_path = write_csv(results, config.OUTPUT_DIR)
    print(f"\n결과 저장: {csv_path}")

    send_slack(results, config.SLACK_WEBHOOK_URL)

    mismatch_count = sum(1 for r in results if r.status == "불일치")
    print(f"완료: {len(results)}건 검수, {mismatch_count}건 불일치")


if __name__ == "__main__":
    main()
