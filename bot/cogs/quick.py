"""Flat, top-level Minecraft admin commands (issue #79).

기존에는 서버 조작이 `/관리자 → 더보기 → 고급 도구 → 인게임 명령어`처럼 여러
단계를 파고들어야 했습니다. 이 Cog는 가장 자주 쓰는 동작을 **최상위 슬래시
명령 한 번**으로 노출합니다. 실제 명령 문자열은 모두 `bot.quick_commands`의
검증된 빌더를 재사용하며, 관리 패널과 동작이 완전히 동일합니다.

명령 이름은 영어 정식명이지만, 한국어 디스코드 클라이언트에는 `command_i18n`의
매핑을 통해 한글로 표시됩니다(`/명령어`, `/무적`, `/지급` 등).
"""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot import BRAND_BLUE, OK_GREEN, ERR_RED, log, userTag
from bot.config import cfg
from bot.error_text import describeError
from bot.player_info import parseOnlinePlayers
from bot.quick_commands import (
    SCOREBOARD_STATS,
    buildGiveCommand,
    buildInvincibilityClearCommands,
    buildInvincibilityCommands,
    buildScoreboardGetCommand,
    buildScoreboardSetupCommands,
    ensureServerAccepted,
    parseInvincibleSeconds,
    parseScoreboardValue,
)
from bot.rcon import Rcon, RconError
from bot.wiki import WIKI_PAGES, wikiPageLabel, wikiPageUrl

_log = log.get("cog.quick")

# 관리자 게이트를 적용하지 않는 공개 명령(친구도 사용 가능).
PUBLIC_QUICK_COMMANDS = {"wiki"}

# 시간·날씨 프리셋: 표시 라벨 → 실제 RCON 명령.
_TIME_PRESETS = {
    "day": ("낮", "time set day"),
    "noon": ("정오", "time set noon"),
    "night": ("밤", "time set night"),
    "midnight": ("자정", "time set midnight"),
}
_WEATHER_PRESETS = {
    "clear": ("맑음", "weather clear"),
    "rain": ("비", "weather rain"),
    "thunder": ("천둥", "weather thunder"),
}


async def _rcon(command: str) -> str:
    """Run one pre-built command through a short-lived local RCON connection."""
    async with Rcon(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password) as client:
        return await client.command(command)


def _is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in cfg.admin_ids


