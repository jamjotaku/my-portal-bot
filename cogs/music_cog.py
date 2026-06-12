import discord
from discord.ext import commands
import logging
from config import settings

logger = logging.getLogger(__name__)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ユーザーごとの再生履歴を保持する: {user_id: set("track - artist")}
        self.user_tracks = {}

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return

        # VCにいない場合は記録しない
        if after.voice is None or after.voice.channel is None:
            return

        # アクティビティからSpotifyを探す
        spotify_activity = discord.utils.get(after.activities, type=discord.ActivityType.listening)
        
        if spotify_activity and isinstance(spotify_activity, discord.Spotify):
            track_name = spotify_activity.title
            artist_name = spotify_activity.artist
            track_info = f"{track_name} - {artist_name}"

            if after.id not in self.user_tracks:
                self.user_tracks[after.id] = []
            
            # 同じ曲の連続記録を防ぐ（簡易的な重複排除。順番は保持したいのでリストを使用）
            if not self.user_tracks[after.id] or self.user_tracks[after.id][-1] != track_info:
                self.user_tracks[after.id].append(track_info)
                logger.info(f"Recorded Spotify track for {after.name}: {track_info}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        # 退室検知 (before.channelが存在し、after.channelがNone)
        if before.channel is not None and after.channel is None:
            tracks = self.user_tracks.pop(member.id, [])
            
            if tracks:
                music_channel = self.bot.get_channel(settings.MUSIC_LOG_ID)
                if music_channel:
                    # 曲目リストをテキスト化（長すぎる場合は省略）
                    tracks_text = "\n".join([f"🎵 {t}" for t in tracks])
                    if len(tracks_text) > 4000:
                        tracks_text = tracks_text[:4000] + "\n... (省略)"

                    embed = discord.Embed(
                        title=f"{member.display_name} の作業用BGMログ",
                        description=tracks_text,
                        color=discord.Color.from_rgb(30, 215, 96) # Spotify Green
                    )
                    await music_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
