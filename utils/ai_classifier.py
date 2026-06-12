import google.generativeai as genai
from config import settings
import json
import logging
import re

logger = logging.getLogger(__name__)

# APIキーの設定
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set.")

async def classify_content(text: str, title: str = "", description: str = "") -> dict:
    """テキストやURLの情報を元にGemini APIで分類を行う"""
    try:
        model = genai.GenerativeModel("gemini-pro") # より互換性の高い 1.0 Proモデルを使用
        
        prompt = f"""
以下の内容を分析し、適切なDiscordのチャンネルに分類してください。

【分類先のチャンネル候補】
- todo-タスク (直近のTODO管理)
- dairy-log (日記・日々の記録)
- gourmet-memo (飲食店ログ・開拓メモ。フォーラム形式)
- hobby-clips (エンタメ・推し活全般)
- cosplay-archive (コスプレイヤー情報・図鑑化。フォーラム形式)

【入力情報】
本文テキスト: {text}
URLのタイトル: {title}
URLの概要: {description}

必ず以下のJSONフォーマットのみで回答してください。マークダウンのコードブロック(```json など)は付けずに、直接JSON文字列だけを出力してください。
{{
  "category": "分類先のチャンネル名",
  "tags": ["フォーラム用のタグ文字列の配列", "該当なしの場合は空配列"],
  "reason": "分類した理由の簡潔な説明"
}}
"""
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1
            )
        )
        
        # 結果をJSONとしてパース
        text_resp = response.text.strip()
        # 万が一コードブロックが含まれていた場合は除去
        text_resp = re.sub(r'^```[a-zA-Z]*\n', '', text_resp)
        text_resp = re.sub(r'\n```$', '', text_resp)
        
        result = json.loads(text_resp)
        return result

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        # フォールバック: エラー時はデフォルトとして日常に返す
        return {
            "category": "dairy-log",
            "tags": [],
            "reason": f"API Error fallback: {e}"
        }
