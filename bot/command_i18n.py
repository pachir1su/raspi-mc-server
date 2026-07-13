"""Discord application-command localization.

English remains the canonical API name so existing integrations keep working.
Discord automatically presents the Korean localization to users whose Discord
client language is Korean.
"""

import discord
from discord import app_commands


# Command and option names must stay short and unique within their parent.
KOREAN_NAMES = {
    "portal": "접속안내",
    "online": "접속자",
    "status": "상태",
    "say": "공지",
    "mc": "마크명령",
    "whitelist": "허용목록",
    "add": "추가",
    "remove": "제거",
    "start": "시작",
    "stop": "정지",
    "restart": "재시작",
    "backup": "백업",
    "create": "생성",
    "list": "목록",
    "timeline": "타임라인",
    "download": "다운로드",
    "delete": "삭제",
    "restore-preview": "복구미리보기",
    "restore": "복구",
    "verify": "검증",
    "prune": "정리",
    "settings": "설정",
    "configure": "구성",
    "world": "월드",
    "upload": "업로드",
    "activate": "적용",
    "storage": "저장공간",
    "health": "건강",
    "audit": "감사기록",
    "panel": "관리패널",
    "players": "플레이어",
    "metrics": "성능지표",
    "tuning-report": "튜닝보고서",
    "incident": "긴급조치",
    "day": "낮",
    "clear-weather": "맑은날씨",
    "peaceful": "평화로움",
    "clear-drops": "드롭정리",
    "logs": "로그",
    "link": "연동",
    "request": "요청",
    "approve": "승인",
    "revoke": "해제",
    "rescue": "구조",
    "spawn": "스폰",
    "whereami": "내위치",
    "place": "좌표",
    "show": "보기",
    "diary": "일지",
    "recent": "최근",
    "server-score": "서버점수",
    "update": "업데이트",
    "check": "확인",
    "apply": "설치",
    "message": "메시지",
    "command": "명령",
    "player": "플레이어",
    "name": "이름",
    "label": "라벨",
    "limit": "개수",
    "user": "사용자",
    "minecraft_name": "마크닉",
    "edition": "에디션",
    "dimension": "차원",
    "description": "설명",
    "photo": "사진",
    "entry_id": "일지번호",
    "file": "파일",
    "confirm": "확인문구",
    "interval_minutes": "간격분",
    "retention_count": "보관개수",
    "enabled": "활성화",
}


# Descriptions are keyed by their canonical English text from decorators.
KOREAN_DESCRIPTIONS = {
    "Show friend-safe server access info and live status.": "친구용 서버 접속 정보와 현재 상태를 표시합니다.",
    "Show who is online without exposing admin controls.": "관리 기능을 노출하지 않고 접속자를 표시합니다.",
    "Show whether the server is up and who is online.": "서버 실행 상태와 접속자를 표시합니다.",
    "Broadcast a message to everyone in-game.": "게임 안의 모든 플레이어에게 공지합니다.",
    "Run ANY server command via RCON (owner cheat channel).": "RCON으로 모든 서버 명령을 실행합니다(관리자 전용).",
    "Manage the whitelist.": "서버 접속 허용 목록을 관리합니다.",
    "Start the Minecraft service.": "마인크래프트 서비스를 시작합니다.",
    "Stop the Minecraft service (saves first).": "저장 후 마인크래프트 서비스를 정지합니다.",
    "Restart the Minecraft service.": "마인크래프트 서비스를 재시작합니다.",
    "Manage HDD world backups.": "HDD 월드 백업을 관리합니다.",
    "Upload and activate HDD maps.": "HDD에 맵을 업로드하고 적용합니다.",
    "Show HDD mount and free-space status.": "HDD 마운트와 여유 공간을 표시합니다.",
    "Check RCON, HDD, scheduler, and backup freshness.": "RCON, HDD, 스케줄러와 최근 백업을 점검합니다.",
    "Show recent privileged-operation audit records.": "최근 관리자 작업 감사 기록을 표시합니다.",
    "Open the button-first Minecraft admin dashboard.": "버튼 방식 마인크래프트 관리 패널을 엽니다.",
    "Select an online player and inspect their state.": "접속 중인 플레이어를 선택해 상태를 확인합니다.",
    "Show Raspberry Pi resources and Paper TPS.": "라즈베리파이 자원과 Paper TPS를 표시합니다.",
    "Explain current performance risks and tuning advice.": "현재 성능 위험과 튜닝 권장 사항을 설명합니다.",
    "Open button controls for bot and Minecraft logs.": "봇과 마인크래프트 로그 버튼을 엽니다.",
    "Link Discord to one Minecraft account.": "Discord 계정을 마인크래프트 계정 하나와 연동합니다.",
    "Self-service help for your linked player.": "연동된 본인 플레이어를 위한 구조 기능입니다.",
    "Shared coordinate book with photos and map links.": "사진과 지도 링크를 지원하는 공유 좌표북입니다.",
    "Shared server-life journal.": "친구들과 공유하는 서버 일지입니다.",
    "Request a link to your Minecraft name.": "본인의 마인크래프트 닉네임 연동을 요청합니다.",
    "Show your current link status.": "현재 계정 연동 상태를 표시합니다.",
    "Approve one pending player link (admin).": "대기 중인 계정 연동을 승인합니다(관리자).",
    "Revoke a player link (admin).": "계정 연동을 해제합니다(관리자).",
    "List pending and approved links (admin).": "대기 및 승인된 연동을 표시합니다(관리자).",
    "Teleport only your linked player to spawn.": "연동된 본인 플레이어만 스폰으로 이동합니다.",
    "Show your linked player's current location.": "연동된 본인 플레이어의 현재 위치를 표시합니다.",
    "Save or replace a shared coordinate.": "공유 좌표를 저장하거나 교체합니다.",
    "List shared coordinate names.": "공유 좌표 이름을 표시합니다.",
    "Open one coordinate card.": "좌표 카드 하나를 엽니다.",
    "Show the calculated server health score.": "계산된 서버 건강 점수를 표시합니다.",
    "Manage safe Raspberry Pi application updates.": "안전한 라즈베리파이 프로그램 업데이트를 관리합니다.",
    "Check the newest GitHub Release without installing it.": "설치하지 않고 최신 GitHub Release를 확인합니다.",
    "Upload a trusted release ZIP and open a confirmation panel.": "신뢰하는 Release ZIP을 올리고 설치 확인 창을 엽니다.",
    "Show the most recent updater result.": "최근 업데이트 결과를 표시합니다.",
    "Text to say in chat": "게임 채팅에 보낼 내용",
    "Your exact in-game name or Xbox gamertag": "정확한 게임 닉네임 또는 Xbox 게이머태그",
    "The Minecraft edition you use to join": "접속에 사용하는 마인크래프트 에디션",
}


class CommandTranslator(app_commands.Translator):
    """Return Korean command metadata for Korean Discord clients."""

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ) -> str | None:
        if locale is not discord.Locale.korean:
            return None
        message = string.message
        if context.location in {
            app_commands.TranslationContextLocation.command_name,
            app_commands.TranslationContextLocation.group_name,
            app_commands.TranslationContextLocation.parameter_name,
        }:
            return KOREAN_NAMES.get(message)
        return KOREAN_DESCRIPTIONS.get(message)
