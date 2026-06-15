import discord
from discord.ext import commands
import re
from datetime import datetime
import logging
from config import settings
from utils.scraper import fetch_page_info
from utils.ai_classifier import classify_content
from utils.database import db

logger = logging.getLogger(__name__)

class InboxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 監視対象チャンネルかチェック
        if message.channel.id not in [settings.INBOX_DAILY_ID, settings.INBOX_TECH_ID]:
            return

        # Webhookからのメッセージの場合、#webhooksチャンネルへ転送する
        if message.webhook_id:
            webhook_channel = self.bot.get_channel(settings.WEBHOOKS_ID)
            if webhook_channel:
                if message.embeds:
                    await webhook_channel.send(content=message.content, embeds=message.embeds)
                else:
                    embed = discord.Embed(
                        title="Webhook Notification",
                        description=message.content,
                        color=discord.Color.purple(),
                        timestamp=datetime.now()
                    )
                    await webhook_channel.send(embed=embed)
                try:
                    await message.delete()
                except Exception:
                    pass
            return

        # Bot自身のメッセージは無視 (Webhook以外のBot)
        if message.author.bot:
            return

        logger.info(f"Received message in Inbox: {message.content}")

        # URLの抽出
        urls = self.url_pattern.findall(message.content)
        title = ""
        description = ""
        target_url = urls[0] if urls else ""

        if target_url:
            # スクレイピング
            page_info = await fetch_page_info(target_url)
            title = page_info.get("title", "")
            description = page_info.get("description", "")

        # AIで分類
        classification = await classify_content(message.content, title, description)
        category_name = classification.get("category", "dairy-log")
        tags = classification.get("tags", [])
        reason = classification.get("reason", "")
        
        target_channel_id = settings.CHANNEL_MAPPING.get(category_name, settings.DAIRY_LOG_ID)
        target_channel = self.bot.get_channel(target_channel_id)

        if not target_channel:
            logger.warning(f"Target channel {category_name} not found. Fallback to Dairy Log.")
            target_channel = self.bot.get_channel(settings.DAIRY_LOG_ID)

        # 転送処理
        if isinstance(target_channel, discord.ForumChannel):
            # フォーラムチャンネルの場合、タグの検索とスレッド作成
            available_tags = target_channel.available_tags
            applied_tags = []
            
            # タグ名でマッチング
            for tag_str in tags:
                for available_tag in available_tags:
                    if tag_str.lower() in available_tag.name.lower():
                        applied_tags.append(available_tag)
                        break
            
            thread_name = title[:90] if title else message.content[:90]
            if not thread_name:
                thread_name = "New Item"

            # 既存の同一名スレッド（アクティブなもの）を探す
            existing_thread = None
            for thread in target_channel.threads:
                if thread.name == thread_name:
                    existing_thread = thread
                    break

            if existing_thread:
                # 既存のスレッドへ追記
                await existing_thread.send(content=message.content)
            else:
                # 新規スレッドを作成
                await target_channel.create_thread(
                    name=thread_name,
                    content=message.content,
                    applied_tags=applied_tags[:5] # Discordの制限で最大5つ
                )
        else:
            # 通常のテキストチャンネルの場合
            await target_channel.send(content=message.content)

        # Webhookチャンネルへ分類理由のログを送信
        webhook_channel = self.bot.get_channel(settings.WEBHOOKS_ID)
        if webhook_channel:
            log_embed = discord.Embed(
                title=f"分類ログ: {title if title else '転送メモ'}",
                url=target_url if target_url else None,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="元のメッセージ", value=message.content[:1024], inline=False)
            log_embed.add_field(name="分類先", value=f"<#{target_channel.id}>", inline=False)
            log_embed.add_field(name="分類理由", value=reason, inline=False)
            log_embed.set_footer(text=f"Tags: {', '.join(tags)}" if tags else "No tags")
            await webhook_channel.send(embed=log_embed)

        # 元のメッセージにリアクション
        await message.add_reaction("✅")

        # Supabaseへ記録
        if target_url:
            await db.add_bookmark(
                original_url=target_url,
                content=message.content,
                title=title,
                description=description,
                image_url="", # 画像URLは現状空
                tags=tags
            )
        else:
            await db.add_memo(
                content=message.content,
                tags=tags
            )

async def setup(bot):
    await bot.add_cog(InboxCog(bot))
