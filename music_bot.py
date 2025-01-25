import discord
from discord.ext import commands
import os

# 1) 길드(서버) 테스트 ID (선택 사항)
TEST_GUILD_ID = 629171925976875009  # 원하는 서버 ID (정수)

# 2) 봇 초기화
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())


@bot.event
async def on_ready():
    # 특정 길드에만 등록하면 즉시 테스트 가능
    # (Global 등록은 최대 1시간 정도 전파 지연)
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s) to guild {TEST_GUILD_ID}.")
    print(f"Logged in as {bot.user}")


async def main():
    async with bot:
        # 3) music_cog.py 로드
        await bot.load_extension("music_cog")
        # 4) 토큰으로 봇 시작
        await bot.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
