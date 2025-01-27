import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# --------------------------------------------------------------------
# .env 파일에서 환경 변수 로드
# --------------------------------------------------------------------
load_dotenv()

# DISCORD_TOKEN 가져오기
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN이 .env 파일에 정의되어 있지 않습니다.")
print("✅ DISCORD_TOKEN이 로드되었습니다.")

# --------------------------------------------------------------------
# 봇 초기화
# --------------------------------------------------------------------
# Discord 봇의 권한 설정 (애플리케이션 명령어 및 메시지 내용 접근 허용)
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 접근 허용 (필요한 경우 활성화)

# 봇 인스턴스 생성
bot = commands.Bot(command_prefix="/", intents=intents)

# --------------------------------------------------------------------
# 리로드 명령어
# --------------------------------------------------------------------
@bot.command(name="리로드", help="특정 코그를 다시 로드합니다.")
@commands.is_owner()  # 봇 소유자만 사용 가능
async def reload_cog(ctx, cog_name: str):
    """특정 코그를 다시 로드합니다."""
    try:
        await bot.reload_extension(cog_name)  # 코그 리로드
        await ctx.send(f"✅ **{cog_name}** 코그가 성공적으로 다시 로드되었습니다.")
        print(f"✅ {cog_name} 코그가 다시 로드되었습니다.")
    except commands.ExtensionNotLoaded:
        await ctx.send(f"⚠️ **{cog_name}** 코그가 로드되지 않았습니다.")
        print(f"⚠️ {cog_name} 코그가 로드되지 않았습니다.")
    except commands.ExtensionNotFound:
        await ctx.send(f"⚠️ **{cog_name}** 코그를 찾을 수 없습니다.")
        print(f"⚠️ {cog_name} 코그를 찾을 수 없습니다.")
    except Exception as e:
        await ctx.send(f"❌ 코그를 다시 로드하는 중 오류가 발생했습니다: {e}")
        print(f"❌ 코그 로드 중 오류 발생: {e}")

# --------------------------------------------------------------------
# 봇 이벤트: on_ready
# --------------------------------------------------------------------
@bot.event
async def on_ready():
    """봇이 준비되었을 때 호출."""
    try:
        # 글로벌 명령어 동기화
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}개의 명령어가 글로벌로 동기화되었습니다.")
    except Exception as e:
        print(f"❌ 글로벌 명령어 동기화 실패: {e}")

    print(f"🟢 Logged in as {bot.user}")  # 봇이 성공적으로 로그인했음을 표시


# --------------------------------------------------------------------
# 메인 실행 함수
# --------------------------------------------------------------------
async def main():
    """봇 실행을 관리하는 메인 함수."""
    try:
        # 로드할 확장(코그) 목록
        extensions = ["balance_cog", "music_cog", "gamble_cog", "stock_cog"]

        # 봇 실행을 비동기로 관리
        async with bot:
            # 확장 로드
            for extension in extensions:
                try:
                    await bot.load_extension(extension)
                    print(f"✅ {extension}이(가) 로드되었습니다.")
                except Exception as e:
                    print(f"❌ {extension} 로드 실패: {e}")

            # 봇 시작
            await bot.start(DISCORD_TOKEN)

    except KeyboardInterrupt:
        print("🔴 봇이 중단되었습니다.")  # Ctrl+C로 종료한 경우 표시
    finally:
        # 봇 종료 처리
        await bot.close()
        print("🔴 봇이 종료되었습니다.")


# --------------------------------------------------------------------
# 스크립트의 진입점
# --------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main()) # 메인 함수 실행
    except KeyboardInterrupt:
        print("\n🔴 프로그램 종료(Ctrl+C).")
