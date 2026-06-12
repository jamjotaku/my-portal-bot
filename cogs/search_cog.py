import discord
from discord.ext import commands
from discord import app_commands
import logging
from utils.database import db

logger = logging.getLogger(__name__)

class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search", description="スプレッドシート(archive_logs)からキーワードで検索します")
    @app_commands.describe(keyword="検索したいキーワード")
    async def search(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer() # 処理に時間がかかる可能性があるのでdefer

        try:
            results = await db.search_archive_logs(keyword)

            if not results:
                await interaction.followup.send(f"「{keyword}」に一致するレコードは見つかりませんでした。")
                return

            embed = discord.Embed(
                title=f"検索結果: {keyword}",
                color=discord.Color.blue(),
                description=f"最大10件を表示しています。"
            )

            for item in results:
                date_str = item.get('日時', '')
                title = item.get('タイトル', 'No Title')
                url = item.get('URL', '')
                category = item.get('分類カテゴリ', '')

                value = f"**カテゴリ**: {category}\n**日時**: {date_str}"
                if url:
                    value += f"\n[リンクを開く]({url})"

                embed.add_field(name=title, value=value, inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Search command error: {e}")
            await interaction.followup.send("検索中にエラーが発生しました。")

async def setup(bot):
    await bot.add_cog(SearchCog(bot))