class Quick(commands.Cog):
    """One-step admin commands that mirror the button panel's actions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        name = interaction.command.name if interaction.command else ""
        if name in PUBLIC_QUICK_COMMANDS:
            return True
        if _is_admin(interaction):
            return True
        await interaction.response.send_message(
            "⛔ 관리자만 사용할 수 있습니다.", ephemeral=True
        )
        _log.warning("denied quick command from %s", userTag(interaction.user))
        return False

    async def cog_load(self) -> None:
        """Create the stats scoreboards once so `/통계`·`/내통계` have data (#68)."""
        try:
            for command in buildScoreboardSetupCommands():
                # 이미 존재하면 서버가 오류를 돌려주지만 무해하므로 삼킵니다.
                await _rcon(command)
        except RconError as error:
            # 서버가 꺼져 있을 수 있습니다 — 시작을 막지 않고 로그만 남깁니다.
            _log.info("scoreboard setup deferred (server offline?): %s", error)

    async def onlinePlayerAutocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggest currently online players so no name has to be typed."""
        try:
            players = parseOnlinePlayers(await _rcon("list"))
        except RconError:
            return []
        lowered = current.lower()
        return [
            app_commands.Choice(name=name[:100], value=name)
            for name in players
            if lowered in name.lower()
        ][:25]

    # --- 조회 ----------------------------------------------------------
    @app_commands.command(name="who", description="Show who is online right now.")
    async def who(self, interaction: discord.Interaction) -> None:
        try:
            players = parseOnlinePlayers(await _rcon("list"))
        except RconError as error:
            await interaction.response.send_message(
                f"❌ {describeError(error)}", ephemeral=True
            )
            return
        body = "\n".join(f"• {name}" for name in players) or "지금 접속한 사람이 없습니다."
        await interaction.response.send_message(
            embed=discord.Embed(title="👥 현재 접속자", description=body, color=OK_GREEN),
            ephemeral=True,
        )

    # --- 인게임 명령 직접 실행 -----------------------------------------
    @app_commands.command(name="cmd", description="Run one server command via RCON.")
    @app_commands.describe(command="예: gamemode creative Steve, give Steve diamond 8")
    async def cmd(self, interaction: discord.Interaction, command: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            out = (await _rcon(command)).strip() or "(출력 없음)"
        except RconError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await interaction.followup.send(
            embed=discord.Embed(
                title="🎛️ 명령 실행 완료",
                description=f"`/{command}`\n```\n{out[:1800]}\n```",
                color=BRAND_BLUE,
            ),
            ephemeral=True,
        )
        _log.info("cmd by %s: %s", userTag(interaction.user), command)

    @app_commands.command(name="notice", description="Broadcast a message to everyone in-game.")
    @app_commands.describe(message="게임 채팅에 보낼 공지 내용")
    async def notice(self, interaction: discord.Interaction, message: str) -> None:
        try:
            await _rcon(f"say {message}")
        except RconError as error:
            await interaction.response.send_message(
                f"❌ {describeError(error)}", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"📢 공지를 전송했습니다: {message}", ephemeral=True
        )
        _log.info("notice by %s: %s", userTag(interaction.user), message)

    # --- 월드 프리셋 ---------------------------------------------------
    @app_commands.command(name="time", description="Set the world time to a preset.")
    @app_commands.describe(preset="설정할 시간대")
    @app_commands.choices(preset=[
        app_commands.Choice(name=label, value=key)
        for key, (label, _) in _TIME_PRESETS.items()
    ])
    async def time(
        self, interaction: discord.Interaction, preset: app_commands.Choice[str]
    ) -> None:
        label, command = _TIME_PRESETS[preset.value]
        await self._runSimple(interaction, command, f"🕰️ 시간을 **{label}**(으)로 바꿨습니다.")

    @app_commands.command(name="weather", description="Set the world weather to a preset.")
    @app_commands.describe(preset="설정할 날씨")
    @app_commands.choices(preset=[
        app_commands.Choice(name=label, value=key)
        for key, (label, _) in _WEATHER_PRESETS.items()
    ])
    async def weather(
        self, interaction: discord.Interaction, preset: app_commands.Choice[str]
    ) -> None:
        label, command = _WEATHER_PRESETS[preset.value]
        await self._runSimple(interaction, command, f"🌤️ 날씨를 **{label}**(으)로 바꿨습니다.")

    async def _runSimple(
        self, interaction: discord.Interaction, command: str, successText: str
    ) -> None:
        try:
            ensureServerAccepted(await _rcon(command))
        except (RconError, ValueError) as error:
            await interaction.response.send_message(
                f"❌ {describeError(error) if isinstance(error, RconError) else error}",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(successText, ephemeral=True)
        _log.info("%s by %s", command, userTag(interaction.user))

    # --- 플레이어 대상 ------------------------------------------------
    @app_commands.command(name="invincible", description="Grant temporary invincibility to a player.")
    @app_commands.describe(player="대상 접속자", seconds="지속 시간(초, 기본 5)")
    @app_commands.autocomplete(player=onlinePlayerAutocomplete)
    async def invincible(
        self, interaction: discord.Interaction, player: str, seconds: str = "5"
    ) -> None:
        try:
            duration = parseInvincibleSeconds(seconds)
            commands_ = buildInvincibilityCommands(player, duration)
        except ValueError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            for command in commands_:
                ensureServerAccepted(await _rcon(command))
        except (RconError, ValueError) as error:
            text = describeError(error) if isinstance(error, RconError) else error
            await interaction.followup.send(f"❌ {text}", ephemeral=True)
            return
        await interaction.followup.send(
            f"🛡️ `{player}` 님을 **{duration}초** 동안 무적으로 만들었습니다. "
            "(재생·저항·화염 저항·포화, 파티클 숨김)",
            ephemeral=True,
        )
        _log.info("invincible %s (%ss) by %s", player, duration, userTag(interaction.user))

    @app_commands.command(name="mortal", description="Remove invincibility from a player.")
    @app_commands.describe(player="대상 접속자")
    @app_commands.autocomplete(player=onlinePlayerAutocomplete)
    async def mortal(self, interaction: discord.Interaction, player: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            for command in buildInvincibilityClearCommands(player):
                await _rcon(command)
        except RconError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await interaction.followup.send(
            f"⚔️ `{player}` 님의 무적을 해제했습니다.", ephemeral=True
        )
        _log.info("mortal %s by %s", player, userTag(interaction.user))

    @app_commands.command(name="give", description="Give an item to a player (Korean aliases ok).")
    @app_commands.describe(player="대상 접속자", item="아이템(한글 별칭 가능)", count="수량(기본 1)")
    @app_commands.autocomplete(player=onlinePlayerAutocomplete)
    async def give(
        self, interaction: discord.Interaction, player: str, item: str, count: str = "1"
    ) -> None:
        try:
            command = buildGiveCommand(player, item, count)
        except ValueError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ensureServerAccepted(await _rcon(command))
        except (RconError, ValueError) as error:
            text = describeError(error) if isinstance(error, RconError) else error
            await interaction.followup.send(f"❌ {text}", ephemeral=True)
            return
        await interaction.followup.send(
            f"🎁 `{player}` 님에게 `{item}` × {count}을(를) 지급했습니다.", ephemeral=True
        )
        _log.info("give %s %s x%s by %s", player, item, count, userTag(interaction.user))

    @app_commands.command(name="stats", description="Show a player's tracked stats (deaths/kills).")
    @app_commands.describe(player="조회할 접속자")
    @app_commands.autocomplete(player=onlinePlayerAutocomplete)
    async def stats(self, interaction: discord.Interaction, player: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._sendStats(interaction, player, title=f"📊 `{player}` 통계")

    async def _sendStats(
        self, interaction: discord.Interaction, playerName: str, title: str
    ) -> None:
        """Query every stats objective and render one embed (#68)."""
        try:
            lines = []
            for _, objective, _, label in SCOREBOARD_STATS:
                value = parseScoreboardValue(
                    await _rcon(buildScoreboardGetCommand(playerName, objective))
                )
                lines.append(f"• {label}: **{value}**")
        except (RconError, ValueError) as error:
            text = describeError(error) if isinstance(error, RconError) else error
            await interaction.followup.send(f"❌ {text}", ephemeral=True)
            return
        embed = discord.Embed(title=title, description="\n".join(lines), color=BRAND_BLUE)
        embed.set_footer(text="통계는 봇이 처음 실행된 시점부터 집계됩니다.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- 위키(#71) ----------------------------------------------------
    @app_commands.command(name="wiki", description="Open an in-game help wiki page.")
    @app_commands.describe(page="열어볼 문서")
    @app_commands.choices(page=[
        app_commands.Choice(name=label, value=key) for key, label, _ in WIKI_PAGES
    ])
    async def wiki(
        self, interaction: discord.Interaction, page: app_commands.Choice[str]
    ) -> None:
        url = wikiPageUrl(page.value, language="ko")
        embed = discord.Embed(
            title=f"📖 위키 — {wikiPageLabel(page.value)}",
            description=f"[문서 열기]({url})",
            color=BRAND_BLUE,
        )
        embed.set_footer(text="GitHub의 최신 문서로 이동합니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Quick(bot))
