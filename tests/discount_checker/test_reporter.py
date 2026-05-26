import csv
from tools.discount_checker.comparator import CompareResult
from tools.discount_checker.reporter import write_csv


def test_write_csv_creates_file(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    assert path.exists()


def test_write_csv_filename_contains_date(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    assert "discount_check_" in path.name
    assert path.suffix == ".csv"


def test_write_csv_headers(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {
            "검수일시", "광고명", "소재_할인율", "대표_UID", "실제_최대_할인율", "오차", "상태"
        }


def test_write_csv_일치_row(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["광고명"] == "ad_A"
    assert rows[0]["소재_할인율"] == "70"
    assert rows[0]["실제_최대_할인율"] == "70"
    assert rows[0]["오차"] == "0"
    assert rows[0]["상태"] == "일치"


def test_write_csv_불일치_row(tmp_path):
    results = [CompareResult("ad_B", 70, "uid2", 68, 2, "불일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["상태"] == "불일치"
    assert rows[0]["오차"] == "2"


def test_write_csv_추출불가_row(tmp_path):
    results = [CompareResult("ad_C", None, None, None, None, "추출불가")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["소재_할인율"] == "추출불가"
    assert rows[0]["상태"] == "추출불가"


def test_write_csv_multiple_rows(tmp_path):
    results = [
        CompareResult("ad_A", 70, "uid1", 70, 0, "일치"),
        CompareResult("ad_B", 70, "uid2", 68, 2, "불일치"),
    ]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
