import discord
from discord.ext import commands
from discord import app_commands

class TitleManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_titles = {}

    def get_user_title(self, user_id: str) -> str:
        """사용자의 칭호를 반환합니다."""
        return self.user_titles.get(user_id, "칭호 없음")

    def set_user_title(self, user_id: str, title: str):
        """사용자의 칭호를 설정합니다."""
        self.user_titles[user_id] = title

    @app_commands.command(name="칭호설정", description="자신의 닉네임 앞에 칭호를 설정합니다.")
    async def set_title(self, interaction: discord.Interaction, 칭호: str):
        """사용자의 닉네임에 칭호를 추가합니다."""
        # 권한 확인
        if not interaction.guild.me.guild_permissions.manage_nicknames:
            await interaction.response.send_message("🔴 닉네임 변경 권한이 없습니다.", ephemeral=True)
            return

        member = interaction.user
        user_id = str(member.id)

        # 칭호 설정
        self.set_user_title(user_id, 칭호)

        # 닉네임 변경
        original_name = member.display_name
        new_nickname = f"[{칭호}] {original_name}"

        try:
            await member.edit(nick=new_nickname)
            await interaction.response.send_message(f"✅ 닉네임이 변경되었습니다: **{new_nickname}**")
        except discord.Forbidden:
            await interaction.response.send_message("🔴 닉네임을 변경할 수 없습니다. 봇의 권한을 확인해주세요.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"🔴 닉네임 변경 중 오류가 발생했습니다: {e}", ephemeral=True)

    @app_commands.command(name="칭호해제", description="닉네임에 추가된 칭호를 제거합니다.")
    async def remove_title(self, interaction: discord.Interaction):
        """사용자의 닉네임에서 칭호를 제거합니다."""
        # 권한 확인
        if not interaction.guild.me.guild_permissions.manage_nicknames:
            await interaction.response.send_message("🔴 닉네임 변경 권한이 없습니다.", ephemeral=True)
            return

        member = interaction.user
        user_id = str(member.id)

        # 칭호 제거
        self.user_titles.pop(user_id, None)

        # 닉네임 원래대로 복구
        original_name = member.name  # Discord에 저장된 유저의 원래 이름
        try:
            await member.edit(nick=original_name)
            await interaction.response.send_message(f"✅ 닉네임이 원래대로 복구되었습니다: **{original_name}**")
        except discord.Forbidden:
            await interaction.response.send_message("🔴 닉네임을 변경할 수 없습니다. 봇의 권한을 확인해주세요.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"🔴 닉네임 변경 중 오류가 발생했습니다: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TitleManager(bot))
