"""Strict builders and parsers for linked-player rescue commands.

[유지보수 안내 — 스폰 동작 통합]
스폰의 기준은 이제 "월드 스폰(setworldspawn)" 하나입니다.
- 죽었을 때(침대·리스폰 정박기가 없을 때) 되살아나는 곳 = 월드 스폰
- /도구의 "선택 계정 스폰 귀환" = 번들 플러그인(raspiops rescue)이 월드 스폰으로 이동
- 관리자는 관리 패널의 "빠른 명령 → 스폰 지정"으로 월드 스폰을 옮깁니다.
과거에는 .env의 MC_SPAWN_X/Y/Z/DIMENSION으로 귀환 좌표를 따로 지정할 수
있었지만, 죽었을 때 위치와 버튼 귀환 위치가 서로 달라지는 원인이라 제거했습니다.
라즈베리파이의 운영 .env에 MC_SPAWN_* 값이 남아 있다면 지워도 됩니다(무시됨).
침대에서 잔 플레이어는 마인크래프트 기본 동작대로 침대에서 리스폰합니다.
"""

import re

from bot.player_names import validateServerPlayerName


POSITION_PATTERN = re.compile(
    r"\[\s*(-?\d+(?:\.\d+)?)[dDfF]?,\s*"
    r"(-?\d+(?:\.\d+)?)[dDfF]?,\s*"
    r"(-?\d+(?:\.\d+)?)[dDfF]?\s*\]"
)
DIMENSION_PATTERN = re.compile(r"minecraft:(overworld|the_nether|the_end)")

# 번들 플러그인(raspiops rescue)이 돌려주는 응답 문구와 한글 안내의 대응표.
# 플러그인은 실패도 "정상 텍스트"로 답하기 때문에(RCON 특성) 아래 문구를
# 검사하지 않으면 미접속 플레이어도 성공으로 보입니다(이슈 #45 댓글 버그).
# 플러그인 응답 문구를 바꾸면 이 표도 함께 갱신해야 합니다.
_FAILURE_MESSAGES = {
    "player is not online": "플레이어가 게임에 접속 중이 아닙니다. 마인크래프트에 접속한 뒤 다시 시도하세요.",
    "no entity was found": "플레이어가 게임에 접속 중이 아닙니다. 마인크래프트에 접속한 뒤 다시 시도하세요.",
    "invalid exact player name": "플레이어 이름이 올바르지 않습니다. 서버장에게 계정 등록 정보를 확인해 달라고 하세요.",
    "usage:": "구조 명령 형식이 잘못되었습니다. 서버장에게 알려주세요.",
    "no world is loaded": "서버에 불러온 월드가 없습니다. 서버장에게 알려주세요.",
    "paper rejected": "서버가 순간이동을 거부했습니다. 잠시 후 다시 시도하세요.",
    "you do not have permission": "서버가 구조 명령 권한을 거부했습니다. 서버장에게 알려주세요.",
    "unknown command": "서버에 구조 플러그인이 설치되지 않았습니다. 서버장에게 알려주세요.",
    "unknown or incomplete": "서버에 구조 플러그인이 설치되지 않았습니다. 서버장에게 알려주세요.",
    "command failed safely": "서버에서 구조 명령이 실패했습니다. 서버장에게 알려주세요.",
}


def buildAutomaticSpawnCommand(playerName: str) -> str:
    """Ask the bundled Paper plugin to use the live world's configured spawn."""
    safeName = validateServerPlayerName(playerName)
    return f"raspiops rescue {safeName}"


def ensureRescueSucceeded(output: str) -> None:
    """Raise a Korean, friend-readable error unless the teleport really happened.

    성공 판정은 플러그인의 성공 응답("Teleported ...")을 기준으로 합니다.
    알 수 없는 응답도 실패로 취급해 허위 성공 메시지를 막습니다.
    """
    lowered = (output or "").casefold()
    if "teleported" in lowered:
        return
    for marker, koreanMessage in _FAILURE_MESSAGES.items():
        if marker in lowered:
            raise ValueError(koreanMessage)
    snippet = (output or "").strip()[:200] or "(응답 없음)"
    raise ValueError(f"스폰 귀환을 확인하지 못했습니다. 서버 응답: {snippet}")


def parsePosition(positionOutput: str, dimensionOutput: str) -> tuple[str, float, float, float]:
    """Parse Paper's entity NBT replies for the linked player's own location."""
    positionMatch = POSITION_PATTERN.search(positionOutput or "")
    dimensionMatch = DIMENSION_PATTERN.search(dimensionOutput or "")
    if not positionMatch or not dimensionMatch:
        raise ValueError("플레이어 위치를 확인할 수 없습니다. 게임에 접속 중이 아닐 수 있습니다.")
    dimension = {
        "the_nether": "nether",
        "the_end": "the_end",
        "overworld": "overworld",
    }[dimensionMatch.group(1)]
    x, y, z = (float(value) for value in positionMatch.groups())
    return dimension, x, y, z
