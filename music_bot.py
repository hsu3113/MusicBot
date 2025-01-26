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

# 봇 초기화
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f"connecting...")
    # 특정 서버 ID
    GUILD_ID = 629171925976875009  # 테스트할 서버 ID를 입력하세요
    guild = discord.Object(id=GUILD_ID)

    print(f"connecting.")

    # 특정 서버에서 Slash Command 동기화
    synced = await bot.tree.sync(guild=guild)
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
    except Exception as e:
        print(f"명령어 동기화 중 오류 발생: {e}")


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
