import discord
from discord.ext import commands
from datetime import datetime
import logging
from config import settings
from utils.database import db

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ユーザーIDをキーに、入室時刻を保持
        self.voice_sessions = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        # 入室検知 (before.channelがNoneで、after.channelが存在する)
        if before.channel is None and after.channel is not None:
            self.voice_sessions[member.id] = datetime.now()
            logger.info(f"{member.name} joined VC at {self.voice_sessions[member.id]}")

        # 退室検知 (before.channelが存在し、after.channelがNone)
        elif before.channel is not None and after.channel is None:
            join_time = self.voice_sessions.pop(member.id, None)
            
            if join_time:
                leave_time = datetime.now()
                duration = leave_time - join_time
                duration_minutes = int(duration.total_seconds() / 60)
                
                hours, mins = divmod(duration_minutes, 60)
                time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

                # ログチャンネルへ投稿
                log_channel = self.bot.get_channel(settings.WORK_LOG_ID)
                if log_channel:
                    date_str = join_time.strftime("%Y-%m-%d")
                    join_str = join_time.strftime("%H:%M")
                    leave_str = leave_time.strftime("%H:%M")
                    
                    embed = discord.Embed(
                        title="作業時間記録",
                        color=discord.Color.green(),
                        description=f"**{member.display_name}** が作業を終了しました。"
                    )
                    embed.add_field(name="日付", value=date_str, inline=True)
                    embed.add_field(name="時間", value=f"{join_str} 〜 {leave_str}", inline=True)
                    embed.add_field(name="経過時間", value=time_str, inline=True)
                    
                    await log_channel.send(embed=embed)

                    # スプレッドシートへ記録
                    await db.add_work_log(date_str, join_str, leave_str, duration_minutes)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
