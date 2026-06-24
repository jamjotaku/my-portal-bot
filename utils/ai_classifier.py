import google.generativeai as genai
from config import settings
import json
import logging

logger = logging.getLogger(__name__)

# APIキーの設定
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set.")

# JSONスキーマの定義 (Structured Outputs用)
classification_schema = {
    "type": "OBJECT",
    "properties": {
        "category": {
            "type": "STRING",
            "description": "分類先のチャンネル名（例: todo-タスク, dairy-log, gourmet-memo, hobby-clips, cosplay-archive のいずれか）"
        },
        "tags": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "フォーラム用のタグ、または該当なしの場合は空配列"
        },
        "reason": {
            "type": "STRING",
            "description": "分類した理由の簡潔な説明"
        }
    },
    "required": ["category", "tags", "reason"]
}

async def classify_content(text: str, title: str = "", description: str = "") -> dict:
    """テキストやURLの情報を元にGemini APIで分類を行う"""
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        
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

JSONフォーマットで回答してください。
"""
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=classification_schema,
                temperature=0.1
            )
        )
        
        result = json.loads(response.text)
        return result

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return {
            "category": "dairy-log",
            "tags": [],
            "reason": f"API Error fallback: {e}"
        }

async def transcribe_audio(file_path: str) -> str:
    """音声ファイルをGeminiに渡して文字起こしを行う"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # ファイルをアップロード (ローカルパスを指定)
        audio_file = genai.upload_file(path=file_path)
        
        prompt = "この音声メッセージの文字起こしをしてください。自然な日本語の文章に整えてください。"
        response = await model.generate_content_async([prompt, audio_file])
        
        # 不要になったファイルを削除
        try:
            genai.delete_file(audio_file.name)
        except Exception:
            pass
            
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Audio Transcription Error: {e}")
        return ""
