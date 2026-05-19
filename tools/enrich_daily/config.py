# tools/enrich_daily/config.py
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"   # Google Sheets 스프레드시트 ID로 교체
INDEX_GID = "0"                           # ad_index 시트의 gid
INDEX_SHEET_NAME = "ad_index"             # gspread용 시트 이름 (쓰기 시 사용)
CREDS_PATH = r"C:\Users\MADUP\.claude\google-service-account.json"
OUTPUT_DIR = "data/output"
