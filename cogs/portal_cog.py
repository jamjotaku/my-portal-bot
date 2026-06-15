import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
from utils.database import db
from config import settings
import logging

logger = logging.getLogger(__name__)

class PortalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_reminder.start()

    def cog_unload(self):
        self.daily_reminder.cancel()

    tz_jst = datetime.timezone(datetime.timedelta(hours=9))
    time_2200 = datetime.time(hour=22, minute=0, tzinfo=tz_jst)

    @tasks.loop(time=time_2200)
    async def daily_reminder(self):
        try:
            channel = self.bot.get_channel(settings.DAIRY_LOG_ID)
            if channel:
                await channel.send('🌙 夜の22時です！今日の振り返りやメンタルスコアはつけましたか？\nWebポータルまたはコマンドから記録しましょう！')
        except Exception as e:
            logger.error(f"Error in daily_reminder: {e}")

    @daily_reminder.before_loop
    async def before_daily_reminder(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="memos", description="最近のメモを5件表示します")
    async def memos(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            memos_data = await db.get_recent_memos(limit=5)
            if not memos_data:
                await interaction.followup.send("まだメモがありません。")
                return

            embed = discord.Embed(title="最近のメモ", color=discord.Color.yellow())
            for memo in memos_data:
                content = memo.get("content", "")[:200]
                date_str = memo.get("created_at", "")[:10]
                embed.add_field(name=date_str, value=content, inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in memos command: {e}")
            await interaction.followup.send("メモの取得に失敗しました。")

    @app_commands.command(name="bookmarks", description="最近のブックマークを5件表示します")
    async def bookmarks(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            bookmarks_data = await db.get_recent_bookmarks(limit=5)
            if not bookmarks_data:
                await interaction.followup.send("まだブックマークがありません。")
                return

            embed = discord.Embed(title="最近のブックマーク", color=discord.Color.blue())
            for bm in bookmarks_data:
                title = bm.get("title") or bm.get("content", "")[:50] or "No Title"
                url = bm.get("original_url", "")
                date_str = bm.get("created_at", "")[:10]
                embed.add_field(name=f"{date_str} - {title}", value=url, inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in bookmarks command: {e}")
            await interaction.followup.send("ブックマークの取得に失敗しました。")

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return
        
        activity_name = after.activity.name if after.activity else ""
        status_name = str(after.status)
        vc_name = after.voice.channel.name if after.voice and after.voice.channel else ""
        
        await db.update_discord_status(status=status_name, activity=activity_name, vc_channel_name=vc_name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
            
        activity_name = member.activity.name if member.activity else ""
        status_name = str(member.status)
        vc_name = after.channel.name if after.channel else ""
        
        await db.update_discord_status(status=status_name, activity=activity_name, vc_channel_name=vc_name)

async def setup(bot):
    await bot.add_cog(PortalCog(bot))
