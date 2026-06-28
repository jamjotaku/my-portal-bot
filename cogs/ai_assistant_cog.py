import discord
from discord.ext import commands
import logging
from config import settings
from utils.database import db
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIAssistantCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージは無視
        if message.author.bot:
            return

        # Botへのメンションが含まれているかチェック
        if self.bot.user in message.mentions:
            if not self.model:
                await message.reply("⚠️ AIの設定が行われていません (APIキー未設定)")
                return

            # 「メンション部分」を取り除いたテキストを取得
            user_text = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            if not user_text:
                await message.reply("私に何か質問やお願いがありますか？")
                return

            # 入力中ステータスを表示
            async with message.channel.typing():
                try:
                    # 過去のメモとブックマークをデータベースから取得
                    recent_memos = await db.get_recent_memos(limit=30)
                    recent_bookmarks = await db.get_recent_bookmarks(limit=10)
                    
                    # コンテキストの構築
                    context_text = "【最近のあなたのメモ】\n"
                    for memo in recent_memos:
                        tags = memo.get('tags') or []
                        context_text += f"- {memo.get('created_at')} : {memo.get('content')} (タグ: {', '.join(tags)})\n"
                    
                    context_text += "\n【最近のあなたのブックマーク】\n"
                    for bm in recent_bookmarks:
                        context_text += f"- {bm.get('created_at')} : {bm.get('title')} ({bm.get('original_url')})\n"
                    
                    prompt = f"""
あなたはユーザーの個人的なAIアシスタントです。
以下の「ユーザーの最近の記録（メモ・ブックマーク）」を参考にして、ユーザーの質問や指示に答えてください。
もし記録にないことを聞かれた場合は、一般論として答えるか、記録にない旨を伝えてください。
回答は親しみやすく、かつ簡潔にまとめてください。

{context_text}

【ユーザーからのメッセージ】
{user_text}
"""
                    response = await self.model.generate_content_async(prompt)
                    
                    # Discordの文字数制限(2000文字)を超えないように分割または切り詰め
                    reply_text = response.text.strip()
                    if len(reply_text) > 2000:
                        reply_text = reply_text[:1995] + "..."

                    await message.reply(reply_text)

                except Exception as e:
                    logger.error(f"AIAssistant Error: {e}")
                    await message.reply("申し訳ありません、処理中にエラーが発生しました。")

async def setup(bot):
    await bot.add_cog(AIAssistantCog(bot))
