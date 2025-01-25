import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import random

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
    'default_search': 'ytsearch3',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# --------------------------------------------------------------------
# 2) YTDLSource 클래스
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
# 3) 노래 선택 Dropdown 관련
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
# 4) 재생 대기열 및 사용자 소지금 데이터
# --------------------------------------------------------------------
queue = []
user_balances = {}  # 사용자 소지금을 저장하는 딕셔너리

# --------------------------------------------------------------------
# 5) MusicBot Cog
# --------------------------------------------------------------------
class MusicBot(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="검색", description="음악을 재생하거나 노래 제목 또는 URL로 검색합니다.")
    async def 검색(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()  # Interaction 응답 지연 설정

        if not interaction.user.voice:
            await interaction.followup.send("먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if not voice_client:
            try:
                voice_client = await channel.connect()
                await interaction.followup.send("음성 채널에 연결되었습니다. 검색을 시작합니다.")
            except Exception as e:
                await interaction.followup.send("🔴 음성 채널에 연결할 수 없습니다. 다시 시도해주세요.", ephemeral=True)
                return

        # YouTube 검색
        try:
            search_data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ytdl.extract_info(f"ytsearch5:{query}", download=False)
            )

            if 'entries' not in search_data or not search_data['entries']:
                await interaction.followup.send("검색 결과를 찾을 수 없습니다.", ephemeral=True)
                return

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

    @app_commands.command(name="도박", description="소지금을 걸고 도박을 합니다.")
    async def 도박(self, interaction: discord.Interaction, 금액: int):
        user_id = str(interaction.user.id)
        balance = user_balances.get(user_id, 0)

        if 금액 <= 0:
            await interaction.response.send_message("🔴 베팅 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        if 금액 > balance:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

        outcome = random.choice(["win", "lose"])
        if outcome == "win":
            winnings = 금액 * 2
            user_balances[user_id] += 금액
            await interaction.response.send_message(f"🎉 축하합니다! {금액}원을 베팅하여 {winnings}원을 얻었습니다! 현재 소지금: {user_balances[user_id]}원")
        else:
            user_balances[user_id] -= 금액
            await interaction.response.send_message(f"💔 아쉽게도 {금액}원을 잃었습니다. 현재 소지금: {user_balances[user_id]}원")

    @app_commands.command(name="스킵", description="현재 재생 중인 곡을 건너뜁니다.")
    async def 스킵(self, interaction: discord.Interaction):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("🎵 현재 곡을 건너뜁니다.")
        else:
            await interaction.response.send_message("재생 중인 곡이 없습니다.", ephemeral=True)

