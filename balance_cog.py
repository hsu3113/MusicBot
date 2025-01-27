import json
import discord
from discord.ext import commands
from discord import app_commands

# --------------------------------------------------------------------
# 소지금 데이터 파일
# --------------------------------------------------------------------
BALANCE_FILE = "user_balances.json"

# --------------------------------------------------------------------
# BalanceManager Cog
# --------------------------------------------------------------------
class BalanceManager(commands.Cog):
    """
    사용자 소지금을 관리하는 Cog 클래스입니다.
    소지금 확인, 송금, 랭킹 등의 기능을 제공합니다.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_balances = {}  # 사용자 소지금 저장
        self.load_balances()  # 파일에서 소지금 데이터 로드

    # ----------------------------------------------------------------
    # 소지금 데이터 파일 로드 및 저장
    # ----------------------------------------------------------------
    def load_balances(self):
        """소지금을 파일에서 로드합니다."""
        try:
            with open(BALANCE_FILE, "r") as f:
                self.user_balances = json.load(f)
        except FileNotFoundError:
            self.user_balances = {}  # 파일이 없으면 빈 딕셔너리로 초기화

    def save_balances(self):
        """소지금을 파일에 저장합니다."""
        with open(BALANCE_FILE, "w") as f:
            json.dump(self.user_balances, f)

    # ----------------------------------------------------------------
    # 소지금 관리 함수
    # ----------------------------------------------------------------
    def add_balance(self, user_id: str, amount: int):
        """소지금을 추가합니다."""
        self.user_balances[user_id] = self.user_balances.get(user_id, 0) + amount
        self.save_balances()

    def get_balance(self, user_id: str) -> int:
        """현재 소지금을 반환합니다."""
        return self.user_balances.get(user_id, 0)

    # ----------------------------------------------------------------
    # Discord 명령어
    # ----------------------------------------------------------------

    @app_commands.command(name="소지금", description="자신의 소지금을 확인합니다.")
    async def check_balance(self, interaction: discord.Interaction):
        """사용자가 자신의 소지금을 확인합니다."""
        user_id = str(interaction.user.id)
        balance = self.get_balance(user_id)
        await interaction.response.send_message(
            f"💰 {interaction.user.display_name}님의 소지금: {balance}원"
        )

    @app_commands.command(name="송금", description="다른 사용자에게 소지금을 송금합니다.")
    async def 송금(self, interaction: discord.Interaction, 상대방: discord.Member, 금액: int):
        """
        다른 사용자에게 소지금을 송금합니다.

        Args:
            상대방 (discord.Member): 송금을 받을 사용자.
            금액 (int): 송금할 금액.
        """
        sender_id = str(interaction.user.id)
        receiver_id = str(상대방.id)

        # 금액 유효성 검사
        if 금액 <= 0:
            await interaction.response.send_message("🔴 송금 금액은 0원 이상이어야 합니다.", ephemeral=True)
            return

        sender_balance = self.get_balance(sender_id)

        # 소지금 확인
        if sender_balance < 금액:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return

        # 송금 처리
        self.user_balances[sender_id] = sender_balance - 금액
        self.user_balances[receiver_id] = self.get_balance(receiver_id) + 금액
        self.save_balances()

        await interaction.response.send_message(
            f"💸 {interaction.user.display_name}님이 {상대방.display_name}님에게 {금액}원을 송금했습니다.\n"
            f"현재 {interaction.user.display_name}님의 소지금: {self.user_balances[sender_id]}원"
        )

    @app_commands.command(name="랭킹", description="모두의 소지금을 순서대로 표시합니다.")
    async def 랭킹(self, interaction: discord.Interaction):
        """모든 사용자의 소지금을 랭킹 형식으로 표시합니다."""
        if not self.user_balances:
            await interaction.response.send_message("아직 등록된 사용자가 없습니다.", ephemeral=True)
        else:
            # 소지금을 기준으로 내림차순 정렬
            sorted_balances = sorted(
                self.user_balances.items(), key=lambda x: x[1], reverse=True
            )
            ranking_list = "\n".join([
                f"{i + 1}. <@{user_id}>: {balance}원"
                for i, (user_id, balance) in enumerate(sorted_balances)
            ])
            await interaction.response.send_message(f"💰 소지금 랭킹:\n{ranking_list}")

# --------------------------------------------------------------------
# Cog 로드
# --------------------------------------------------------------------
async def setup(bot: commands.Bot):
    """
    BalanceManager Cog를 로드합니다.
    """
    await bot.add_cog(BalanceManager(bot))
