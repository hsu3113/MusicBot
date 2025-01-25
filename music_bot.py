import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# 봇 초기화
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")
    print(f"Logged in as {bot.user}")


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
