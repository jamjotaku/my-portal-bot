import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
from config import settings
from datetime import datetime
import dateutil.parser

logger = logging.getLogger(__name__)

class YoutubeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="yt", description="YouTubeチャンネルの最新動画や配信予定を取得します")
    @app_commands.describe(channel_name="検索するチャンネル名")
    async def yt(self, interaction: discord.Interaction, channel_name: str):
        await interaction.response.defer()

        if not settings.YOUTUBE_API_KEY:
            await interaction.followup.send("YOUTUBE_API_KEY が設定されていません。")
            return

        try:
            async with aiohttp.ClientSession() as session:
                # 1. チャンネル名からチャンネルIDを検索
                search_url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": channel_name,
                    "type": "channel",
                    "key": settings.YOUTUBE_API_KEY,
                    "maxResults": 1
                }
                async with session.get(search_url, params=params) as resp:
                    data = await resp.json()
                    
                    if not data.get("items"):
                        await interaction.followup.send(f"「{channel_name}」というチャンネルは見つかりませんでした。")
                        return
                    
                    channel_id = data["items"][0]["id"]["channelId"]
                    channel_title = data["items"][0]["snippet"]["title"]

                # 2. チャンネルの最新動画（配信を含む）を取得
                params_video = {
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "date",
                    "type": "video",
                    "key": settings.YOUTUBE_API_KEY,
                    "maxResults": 3 # 最新3件
                }
                async with session.get(search_url, params=params_video) as resp_v:
                    video_data = await resp_v.json()

                    if not video_data.get("items"):
                        await interaction.followup.send(f"{channel_title} の最新動画は見つかりませんでした。")
                        return

                    embeds = []
                    for item in video_data["items"]:
                        vid_id = item["id"]["videoId"]
                        snippet = item["snippet"]
                        title = snippet["title"]
                        publish_time = snippet["publishedAt"]
                        thumbnail = snippet["thumbnails"]["high"]["url"]
                        
                        # 配信かどうかの詳細(liveBroadcastContent)を確認
                        live_status = snippet.get("liveBroadcastContent", "none")
                        status_text = "📺 動画"
                        color = discord.Color.red()
                        
                        if live_status == "live":
                            status_text = "🔴 配信中"
                            color = discord.Color.red()
                        elif live_status == "upcoming":
                            status_text = "📅 配信予定"
                            color = discord.Color.blue()
                            
                        # 時刻のフォーマット
                        dt = dateutil.parser.isoparse(publish_time)
                        formatted_time = dt.strftime("%Y/%m/%d %H:%M")

                        embed = discord.Embed(
                            title=title,
                            url=f"https://www.youtube.com/watch?v={vid_id}",
                            color=color,
                            description=f"**{status_text}**\n日時: {formatted_time}"
                        )
                        embed.set_author(name=channel_title)
                        embed.set_thumbnail(url=thumbnail)
                        embeds.append(embed)

                    await interaction.followup.send(content=f"**{channel_title}** の最新情報:", embeds=embeds)

        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            await interaction.followup.send("情報の取得中にエラーが発生しました。")

async def setup(bot):
    await bot.add_cog(YoutubeCog(bot))
