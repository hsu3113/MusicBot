import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import random
import json

# --------------------------------------------------------------------
# 1) 유튜브DL 관련 옵션 설정
# --------------------------------------------------------------------
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# --------------------------------------------------------------------
# 2) 파일 저장 및 로드 함수
# --------------------------------------------------------------------
BALANCE_FILE = "user_balances.json"

def save_balances():
    with open(BALANCE_FILE, "w") as f:
        json.dump(user_balances, f)

def load_balances():
    global user_balances
    try:
        with open(BALANCE_FILE, "r") as f:
            user_balances = json.load(f)
    except FileNotFoundError:
        user_balances = {}

# --------------------------------------------------------------------
# 3) YTDLSource 클래스
# --------------------------------------------------------------------
class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --------------------------------------------------------------------
# 4) 노래 선택 Dropdown 관련
# --------------------------------------------------------------------
class Dropdown(discord.ui.Select):

    def __init__(self, options, interaction, music_bot):
        self.interaction = interaction
        self.music_bot = music_bot
        super().__init__(placeholder="노래를 선택하세요!",
                         min_values=1,
                         max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_url = self.values[0]
        queue.append(selected_url)

        # 소지금 추가 로직
        user_id = str(interaction.user.id)
        user_balances[user_id] = user_balances.get(user_id, 0) + 100
        save_balances()

        await interaction.response.send_message(f"🎵 대기열에 추가되었습니다: {selected_url}. 현재 소지금: {user_balances[user_id]}원")

        voice_client = discord.utils.get(self.music_bot.bot.voice_clients,
                                         guild=interaction.guild)
        if voice_client and not voice_client.is_playing():
            await self.music_bot.play_next(interaction, voice_client)

class DropdownView(discord.ui.View):

    def __init__(self, options, interaction, music_bot):
        super().__init__()
        self.add_item(Dropdown(options, interaction, music_bot))

# --------------------------------------------------------------------
# 5) 재생 대기열 및 사용자 소지금 데이터
# --------------------------------------------------------------------
queue = []
user_balances = {}
load_balances()

# --------------------------------------------------------------------
# 6) MusicBot Cog
# --------------------------------------------------------------------
class MusicBot(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="검색", description="음악을 재생하거나 노래 제목 또는 URL로 검색합니다.")
    async def 검색(self, interaction: discord.Interaction, query: str):
        # 음성 채널 연결 여부 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("🔴 음성 채널에 입장해야 명령어를 사용할 수 있습니다.", ephemeral=True)
            return

        # Interaction 응답 지연 설정
        await interaction.response.defer()

        try:
            # 봇이 음성 채널에 연결되지 않은 경우 연결
            channel = interaction.user.voice.channel
            voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

            if not voice_client:
                await channel.connect()
            elif voice_client.channel != channel:
                await voice_client.move_to(channel)

            # URL 또는 검색어 처리
            if query.startswith("http"):
                try:
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: ytdl.extract_info(query, download=False)
                    )

                    if 'entries' in data:  # 플레이리스트 처리
                        for entry in data['entries']:
                            queue.append(entry['webpage_url'])

                        # 소지금 추가 로직
                        user_id = str(interaction.user.id)
                        user_balances[user_id] = user_balances.get(user_id, 0) + 100
                        save_balances()

                        await interaction.followup.send(
                            f"🎵 플레이리스트에서 {len(data['entries'])}곡을 대기열에 추가했습니다. 현재 소지금: {user_balances[user_id]}원")
                    else:  # 단일 곡 처리
                        queue.append(data['webpage_url'])

                        # 소지금 추가 로직
                        user_id = str(interaction.user.id)
                        user_balances[user_id] = user_balances.get(user_id, 0) + 100
                        save_balances()

                        await interaction.followup.send(
                            f"🎵 대기열에 추가되었습니다: {data['title']}. 현재 소지금: {user_balances[user_id]}원")

                    if not voice_client.is_playing():
                        await self.play_next(interaction, voice_client)

                except Exception as e:
                    await interaction.followup.send(f"🔴 URL 처리 중 오류가 발생했습니다: {e}", ephemeral=True)

            else:
                # 검색어 처리
                search_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(f"ytsearch5:{query}", download=False)
                )

                if 'entries' not in search_data or not search_data['entries']:
                    await interaction.followup.send("검색 결과를 찾을 수 없습니다.", ephemeral=True)
                    return

                # 검색 결과 옵션 생성
                options = [
                    discord.SelectOption(label=entry['title'], value=entry['webpage_url'])
                    for entry in search_data['entries'][:5]
                ]
                view = DropdownView(options, interaction, music_bot=self)
                await interaction.followup.send("원하는 노래를 선택하세요:", view=view)

        except Exception as e:
            await interaction.followup.send(f"🔴 검색 중 오류가 발생했습니다: {e}", ephemeral=True)

    async def play_next(self, interaction: discord.Interaction, voice_client):
        if queue:
            url = queue.pop(0)
            async with interaction.channel.typing():
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction, voice_client), self.bot.loop).result() if queue else None)

            await interaction.channel.send(f"🎵 재생 중: {player.title}")
        else:
            await voice_client.disconnect()
            await interaction.channel.send("🎵 대기열이 비었습니다. 음성 채널을 떠납니다.")

    @app_commands.command(name="대기열", description="현재 대기열을 표시합니다.")
    async def 대기열(self, interaction: discord.Interaction):
        if not queue:
            await interaction.response.send_message("🎵 현재 대기열이 비어 있습니다.", ephemeral=True)
        else:
            queue_list = "\n".join([f"{i + 1}. {url}" for i, url in enumerate(queue)])
            await interaction.response.send_message(f"🎵 현재 대기열:\n{queue_list}")

    @app_commands.command(name="소지금", description="자신의 소지금을 확인합니다.")
    async def 소지금(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        balance = user_balances.get(user_id, 0)
        await interaction.response.send_message(f"💰 {interaction.user.display_name}님의 소지금: {balance}원")

    @app_commands.command(name="랭킹", description="모두의 소지금을 순서대로 표시합니다.")
    async def 랭킹(self, interaction: discord.Interaction):
        if not user_balances:
            await interaction.response.send_message("아직 등록된 사용자가 없습니다.", ephemeral=True)
        else:
            sorted_balances = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
            ranking_list = "\n".join([
                f"{i + 1}. <@{user_id}>: {balance}원"
                for i, (user_id, balance) in enumerate(sorted_balances)
            ])
            await interaction.response.send_message(f"💰 소지금 랭킹:\n{ranking_list}")

    @app_commands.command(name="송금", description="다른 사용자에게 소지금을 송금합니다.")
    async def 송금(self, interaction: discord.Interaction, 상대방: discord.Member, 금액: int):
        sender_id = str(interaction.user.id)
        receiver_id = str(상대방.id)

        if 금액 <= 0:
            await interaction.response.send_message("🔴 송금 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        sender_balance = user_balances.get(sender_id, 0)

        if sender_balance < 금액:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

        # 송금 처리
        user_balances[sender_id] = sender_balance - 금액
        user_balances[receiver_id] = user_balances.get(receiver_id, 0) + 금액
        save_balances()

        await interaction.response.send_message(
            f"💸 {interaction.user.display_name}님이 {상대방.display_name}님에게 {금액}원을 송금했습니다.\n"
            f"현재 {interaction.user.display_name}님의 소지금: {user_balances[sender_id]}원"
        )
        
    @app_commands.command(name="도박", description="소지금을 걸고 도박을 합니다.")
    async def 도박(self, interaction: discord.Interaction, 금액: int, 종류: str):
        user_id = str(interaction.user.id)
        balance = user_balances.get(user_id, 0)

        if 금액 <= 0:
            await interaction.response.send_message("🔴 베팅 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        if 금액 > balance:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

        if 종류 == "꽃도박":
            grid = [[random.choice(["🌸", "⬜"]) for _ in range(5)] for _ in range(5)]
            flower_count = sum(row.count("🌸") for row in grid)
            if flower_count > 10 :
                multiplier = 1 + flower_count * 0.1
                winnings = int(금액 * multiplier)
            else :
                winnings = 0
            user_balances[user_id] += winnings - 금액
            save_balances()

            grid_display = "\n".join(["".join(row) for row in grid])
            await interaction.response.send_message(
                f"꽃이 10개 이하면 배당금을 모두 잃습니다.\n🌸 꽃도박 결과:\n{grid_display}\n🌸 꽃 개수: {flower_count}\n💰 배당금: {winnings}원\n현재 소지금: {user_balances[user_id]}원"
            )

        elif 종류 == "홀짝":
            outcome = random.choice(["홀수", "짝수"])
            user_choice = "홀수" if 금액 % 2 else "짝수"

            if user_choice == outcome:
                winnings = 금액 * 2
                user_balances[user_id] += winnings - 금액
                result = "승리"
            else:
                user_balances[user_id] -= 금액
                winnings = 0
                result = "패배"

            save_balances()
            await interaction.response.send_message(
                f"배당금의 홀짝에 따라 플레이어의 선택이 결정됩니다.\n🎲 홀짝 결과: {outcome}\n💰 {result}! 배당금: {winnings}원\n현재 소지금: {user_balances[user_id]}원"
            )
        else:
            await interaction.response.send_message("🔴 잘못된 도박 종류입니다. (가능한 종류: 꽃도박, 홀짝)", ephemeral=True)
# --------------------------------------------------------------------
# 봇 초기화
# --------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def setup(bot):
    await bot.add_cog(MusicBot(bot))
