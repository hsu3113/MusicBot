import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# 봇 초기화
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())


@bot.event
async def on_ready():
    # 특정 서버 ID
    GUILD_ID = 629171925976875009  # 테스트할 서버 ID를 입력하세요
    guild = discord.Object(id=GUILD_ID)

    # 특정 서버에서 Slash Command 동기화
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready and online!")



async def main():
    try :
        async with bot:
            # music_cog.py 로드
            await bot.load_extension("music_cog")
            # 토큰으로 봇 시작
            load_dotenv()
            await bot.start(os.getenv("DISCORD_TOKEN"))
            print(f"Discord Token: {DISCORD_TOKEN}")
    except KeyboardInterrupt:
        print("봇이 중단되었습니다.")
    finally:
        await bot.close()  # 봇 종료 처리


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
