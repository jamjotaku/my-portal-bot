import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.credentials_path = 'credentials.json'
        self.client = None
        self.sheet = None

    def _authenticate(self):
        if not self.client:
            try:
                import os
                import json
                creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
                else:
                    creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, self.scope)
                
                self.client = gspread.authorize(creds)
                self.sheet = self.client.open_by_key(settings.GOOGLE_SHEET_KEY)
                logger.info("Successfully connected to Google Sheets.")
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {e}")

    async def add_archive_log(self, date_str, title, url, category):
        """archive_logs ワークシートにデータを追加する"""
        def _add():
            self._authenticate()
            if self.sheet:
                try:
                    worksheet = self.sheet.worksheet("archive_logs")
                    worksheet.append_row([date_str, title, url, category])
                except Exception as e:
                    logger.error(f"Error appending to archive_logs: {e}")
        await asyncio.to_thread(_add)

    async def add_work_log(self, date_str, join_time, leave_time, duration_minutes):
        """work_logs ワークシートにデータを追加する"""
        def _add():
            self._authenticate()
            if self.sheet:
                try:
                    worksheet = self.sheet.worksheet("work_logs")
                    worksheet.append_row([date_str, join_time, leave_time, duration_minutes])
                except Exception as e:
                    logger.error(f"Error appending to work_logs: {e}")
        await asyncio.to_thread(_add)

    async def search_archive_logs(self, keyword):
        """archive_logs ワークシートからキーワードで部分一致検索を行う"""
        def _search():
            self._authenticate()
            if not self.sheet:
                return []
            try:
                worksheet = self.sheet.worksheet("archive_logs")
                records = worksheet.get_all_records()
                results = []
                for record in records:
                    title = str(record.get('タイトル', ''))
                    category = str(record.get('分類カテゴリ', ''))
                    if keyword.lower() in title.lower() or keyword.lower() in category.lower():
                        results.append(record)
                return results[:10] # 最大10件
            except Exception as e:
                logger.error(f"Error searching archive_logs: {e}")
                return []
        return await asyncio.to_thread(_search)

db = Database()
