from discord.ext import commands
from discord import app_commands
import discord
import random

class Gamble(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
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
        
        # BalanceManager 가져오기
        balance_manager = self.bot.get_cog("BalanceManager")
        if not balance_manager:
            await interaction.response.send_message("🔴 BalanceManager가 로드되지 않았습니다. 도박을 진행할 수 없습니다.", ephemeral=True)
            return
        
        # 유저 소지금 확인 및 로직
        user_id = str(interaction.user.id)
        balance = balance_manager.get_balance(user_id)

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
            result = "승리 🎉"
        else:
            winnings = 0
            result = "패배 ❌"
        balance_manager.add_balance(user_id, winnings - 베팅_금액)
        balance_manager.save_balances()

        # 깔끔한 출력 메시지 생성
        message = (
            f"🎲 **홀짝 도박 결과** 🎲\n"
            f"🔹 **플레이어의 선택:** {player_choice}\n"
            f"🔹 **결과:** {outcome}\n"
            f"🔹 **결과 판정:** {result}\n"
            f"💰 **당첨금:** {winnings}원\n"
            f"💵 **현재 소지금:** {balance_manager.get_balance(user_id)}원"
        )

        await interaction.response.send_message(message)

    @app_commands.command(name="꽃도박", description="꽃도박을 실행합니다.")
    async def 꽃도박(self, interaction: discord.Interaction, 베팅_금액: int):
        
        # BalanceManager 가져오기
        balance_manager = self.bot.get_cog("BalanceManager")
        if not balance_manager:
            await interaction.response.send_message("🔴 BalanceManager가 로드되지 않았습니다. 도박을 진행할 수 없습니다.", ephemeral=True)
            return
        
        # 유저 소지금 확인 및 로직
        user_id = str(interaction.user.id)
        balance = balance_manager.get_balance(user_id)

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
        elif flower_count == 25:
            multiplier = 1000
        elif flower_count >= 8:
            multiplier = 25

        winnings = int(베팅_금액 * multiplier)

        if multiplier == 0 :
            result_message = "❌ 돈을 모두 잃었습니다. ㅠㅠ"
        elif multiplier == 1:
            result_message = f"🌸 1배 🌸"
        else:
            result_message = f"🎉 {multiplier}배 당첨 🎉"
            
            
        balance_manager.add_balance(user_id, winnings - 베팅_금액)
        balance_manager.save_balances()

        # 격자 출력 메시지 생성
        grid_display = "\n".join(["".join(row) for row in grid])
        message = (
            f"🌸 **꽃도박 결과** 🌸\n{grid_display}\n"
            f"🔹 **꽃 개수:** {flower_count}\n"
            f"🔹 **결과:** {result_message}\n"
            f"💰 **당첨금:** {winnings}원\n"
            f"💵 **현재 소지금:** {balance_manager.get_balance(user_id)}원"
        )
    
        await interaction.response.send_message(message)

    @app_commands.command(name="투표시작", description="투표를 시작합니다. 사용법: /투표시작 제목 선택지1 선택지2 ... (최대 5개)")
    async def 투표시작(self, interaction: discord.Interaction, 제목: str, 선택1: str, 선택2: str, 선택3: str = None, 선택4: str = None, 선택5: str = None):        
        try:
            await interaction.response.defer()
            # 관리자 권한 확인
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("🔴 이 명령어를 실행하려면 관리자 권한이 필요합니다.", ephemeral=True)
                return
    
            # 투표 시작 코드
            options = [선택1, 선택2]
            if 선택3:
                options.append(선택3)
            if 선택4:
                options.append(선택4)
            if 선택5:
                options.append(선택5)
    
            self.current_vote = {
                "title": 제목,
                "options": options,
                "bets": {option: {"total": 0, "users": {}} for option in options},
                "active": True
            }
    
            options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
            await interaction.followup.send(
                f"🗳️ 투표가 시작되었습니다!\n**제목**: {제목}\n**선택지**:\n{options_text}\n"
                f"베팅하려면 `/베팅 <선택지번호> <금액>`을 사용하세요."
            )
        except Exception as e:
            await interaction.followup.send(f"🔴 투표 생성 중 오류가 발생했습니다: {e}", ephemeral=True)
            print(f"[ERROR] 투표시작 오류: {e}")
    
    @app_commands.command(name="베팅", description="베팅을 진행합니다. 사용법: /베팅 선택지번호 금액")
    async def 베팅(self, interaction: discord.Interaction, 선택지번호: int, 금액: int):
        """
        베팅을 진행합니다. 사용법: /베팅 선택지번호 금액
        """
        # BalanceManager 가져오기
        balance_manager = self.bot.get_cog("BalanceManager")
        if not balance_manager:
            await interaction.response.send_message("🔴 BalanceManager가 로드되지 않았습니다. 베팅을 진행할 수 없습니다.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
    
        # 진행 중인 투표 확인
        if not self.current_vote or not self.current_vote["active"]:
            await interaction.response.send_message("현재 진행 중인 투표가 없습니다!", ephemeral=True)
            return
    
        # 선택지 유효성 확인
        if 선택지번호 < 1 or 선택지번호 > len(self.current_vote["options"]):
            await interaction.response.send_message("유효한 선택지 번호를 입력하세요.", ephemeral=True)
            return
    
        # 베팅 금액 확인
        if 금액 <= 0:
            await interaction.response.send_message("베팅 금액은 1 이상이어야 합니다.", ephemeral=True)
            return
    
        # 사용자의 소지금 확인
        balance = balance_manager.get_balance(user_id)
        if 금액 > balance:
            await interaction.response.send_message("🔴 소지금이 부족합니다.", ephemeral=True)
            return
    
        # 선택지 및 사용자 ID 확인
        선택지 = self.current_vote["options"][선택지번호 - 1]
    
        # 소지금 차감
        balance_manager.add_balance(user_id, -금액)
        balance_manager.save_balances()
    
        # 베팅 데이터 업데이트
        self.current_vote["bets"][선택지]["users"][user_id] = self.current_vote["bets"][선택지]["users"].get(user_id, 0) + 금액
        self.current_vote["bets"][선택지]["total"] += 금액
    
        # 베팅 비율 계산
        total_bets = sum(option_data["total"] for option_data in self.current_vote["bets"].values())
        bet_ratios = {
            opt: round((data["total"] / total_bets) * 100, 2) if total_bets > 0 else 0
            for opt, data in self.current_vote["bets"].items()
        }
    
        # 상태 메시지
        await interaction.response.send_message(
            f"✅ {interaction.user.mention}님이 **{선택지}**에 {금액}원을 베팅했습니다.\n"
            f"현재 베팅 비율:\n" +
            "\n".join([f"{opt}: {ratio}%" for opt, ratio in bet_ratios.items()]) +
            f"\n💰 남은 소지금: {balance_manager.get_balance(user_id)}원"
        )

    
    @app_commands.command(name="투표종료", description="현재 진행 중인 투표를 종료합니다.")
    async def 투표종료(self, interaction: discord.Interaction, 우승_선택지: str = None):
        """현재 투표를 종료합니다."""
        
        # 관리자 권한 확인
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔴 이 명령어를 실행하려면 관리자 권한이 필요합니다.", ephemeral=True)
            return
    
        if not self.current_vote or not self.current_vote["active"]:
            await interaction.response.send_message("현재 진행 중인 투표가 없습니다!", ephemeral=True)
            return
        
         # BalanceManager 가져오기
        balance_manager = self.bot.get_cog("BalanceManager")
        if not balance_manager:
            await interaction.response.send_message("🔴 BalanceManager가 로드되지 않았습니다. 투표를 종료할 수 없습니다.", ephemeral=True)
            return
        
        # 최종 결과 계산
        total_bets = sum(option_data["total"] for option_data in self.current_vote["bets"].values())
        results = {
            opt: {"total": data["total"], "ratio": round((data["total"] / total_bets) * 100, 2) if total_bets > 0 else 0}
            for opt, data in self.current_vote["bets"].items()
        }
    
        # 우승 선택지 설정
        if 우승_선택지:
            if 우승_선택지 not in self.current_vote["options"]:
                await interaction.response.send_message(f"🔴 '{우승_선택지}'는 유효한 선택지가 아닙니다. 유효한 선택지: {', '.join(self.current_vote['options'])}", ephemeral=True)
                return
            winning_option = 우승_선택지
        else:
            # 베팅 금액이 가장 높은 선택지를 자동으로 우승으로 설정
            winning_option = max(results, key=lambda x: results[x]["total"])
        
        
        # 투표 종료 처리
        self.current_vote["active"] = False
        
        # 우승자에게 상금 분배
        winners = self.current_vote["bets"][winning_option]["users"]
        total_bet_on_winner = self.current_vote["bets"][winning_option]["total"]
        payout_message = "💸 **우승자 배당금:**\n"
    
        for user_id, bet_amount in winners.items():
            payout_ratio = bet_amount / total_bet_on_winner
            winnings = int(total_bets * payout_ratio)
            
            balance_manager.add_balance(user_id, winnings)
            payout_message += f"<@{user_id}>: +{winnings}원 (베팅: {bet_amount}원)\n"

        balance_manager.save_balances()   
         
        # 결과 메시지 생성
        result_text = "\n".join([f"{opt}: {data['total']}원 ({data['ratio']}%)" for opt, data in results.items()])
        await interaction.response.send_message(
            f"🛑 투표가 종료되었습니다!\n**결과**:\n{result_text}\n\n**우승 선택지:** {winning_option}\n\n{payout_message}"
        )
        
        # 투표 데이터 초기화
        self.current_vote = None
# --------------------------------------------------------------------
# Cog 로드
# --------------------------------------------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Gamble(bot))