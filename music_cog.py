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
    'default_search': 'auto',
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
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --------------------------------------------------------------------
# 3) Music Cog
# --------------------------------------------------------------------
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue = []
        self.current_song = None

    async def check_voice_state(self, interaction: discord.Interaction, voice_client):
        """재생 중인 노래가 없거나 음성 채널에 사용자가 없으면 채널 나가기 및 초기화."""
        if not voice_client.is_playing() and len(voice_client.channel.members) <= 1:
            await voice_client.disconnect()
            self.queue.clear()
            await interaction.channel.send("🔊 음성 채널에서 나갔습니다. 대기열이 초기화되었습니다.")    
    
    async def play_next(self, interaction: discord.Interaction, voice_client):
        if self.queue:
            url = self.queue.pop(0)
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(interaction, voice_client), self.bot.loop).result() if self.queue else None)
            await interaction.channel.send(f"🎵 재생 중: {player.title}")
        else:
            await self.check_voice_state(interaction, voice_client)

    @app_commands.command(name="검색", description="음악을 재생하거나 노래 제목 또는 URL로 검색합니다.")
    async def 검색(self, interaction: discord.Interaction, url: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("🔴 음성 채널에 입장해야 명령어를 사용할 수 있습니다.", ephemeral=True)
            return
        
        balance_manager = self.bot.get_cog("BalanceManager")
        
        await interaction.response.defer()
        channel = interaction.user.voice.channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        try:
            # 음성 채널에 연결
            if not voice_client:
                voice_client = await channel.connect()
            elif voice_client.channel != channel:
                await voice_client.move_to(channel)

            # URL 또는 검색 처리
            if url.startswith("http"):
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(url, download=False)
                )
                if 'entries' in data:
                    for entry in data['entries']:
                        self.queue.append(entry['webpage_url'])
                        
                    # 소지금 추가
                    
                    if balance_manager:
                        balance_manager.add_balance(str(interaction.user.id), 100)

                    await interaction.followup.send(f"🎵 {len(data['entries'])}을 대기열에 추가했습니다. \n💰 {interaction.user.display_name}님의 소지금: {balance_manager.get_balance(interaction.user.id)}원")
                else:
                    self.queue.append(data['webpage_url'])
                        
                    # 소지금 추가
                    if balance_manager:
                        balance_manager.add_balance(str(interaction.user.id), 100)
                        
                    await interaction.followup.send(f"🎵 {data['title']}를 대기열에 추가했습니다. \n💰 {interaction.user.display_name}님의 소지금: {balance_manager.get_balance(interaction.user.id)}원")
            else:
                search_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(f"ytsearch5:{url}", download=False)
                )
                if not search_data.get('entries'):
                    await interaction.followup.send("🔍 검색 결과를 찾을 수 없습니다.", ephemeral=True)
                    return

                options = [discord.SelectOption(label=entry['title'], value=entry['webpage_url'])
                           for entry in search_data['entries'][:5]]
                view = DropdownView(options, interaction, self)
                await interaction.followup.send("🎵 검색 결과를 선택하세요:", view=view)

            if not voice_client.is_playing():
                await self.play_next(interaction, voice_client)

        except Exception as e:
            await interaction.followup.send(f"🔴 오류가 발생했습니다: {e}", ephemeral=True)

    @app_commands.command(name="대기열", description="현재 대기열을 표시합니다.")
    async def 대기열(self, interaction: discord.Interaction):
        if not self.queue:
            await interaction.response.send_message("🎵 대기열이 비어 있습니다.", ephemeral=True)
        else:
            queue_list = "\n".join([f"{i + 1}. {url}" for i, url in enumerate(self.queue)])
            await interaction.response.send_message(f"🎵 현재 대기열:\n{queue_list}")

    @app_commands.command(name="스킵", description="현재 재생 중인 곡을 건너뜁니다.")
    async def 스킵(self, interaction: discord.Interaction):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("🎵 현재 곡을 건너뜁니다.")
        else:
            await interaction.response.send_message("현재 재생 중인 곡이 없습니다.", ephemeral=True)

    @app_commands.command(name="종료", description="재생을 멈추고 음성 채널에서 봇을 퇴장시킵니다.")
    async def 종료(self, interaction: discord.Interaction):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.response.send_message("봇이 음성 채널에서 퇴장했습니다.")
        else:
            await interaction.response.send_message("봇이 음성 채널에 있지 않습니다.", ephemeral=True)

# --------------------------------------------------------------------
# 4) Dropdown 관련 클래스
# --------------------------------------------------------------------
class Dropdown(discord.ui.Select):
    def __init__(self, options, interaction, bot):
        self.interaction = interaction
        self.bot = bot
        super().__init__(placeholder="노래를 선택하세요!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_url = self.values[0]
        self.bot.queue.append(selected_url)
        
        # 소지금 추가
        balance_manager = self.bot.get_cog("BalanceManager")
        if balance_manager:
            balance_manager.add_balance(str(interaction.user.id), 100)
        
        await interaction.response.send_message(f"🎵 {selected_url}이 대기열에 추가되었습니다. \n💰 {interaction.user.display_name}님의 소지금: {balance_manager.get_balance(interaction.user.id)}원")   
        
        voice_client = discord.utils.get(self.bot.bot.voice_clients, guild=interaction.guild)
        if voice_client and not voice_client.is_playing():
            await self.bot.play_next(interaction, voice_client)

class DropdownView(discord.ui.View):
    def __init__(self, options, interaction, bot):
        super().__init__()
        self.add_item(Dropdown(options, interaction, bot))

# --------------------------------------------------------------------
# 5) Cog 로드
# --------------------------------------------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
