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
        self.current_vote = None
        
    async def check_voice_state(self, voice_client):
        """재생 중인 노래가 없거나 음성 채널에 사용자가 없으면 채널 나가기 및 초기화."""
        if not voice_client.is_playing() and len(voice_client.channel.members) <= 1:
            await voice_client.disconnect()
            self.queue.clear()
            print("🔊 음성 채널에서 나갔습니다. 대기열이 초기화되었습니다.")
            
    @app_commands.command(name="검색", description="음악을 재생하거나 노래 제목 또는 url로 검색합니다.")
    async def 검색(self, interaction: discord.Interaction, url: str):
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

            # url 또는 검색어 처리
            if url.startswith("http"):
                try:
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: ytdl.extract_info(url, download=False)
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
                    await interaction.followup.send(f"🔴 url 처리 중 오류가 발생했습니다: {e}", ephemeral=True)

            else:
                # 검색어 처리
                search_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(f"ytsearch5:{url}", download=False)
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
            # 재생할 노래가 없으면 상태 확인 후 채널 나가기
            await self.check_voice_state(voice_client)

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

    @app_commands.command(name="스킵", description="현재 재생 중인 곡을 건너뜁니다.")
    async def 스킵(self, interaction: discord.Interaction):
        voice_client = discord.utils.get(self.bot.voice_clients,
                                         guild=interaction.guild)

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("🎵 현재 곡을 건너뜁니다.")
        else:
            await interaction.response.send_message("재생 중인 곡이 없습니다.",
                                                    ephemeral=True)

    @app_commands.command(name="종료", description="재생을 멈추고 음성 채널에서 봇을 퇴장시킵니다.")
    async def 종료(self, interaction: discord.Interaction):
        voice_client = discord.utils.get(self.bot.voice_clients,
                                         guild=interaction.guild)

        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.response.send_message("음악을 멈추고 봇이 퇴장했습니다.")
        else:
            await interaction.response.send_message("봇이 음성 채널에 있지 않습니다.",
                                                    ephemeral=True)
    
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
            , ephemeral=True
        )
    
    
    
    # 도박
    @app_commands.command(name="도박", description="사용 가능한 도박 종류를 알려줍니다.")
    async def 도박(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🎲 사용 가능한 도박 명령어:\n- 홀짝\n- 꽃도박\n- 설명"
            , ephemeral=True
        )

    @app_commands.command(name="설명", description="도박에 대한 설명을 제공합니다.")
    async def 홀짝_설명(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🎲 홀짝 도박:\n베팅 금액이 홀수면 플레이어의 선택은 자동으로 홀수, 짝수면 짝수로 설정됩니다.\n맞추면 베팅 금액의 2배를 얻습니다."
            f"\n🌸 꽃도박:\n5x5 격자에서 일정 확률로 꽃이 생성됩니다.\n꽃의 개수에 따라 배당금이 결정됩니다:\n- 0~1개: 0배\n- 2개: 1배\n- 3개: 1.5배\n- 4개: 0배\n- 5개: 2.5배\n- 6~7개: 5배\n- 8개: 25배"
        )

    @app_commands.command(name="홀짝", description="홀짝 도박을 실행합니다.")
    async def 홀짝(self, interaction: discord.Interaction, 베팅_금액: int):
        user_id = str(interaction.user.id)
        balance = user_balances.get(user_id, 0)

        if 베팅_금액 <= 0:
            await interaction.response.send_message("🔴 베팅 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        if 베팅_금액 > balance:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

        # 베팅 금액의 홀짝으로 플레이어 선택 설정
        player_choice = "홀수" if 베팅_금액 % 2 else "짝수"
        outcome = random.choice(["홀수", "짝수"])

        if player_choice == outcome:
            winnings = 베팅_금액 * 2
            user_balances[user_id] += winnings - 베팅_금액
            result = "승리 🎉"
        else:
            user_balances[user_id] -= 베팅_금액
            winnings = 0
            result = "패배 ❌"

        save_balances()

        # 깔끔한 출력 메시지 생성
        message = (
            f"🎲 **홀짝 도박 결과** 🎲\n"
            f"🔹 **플레이어의 선택:** {player_choice}\n"
            f"🔹 **결과:** {outcome}\n"
            f"🔹 **결과 판정:** {result}\n"
            f"💰 **배당금:** {winnings}원\n"
            f"💵 **현재 소지금:** {user_balances[user_id]}원"
        )

        await interaction.response.send_message(message)

    @app_commands.command(name="꽃도박", description="꽃도박을 실행합니다.")
    async def 꽃도박(self, interaction: discord.Interaction, 베팅_금액: int):
        user_id = str(interaction.user.id)
        balance = user_balances.get(user_id, 0)

        if 베팅_금액 <= 0:
            await interaction.response.send_message("🔴 베팅 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        if 베팅_금액 > balance:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

            # 꽃 개수 계산 (5x5 격자에서 10% 확률로 꽃 생성)
        grid = [[random.choice(["🌸", "⬜"]) if random.random() < 0.1 else "⬜" for _ in range(5)] for _ in range(5)]
        flower_count = sum(row.count("🌸") for row in grid)

        multiplier = 0
        if flower_count == 2:
            multiplier = 1
        elif flower_count == 3:
            multiplier = 1.5
        elif flower_count == 5:
            multiplier = 2.5
        elif 6 <= flower_count <= 7:
            multiplier = 5
        elif flower_count == 8:
            multiplier = 25

        winnings = int(베팅_금액 * multiplier)

        if multiplier == 0:
            user_balances[user_id] -= 베팅_금액
            result_message = "🌸 배당금이 없습니다."
        else:
            user_balances[user_id] += winnings - 베팅_금액
            result_message = f"🌸 배당금: {winnings}원"

        save_balances()

        # 격자 출력 메시지 생성
        grid_display = "\n".join(["".join(row) for row in grid])
        message = (
            f"🌸 **꽃도박 결과** 🌸\n"
            f"🔹 **꽃 격자:**\n{grid_display}\n"
            f"🔹 **꽃 개수:** {flower_count}\n"
            f"🔹 **결과:** {result_message}\n"
            f"💵 **현재 소지금:** {user_balances[user_id]}원"
        )
    
        await interaction.response.send_message(message)

    @app_commands.command(name="투표시작", description="투표를 시작합니다. 사용법: /투표시작 제목 선택지1 선택지2 ... (최대 5개)")
    async def 투표시작(self, interaction: discord.Interaction, 제목: str, *선택지: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔴 이 명령어를 실행하려면 관리자 권한이 필요합니다.", ephemeral=True)
            return
        if self.current_vote and self.current_vote["active"]:
            await ctx.send("이미 진행 중인 투표가 있습니다! /투표종료 후 다시 시도하세요.")
            return
    
        if len(options) > 5:
            await ctx.send("선택지는 최대 5개까지만 가능합니다.")
            return
    
        # 투표 데이터 초기화
        self.current_vote = {
            "title": title,
            "options": list(options),
            "bets": {option: {"total": 0, "users": {}} for option in options},
            "active": True
        }
    
        # 투표 시작 메시지
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        await ctx.send(f"🗳️ 투표가 시작되었습니다!\n**제목**: {title}\n**선택지**:\n{options_text}\n베팅하려면 `/베팅 <선택지번호> <금액>`을 사용하세요.")
        
    @app_commands.command(name="베팅")
    async def 베팅(ctx, option_number: int, amount: int):
        """베팅을 진행합니다. 사용법: /베팅 선택지번호 금액"""
    
        if not self.current_vote or not self.current_vote["active"]:
            await ctx.send("현재 진행 중인 투표가 없습니다!")
            return

        if option_number < 1 or option_number > len(self.current_vote["options"]):
            await ctx.send("유효한 선택지 번호를 입력하세요.")
            return

        if amount <= 0:
            await ctx.send("베팅 금액은 1 이상이어야 합니다.")
            return
    
        # 선택지와 사용자 ID 확인
        user_id = str(ctx.author.id)
        option = self.current_vote["options"][option_number - 1]
    
        # 베팅 금액 추가
        self.current_vote["bets"][option]["users"][user_id] = self.current_vote["bets"][option]["users"].get(user_id, 0) + amount
        self.current_vote["bets"][option]["total"] += amount
    
        # 베팅 비율 계산
        total_bets = sum(option_data["total"] for option_data in self.current_vote["bets"].values())
        bet_ratios = {opt: round((data["total"] / total_bets) * 100, 2) if total_bets > 0 else 0 for opt, data in self.current_vote["bets"].items()}
    
        # 베팅 상태 메시지
        await ctx.send(f"✅ {ctx.author.mention}님이 **{option}**에 {amount}원을 베팅했습니다.\n현재 베팅 비율:\n" +
                       "\n".join([f"{opt}: {ratio}%" for opt, ratio in bet_ratios.items()]))

    @app_commands.command(name="투표종료")
    async def 투표종료(self, interaction: discord.Interaction, ctx):
        """현재 투표를 종료합니다."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔴 이 명령어를 실행하려면 관리자 권한이 필요합니다.", ephemeral=True)
            return
        if not self.current_vote or not self.current_vote["active"]:
            await ctx.send("현재 진행 중인 투표가 없습니다!")
            return
    
        # 투표 종료 처리
        self.current_vote["active"] = False
    
        # 최종 결과 계산
        total_bets = sum(option_data["total"] for option_data in self.current_vote["bets"].values())
        results = {opt: {"total": data["total"], "ratio": round((data["total"] / total_bets) * 100, 2) if total_bets > 0 else 0}
                   for opt, data in self.current_vote["bets"].items()}
    
        # 결과 메시지
        result_text = "\n".join([f"{opt}: {data['total']}원 ({data['ratio']}%)" for opt, data in results.items()])
        await ctx.send(f"🛑 투표가 종료되었습니다!\n**결과**:\n{result_text}")
    
        # 투표 데이터 초기화
        self.current_vote = None



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
