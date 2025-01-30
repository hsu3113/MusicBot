import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import os
import random
import json

# --------------------------------------------------------------------
# 파일 및 설정
# --------------------------------------------------------------------
STOCK_FILE = "stock_data.json"  # 주식 데이터 저장 파일
BALANCE_FILE = "user_balances.json"  # 사용자 잔액 데이터 파일
PORTFOLIO_FILE = "user_portfolios.json"  # 사용자 포트폴리오 데이터 파일
MAX_STOCKS = 10  # 최대 상장 주식 수

# --------------------------------------------------------------------
# StockMarket Cog
# --------------------------------------------------------------------
class StockMarket(commands.Cog):
    """
    Discord 주식 시장 Cog 클래스입니다.
    주식 가격 업데이트, 매수/매도, 포트폴리오 관리 기능을 제공합니다.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stocks = {}  # 주식 가격 정보
        self.user_portfolios = {}  # 사용자별 주식 보유 정보
        self.load_data()  # 초기 데이터 로드
        self.price_updater.start()  # 주기적인 주식 가격 업데이트
        self.daily_update.start()  # 매일 새로운 주식 추가 및 정리
    
    def stop_tasks(self):
        """모든 tasks.loop를 안전하게 종료."""
        if self.price_updater.is_running():
            self.price_updater.cancel()
            print("🛑 price_updater를 종료하였습니다.")
            
        if self.daily_update.is_running():
            self.daily_update.cancel()
            print("🛑 daily_update를 종료하였습니다.")

    async def cog_unload(self):
        """Cog가 언로드될 때 호출."""
        self.stop_tasks()
        print("🛑 Cog unloaded and tasks stopped.")
        
    # ----------------------------------------------------------------
    # 데이터 로드 및 저장
    # ----------------------------------------------------------------
    def load_data(self):
        """파일에서 주식 및 사용자 데이터를 로드합니다."""
        try:
            with open(STOCK_FILE, "r") as f:
                self.stocks = json.load(f)
        except FileNotFoundError:
            self.stocks = {"AAPL": 100, "TSLA": 200, "GOOGL": 150}  # 기본 주식 데이터
            
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                self.user_portfolios = json.load(f)
        except FileNotFoundError:
            self.user_portfolios = {}

    def save_data(self):
        """현재 데이터를 파일에 저장합니다."""
        with open(STOCK_FILE, "w") as f:
            json.dump(self.stocks, f)
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(self.user_portfolios, f)

    # ----------------------------------------------------------------
    # 주식 가격 업데이트 (10분 간격)
    # ----------------------------------------------------------------
    @tasks.loop(minutes=10)
    async def price_updater(self):
        """10분마다 주식 가격을 업데이트합니다."""
        price_changes = {}  # 주식별 가격 변동 기록

        for stock in self.stocks:
            current_price = self.stocks[stock]

            # 50% 확률로 가격 상승 또는 하락
            if random.random() < 0.5:
                add_amount = random.uniform(0, 100)  # 0% ~ 50% 상승
            else:
                add_amount = random.uniform(-100, 0)  # -30% ~ 0% 하락
                
            new_price = max(int(current_price + add_amount), 1)  # 최소 가격 1원
            self.stocks[stock] = new_price
            price_changes[stock] = (current_price, new_price)
            
        # 상장폐지 처리 (가격이 10원 이하인 주식)
        delisted_stocks = [stock for stock, price in self.stocks.items() if price <= 1]
        for stock in delisted_stocks:
            del self.stocks[stock]
        
        if delisted_stocks:
            embed.add_field(name="📉 상장폐지 주식", value="\n".join(delisted_stocks), inline=False)
        else:
            embed.add_field(name="📉 상장폐지 주식", value="없음", inline=False)

        self.save_data()  # 데이터 저장

        # Discord 채널에 업데이트 알림
        load_dotenv()
        DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))  # 환경 변수에서 채널 ID 가져오기
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📈 주식 가격 업데이트", color=discord.Color.orange())
            for stock, (old_price, new_price) in price_changes.items():
                change = new_price - old_price
                percentage_change = (change / old_price) * 100
                change_emoji = "📈" if change > 0 else "📉"
                embed.add_field(
                    name=stock,
                    value=f"{change_emoji} {old_price}원 → {new_price}원 ({percentage_change:+.2f}%)",
                    inline=False,
                )
            await channel.send(embed=embed)
        else:
            print("⚠️ 채널을 찾을 수 없습니다.")
    
    @price_updater.before_loop
    async def before_price_updater(self):
        """봇이 준비되기를 기다립니다."""
        await self.bot.wait_until_ready()

    # ----------------------------------------------------------------
    # 매일 주식 정리 및 신규 추가 (24시간 간격)
    # ----------------------------------------------------------------
    @tasks.loop(hours=24)
    async def daily_update(self):
        """매일 주식을 정리하고 새로운 주식을 추가합니다."""

        # 평균 가격 계산
        average_price = sum(self.stocks.values()) / len(self.stocks) if self.stocks else 100

        # 새로운 주식 추가
        if len(self.stocks) < MAX_STOCKS:
            new_stock = self.generate_random_stock_name()
            new_price = int(average_price * random.uniform(0.7, 1.3))  # 평균가의 ±30% 범위
            self.stocks[new_stock] = new_price

        self.save_data()

        # 상장폐지 및 신규 상장 알림
        load_dotenv()
        DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📈 주식 시장 업데이트", color=discord.Color.green())
            embed.add_field(
                name="📈 신규 상장 주식",
                value="\n".join(f"{new_stock}: {self.stocks[new_stock]}원"),
                inline=False,
            )
            await channel.send(embed=embed)

    @daily_update.before_loop
    async def before_price_updater(self):
        """봇이 준비되기를 기다립니다."""
        await self.bot.wait_until_ready()
        
    def generate_random_stock_name(self):
        """무작위로 4글자 주식 이름을 생성합니다."""
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        while True:
            new_stock = "".join(random.choices(letters, k=4))
            if new_stock not in self.stocks:
                return new_stock

    # ----------------------------------------------------------------
    # 명령어 처리
    # ----------------------------------------------------------------
    @app_commands.command(name="주식", description="현재 주식 정보를 확인합니다.")
    async def 주식(self, interaction: discord.Interaction):
        """현재 상장된 주식 정보를 표시합니다."""
        embed = discord.Embed(title="📈 현재 주식 정보", color=discord.Color.blue())
        for stock, price in self.stocks.items():
            embed.add_field(name=stock, value=f"💵 {price}원", inline=False)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="매수", description="주식을 매수합니다.")
    async def 매수(self, interaction: discord.Interaction, stock: str, quantity: int):
        """
        사용자가 주식을 매수하는 기능.
        
        Args:
            stock (str): 매수하려는 주식의 이름.
            quantity (int): 매수하려는 주식의 수량.
        """
        balance_manager = self.bot.get_cog("BalanceManager")
        user_id = str(interaction.user.id)
        stock = stock.upper()  # 주식 이름 대문자로 변환

        # 주식 존재 여부 확인
        if stock not in self.stocks:
            await interaction.response.send_message(f"⚠️ {stock}는 존재하지 않는 주식입니다.", ephemeral=True)
            return

        # 총 매수 금액 계산
        stock_price = self.stocks[stock]
        total_cost = stock_price * quantity

        # 사용자의 잔액 확인
        user_balance = balance_manager.get_balance(user_id)
        if total_cost > user_balance:
            await interaction.response.send_message(
                f"⚠️ 잔액 부족! 현재 잔액: {user_balance}원, 필요 금액: {total_cost}원", ephemeral=True
            )
            return

        # 잔액 차감 및 포트폴리오 업데이트
        balance_manager.add_balance(user_id, -total_cost)  # 잔액 차감
        if user_id not in self.user_portfolios:
            self.user_portfolios[user_id] = {}  # 포트폴리오 생성
        self.user_portfolios[user_id][stock] = self.user_portfolios[user_id].get(stock, 0) + quantity  # 주식 추가

        self.save_data()  # 데이터 저장
        await interaction.response.send_message(
            f"✅ {stock} {quantity}주를 매수했습니다! 남은 잔액: {balance_manager.get_balance(user_id)}원"
        )

    @app_commands.command(name="매도", description="주식을 매도합니다.")
    async def 매도(self, interaction: discord.Interaction, stock: str, quantity: int):
        """
        사용자가 주식을 매도하는 기능.
        
        Args:
            stock (str): 매도하려는 주식의 이름.
            quantity (int): 매도하려는 주식의 수량.
        """
        balance_manager = self.bot.get_cog("BalanceManager")
        user_id = str(interaction.user.id)
        stock = stock.upper()  # 주식 이름 대문자로 변환

        # 주식 존재 여부 확인
        if stock not in self.stocks:
            await interaction.response.send_message(f"⚠️ {stock}는 존재하지 않는 주식입니다.", ephemeral=True)
            return

        # 사용자의 포트폴리오에서 주식 수량 확인
        if user_id not in self.user_portfolios or stock not in self.user_portfolios[user_id]:
            await interaction.response.send_message(f"⚠️ {stock}를 보유하고 있지 않습니다.", ephemeral=True)
            return

        user_stock_quantity = self.user_portfolios[user_id][stock]
        if quantity > user_stock_quantity:
            await interaction.response.send_message(
                f"⚠️ 보유 수량 부족! 현재 보유: {user_stock_quantity}주, 매도 시도: {quantity}주", ephemeral=True
            )
            return

        # 매도 처리: 잔액 증가 및 포트폴리오 업데이트
        stock_price = self.stocks[stock]
        total_earnings = stock_price * quantity  # 매도 후 얻는 금액
        balance_manager.add_balance(user_id, total_earnings)  # 잔액 추가
        self.user_portfolios[user_id][stock] -= quantity  # 보유 수량 차감

        # 해당 주식이 0주가 되면 포트폴리오에서 삭제
        if self.user_portfolios[user_id][stock] == 0:
            del self.user_portfolios[user_id][stock]

        self.save_data()  # 데이터 저장
        await interaction.response.send_message(
            f"✅ {stock} {quantity}주를 매도했습니다! 현재 잔액: {balance_manager.get_balance(user_id)}원"
        )

    @app_commands.command(name="포트폴리오", description="사용자의 포트폴리오를 확인합니다.")
    async def 포트폴리오(self, interaction: discord.Interaction):
        """사용자의 주식 보유 정보를 확인합니다."""
        balance_manager = self.bot.get_cog("BalanceManager")
        user_id = str(interaction.user.id)
        if user_id not in self.user_portfolios or not self.user_portfolios[user_id]:
            await interaction.response.send_message("⚠️ 보유 중인 주식이 없습니다.", ephemeral=True)
            return

        portfolio = self.user_portfolios[user_id]
        total_value = 0
        embed = discord.Embed(title=f"📊 {interaction.user.display_name}님의 포트폴리오", color=discord.Color.purple())
        for stock, quantity in portfolio.items():
            if stock in self.stocks:
                stock_price = self.stocks[stock]
                stock_value = stock_price * quantity
                total_value += stock_value
                embed.add_field(
                    name=f"{stock} ({quantity}주)", value=f"💵 주당 가격: {stock_price}원\n💰 총 가치: {stock_value}원", inline=False
                )
            else:
                embed.add_field(name=f"{stock} ({quantity}주)", value="⚠️ 상장 폐지됨", inline=False)

        user_balance = balance_manager.get_balance(user_id)
        embed.add_field(name="💼 잔액", value=f"{user_balance}원", inline=False)
        embed.add_field(name="💎 총 자산", value=f"{total_value + user_balance}원", inline=False)

        await interaction.response.send_message(embed=embed)

# --------------------------------------------------------------------
# Cog 로드
# --------------------------------------------------------------------
async def setup(bot: commands.Bot):
    """StockMarket Cog를 봇에 추가합니다."""
    await bot.add_cog(StockMarket(bot))
