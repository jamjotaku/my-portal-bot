import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
from utils.database import db
from config import settings
import logging

logger = logging.getLogger(__name__)

class MentalLogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i in range(1, 6):
            btn = discord.ui.Button(label=str(i), style=discord.ButtonStyle.primary, custom_id=f"mental_log_{i}")
            btn.callback = self.make_callback(i)
            self.add_item(btn)
            
    def make_callback(self, level):
        async def callback(interaction: discord.Interaction):
            await db.add_mental_log(level)
            await interaction.response.send_message(f"メンタルスコア【{level}】を記録しました！お疲れ様です。", ephemeral=True)
        return callback

class PortalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(MentalLogView())
        self.daily_reminder.start()
        self.weekly_digest.start()

    def cog_unload(self):
        self.daily_reminder.cancel()
        self.weekly_digest.cancel()

    tz_jst = datetime.timezone(datetime.timedelta(hours=9))
    time_2200 = datetime.time(hour=22, minute=0, tzinfo=tz_jst)

    @tasks.loop(time=time_2200)
    async def daily_reminder(self):
        try:
            channel = self.bot.get_channel(settings.DAIRY_LOG_ID)
            if channel:
                view = MentalLogView()
                await channel.send('🌙 夜の22時です！今日のメンタルスコアを記録しましょう！', view=view)
        except Exception as e:
            logger.error(f"Error in daily_reminder: {e}")

    @tasks.loop(time=time_2200)
    async def weekly_digest(self):
        # 日曜日の場合のみ実行 (0 = 月曜, 6 = 日曜)
        if datetime.datetime.now(self.tz_jst).weekday() != 6:
            return
            
        try:
            channel = self.bot.get_channel(settings.DAIRY_LOG_ID)
            if not channel:
                return
                
            # 過去7日間のデータを取得
            memos = await db.get_recent_memos(limit=50)
            bookmarks = await db.get_recent_bookmarks(limit=20)
            
            # Geminiに渡すプロンプト作成
            import google.generativeai as genai
            if not settings.GEMINI_API_KEY:
                return
                
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-flash-latest")
            
            memo_texts = "\n".join([f"- {m.get('content', '')}" for m in memos[:20]])
            bm_texts = "\n".join([f"- {b.get('title', '')}: {b.get('original_url', '')}" for b in bookmarks[:10]])
            
            prompt = f"""
以下の今週の「メモ」と「ブックマーク」を元に、今週1週間の振り返りレポートを作成してください。
文体は親しみやすく、労うようなトーンでお願いします。

【今週のメモ】
{memo_texts}

【今週のブックマーク】
{bm_texts}

出力形式:
1. 今週のハイライト（要約）
2. 気になったトピック
3. 来週へ向けたひとこと
"""
            response = await model.generate_content_async(prompt)
            
            embed = discord.Embed(title="📊 今週のAI振り返りレポート", description=response.text[:4000], color=discord.Color.purple())
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in weekly_digest: {e}")

    @weekly_digest.before_loop
    async def before_weekly_digest(self):
        await self.bot.wait_until_ready()

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
        
        before_activity = before.activity.name if before.activity else ""
        after_activity = after.activity.name if after.activity else ""
        before_status = str(before.status)
        after_status = str(after.status)
        
        # ステータスかアクティビティに変更がない場合はスキップ
        if before_activity == after_activity and before_status == after_status:
            return
            
        vc_name = after.voice.channel.name if after.voice and after.voice.channel else ""
        
        await db.update_discord_status(status=after_status, activity=after_activity, vc_channel_name=vc_name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
            
        before_vc = before.channel.name if before.channel else ""
        after_vc = after.channel.name if after.channel else ""
        
        # VCチャンネルに変更がない場合はスキップ
        if before_vc == after_vc:
            return
            
        activity_name = member.activity.name if member.activity else ""
        status_name = str(member.status)
        
        await db.update_discord_status(status=status_name, activity=activity_name, vc_channel_name=after_vc)

async def setup(bot):
    await bot.add_cog(PortalCog(bot))
