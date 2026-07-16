"""Tiny runtime language helpers for Discord-facing text."""

from bot.config import cfg

_MESSAGES = {
    "ko": {
        "not_authorized": "⛔ 관리자 전용 기능입니다. 친구용 기능은 `/서버`, `/내도구`, `/도움말`을 사용하세요.",
        "portal_title": "🎮 친구용 서버 포털",
        "portal_description": "접속 정보와 현재 상태를 한 번에 확인하세요.",
        "portal_address": "서버 주소",
        "portal_address_missing": "관리자가 MC_PUBLIC_ADDRESS를 설정하지 않았습니다.",
        "portal_version": "버전",
        "portal_rules": "규칙",
        "portal_rules_default": "서로의 건축물과 아이템을 존중하고, 문제는 서버장에게 알려주세요.",
        "portal_online": "접속자",
        "portal_offline": "서버 상태를 확인할 수 없습니다.",
        "online_none": "현재 접속 중인 플레이어가 없습니다.",
        "online_title": "👥 현재 접속자",
        "alerts_title": "🚨 서버 자동 알림",
        "alerts_ok": "현재 새 경고가 없습니다.",
        "tuning_title": "🧰 성능 튜닝 리포트",
        "tuning_summary": "현재 지표를 기준으로 라즈베리파이 친화 설정을 점검했습니다.",
        "incident_day": "☀️ 시간을 낮으로 바꿨습니다.",
        "incident_clear": "🌤️ 날씨를 맑게 바꿨습니다.",
        "incident_peaceful": "🛡️ 난이도를 peaceful로 바꿨습니다. 필요하면 다시 조정하세요.",
        "incident_kill_items": "🧹 바닥 아이템 정리를 실행했습니다.",
        "incident_confirm_clear_drops": "❌ 모든 바닥 아이템을 지우려면 confirm에 `CLEAR`를 입력하세요.",
        "incident_clear_drops_prompt": "바닥 아이템을 모두 삭제할까요? 친구가 방금 떨어뜨린 아이템도 사라질 수 있습니다.",
        "confirm": "확인",
        "cancel": "취소",
        "cancelled": "취소했습니다.",
        "backup_timeline_title": "🕒 백업 타임라인",
        "restore_preview_title": "🔎 복구 미리보기",
        "restore_preview_ok": "복구 대상 백업을 찾았고, 실제 복구 전 검증을 통과했습니다.",
        "presence": "라즈베리파이 마크 서버",
    },
    "en": {
        "not_authorized": "⛔ This is an admin-only feature. Friends can use `/server`, `/my-tools`, and `/help`.",
        "portal_title": "🎮 Friend server portal",
        "portal_description": "Quick access info and live status for players.",
        "portal_address": "Server address",
        "portal_address_missing": "The admin has not set MC_PUBLIC_ADDRESS yet.",
        "portal_version": "Version",
        "portal_rules": "Rules",
        "portal_rules_default": "Respect builds and items, and tell the operator when something breaks.",
        "portal_online": "Online players",
        "portal_offline": "Server status is unavailable.",
        "online_none": "No players are online right now.",
        "online_title": "👥 Online players",
        "alerts_title": "🚨 Server auto alert",
        "alerts_ok": "No new warnings right now.",
        "tuning_title": "🧰 Performance tuning report",
        "tuning_summary": "Checked the current metrics against Raspberry Pi-friendly settings.",
        "incident_day": "☀️ Set the time to day.",
        "incident_clear": "🌤️ Cleared the weather.",
        "incident_peaceful": "🛡️ Set difficulty to peaceful. Change it back when ready.",
        "incident_kill_items": "🧹 Removed dropped item entities.",
        "incident_confirm_clear_drops": "❌ Type `CLEAR` in confirm to delete every dropped item entity.",
        "incident_clear_drops_prompt": "Delete all dropped items? Items your friends just dropped can disappear too.",
        "confirm": "Confirm",
        "cancel": "Cancel",
        "cancelled": "Cancelled.",
        "backup_timeline_title": "🕒 Backup timeline",
        "restore_preview_title": "🔎 Restore preview",
        "restore_preview_ok": "Found the target backup and it passed pre-restore verification.",
        "presence": "Raspberry Pi Minecraft",
    },
}


def t(key: str) -> str:
    """Return a configured-language message with English fallback."""
    language = cfg.language if cfg.language in _MESSAGES else "en"
    return _MESSAGES[language].get(key, _MESSAGES["en"].get(key, key))
