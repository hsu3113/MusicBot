import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

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
        print("Dropdown callback triggered.")
        selected_url = self.values[0]
        queue.append(selected_url)

        await interaction.response.send_message(f"🎵 대기열에 추가되었습니다: {selected_url}")

        voice_client = discord.utils.get(self.music_bot.bot.voice_clients,
                                         guild=interaction.guild)
        if voice_client and not voice_client.is_playing():
            await self.music_bot.play_next(interaction, voice_client)

class DropdownView(discord.ui.View):

    def __init__(self, options, interaction, music_bot):
        super().__init__()
        self.add_item(Dropdown(options, interaction, music_bot))

# --------------------------------------------------------------------
# 4) 재생 대기열 (전역 리스트)
# --------------------------------------------------------------------
queue = []

# --------------------------------------------------------------------
# 5) MusicBot Cog
# --------------------------------------------------------------------
class MusicBot(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="검색", description="음악을 재생하거나 노래 제목 또는 URL로 검색합니다.")
    async def 검색(self, interaction: discord.Interaction, query: str):
        print(f"/검색 command triggered by {interaction.user}. Query: {query}")

        if not interaction.user.voice:
            print("User is not in a voice channel.")
            await interaction.response.send_message("먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if not voice_client:
            print("Bot is not connected to a voice channel. Connecting now...")
            try:
                print(f"Attempting to connect to channel: {channel.name} (ID: {channel.id})")
                voice_client = await channel.connect(timeout=10.0)  # 타임아웃 설정
                print(f"Successfully connected to the voice channel: {channel.name}")
            except discord.ClientException as e:
                print(f"ClientException: {e}")
                await interaction.followup.send("🔴 음성 채널에 연결할 수 없습니다. 이미 연결되어 있거나 다른 문제가 발생했습니다.", ephemeral=True)
                return
            except discord.InvalidArgument as e:
                print(f"InvalidArgument: {e}")
                await interaction.followup.send("🔴 잘못된 음성 채널 정보입니다. 다시 시도해주세요.", ephemeral=True)
                return
            except asyncio.TimeoutError:
                print("TimeoutError: Connection to the voice channel timed out.")
                await interaction.followup.send("🔴 음성 채널에 연결하는 데 시간이 초과되었습니다.", ephemeral=True)
                return
            except Exception as e:
                print(f"Unexpected error during connection: {e}")
                await interaction.followup.send("🔴 음성 채널에 연결 중 문제가 발생했습니다.", ephemeral=True)
                return
        
        await interaction.followup.send("봇이 음성 채널에 연결되었습니다.")


        await interaction.response.defer()
        print("Deferred interaction response.")

        if query.startswith("http"):
            try:
                print("Processing URL...")
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False))
                print(f"URL data fetched: {data}")

                if 'entries' in data:
                    for entry in data['entries']:
                        queue.append(entry['webpage_url'])
                    await interaction.followup.send(f"🎵 플레이리스트에서 {len(data['entries'])}곡을 대기열에 추가했습니다.")
                else:
                    queue.append(data['webpage_url'])
                    await interaction.followup.send(f"🎵 대기열에 추가되었습니다: {data['title']}")

                if not voice_client.is_playing():
                    await self.play_next(interaction, voice_client)

            except Exception as e:
                print(f"Error processing URL: {e}")
                await interaction.followup.send(f"🔴 URL 처리 중 오류가 발생했습니다: {e}", ephemeral=True)

        else:
            try:
                print("Processing search query...")
                search_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(f"ytsearch5:{query}", download=False))
                print(f"Search data fetched: {search_data}")

                if 'entries' not in search_data or not search_data['entries']:
                    print("No search results found.")
                    await interaction.followup.send("검색 결과를 찾을 수 없습니다.", ephemeral=True)
                    return

                options = [
                    discord.SelectOption(label=entry['title'], value=entry['webpage_url'])
                    for entry in search_data['entries'][:5]
                ]

                view = DropdownView(options, interaction, music_bot=self)
                await interaction.followup.send("원하는 노래를 선택하세요:", view=view)

            except Exception as e:
                print(f"Error processing search query: {e}")
                await interaction.followup.send(f"🔴 검색 중 오류가 발생했습니다: {e}", ephemeral=True)

    async def play_next(self, interaction: discord.Interaction, voice_client):
        print("play_next called.")
        if queue:
            url = queue.pop(0)
            print(f"Playing next song: {url}")
            async with interaction.channel.typing():
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction, voice_client), self.bot.loop).result() if queue else None)

            await interaction.channel.send(f"🎵 재생 중: {player.title}")
        else:
            print("Queue is empty. Disconnecting...")
            await voice_client.disconnect()
            await interaction.channel.send("🎵 대기열이 비었습니다. 음성 채널을 떠납니다.")

    @app_commands.command(name="대기열", description="현재 대기열을 표시합니다.")
    async def 대기열(self, interaction: discord.Interaction):
        print("/대기열 command triggered.")
        if not queue:
            await interaction.response.send_message("🎵 현재 대기열이 비어 있습니다.", ephemeral=True)
        else:
            queue_list = "\n".join([f"{i + 1}. {url}" for i, url in enumerate(queue)])
            await interaction.response.send_message(f"🎵 현재 대기열:\n{queue_list}")

    @app_commands.command(name="스킵", description="현재 재생 중인 곡을 건너뜁니다.")
    async def 스킵(self, interaction: discord.Interaction):
        print("/스킵 command triggered.")
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if voice_client and voice_client.is_playing():
            print("Skipping current song.")
            voice_client.stop()
            await interaction.response.send_message("🎵 현재 곡을 건너뜁니다.")
        else:
            print("No song is currently playing.")
            await interaction.response.send_message("재생 중인 곡이 없습니다.", ephemeral=True)

    @app_commands.command(name="종료", description="재생을 멈추고 음성 채널에서 봇을 퇴장시킵니다.")
    async def 종료(self, interaction: discord.Interaction):
        print("/종료 command triggered.")
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if voice_client and voice_client.is_connected():
            print("Disconnecting from voice channel.")
            await voice_client.disconnect()
            await interaction.response.send_message("음악을 멈추고 봇이 퇴장했습니다.")
        else:
            print("Bot is not connected to any voice channel.")
            await interaction.response.send_message("봇이 음성 채널에 있지 않습니다.", ephemeral=True)

# --------------------------------------------------------------------
# 6) Cog 로드 함수 (필수)
# --------------------------------------------------------------------
async def setup(bot: commands.Bot):
    print("Loading MusicBot cog...")
    await bot.add_cog(MusicBot(bot))
    print("MusicBot cog loaded.")
