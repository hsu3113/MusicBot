import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# .env 파일 로드
load_dotenv()

# DISCORD_TOKEN 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN이 .env 파일에 정의되어 있지 않습니다.")
print(f"DISCORD_TOKEN = {DISCORD_TOKEN} ")

# 봇 초기화
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # 글로벌 동기화
        print(f"Synced {len(synced)} global command(s).")
    except Exception as e:
        print(f"글로벌 명령어 동기화 실패: {e}")
    print(f"Logged in as {bot.user}")


async def main():
    try:
        async with bot:
            # music_cog.py 로드
            await bot.load_extension("music_cog")
            print("Music cog 로드 완료")
            # 토큰으로 봇 시작
            await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("🔴 봇이 중단되었습니다.")
    finally:
        await bot.close()
        print("🔴 봇이 종료되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
