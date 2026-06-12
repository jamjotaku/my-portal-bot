import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import discord
from discord.ext import commands
from config import settings
import os

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIのセットアップ (常時起動用)
app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Discord Botのセットアップ
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready. Logged in as {bot.user}")
    try:
        # スラッシュコマンドの同期
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Cogのロード
async def load_cogs():
    cogs = [
        "cogs.inbox_cog",
        "cogs.voice_cog",
        "cogs.search_cog",
        "cogs.music_cog",
        "cogs.youtube_cog"
    ]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded {cog}")
        except Exception as e:
            logger.error(f"Failed to load {cog}: {e}")

# サーバー起動用関数
async def start_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=settings.PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

# メイン実行処理
async def main():
    # Cogsの読み込み
    await load_cogs()
    
    # BotとAPIサーバーを並行稼働させる
    # renderなどでポートバインディングが必要なためAPIを先に起動させるかgatherで同時に実行する
    if not settings.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set.")
        return

    # asyncio.gatherで両方を同時に実行する
    await asyncio.gather(
        start_api(),
        bot.start(settings.DISCORD_BOT_TOKEN)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
