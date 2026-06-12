import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

async def fetch_page_info(url: str):
    """URLから非同期でページのタイトルとDescriptionを取得する"""
    try:
        async with aiohttp.ClientSession() as session:
            # ユーザーエージェントを設定してブロックを回避しやすくする
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch page: {url}, status code: {response.status}")
                    return {"title": "Failed to retrieve title", "description": ""}

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # タイトルの取得
                title = soup.title.string if soup.title else "No title found"

                # メタディスクリプションの取得
                description = ""
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    description = meta_desc["content"]
                else:
                    # og:descriptionのフォールバック
                    og_desc = soup.find("meta", property="og:description")
                    if og_desc and og_desc.get("content"):
                        description = og_desc["content"]

                return {"title": title.strip() if title else "", "description": description.strip() if description else ""}

    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return {"title": "Error retrieving title", "description": ""}
