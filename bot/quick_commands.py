"""관리자 '빠른 명령'용 안전한 명령 빌더와 결과 검증기.

[유지보수 안내]
관리 패널의 접속자 관리·빠른 명령 버튼은 이 모듈의 빌더만 사용합니다.
버튼 → RCON 명령 대응이 전부 이 파일에 모여 있으므로, 마인크래프트가
업데이트되어 명령 문법이 바뀌면 이 파일과 `bot/item_aliases.py`만 고치면
됩니다. 새 버튼을 만들 때도 명령 문자열을 뷰(control_panel.py)에 직접
쓰지 말고 여기에 빌더를 추가하세요(플레이어 이름 검증을 강제하기 위함).
"""

import difflib
import re

from bot.item_aliases import ITEM_ALIASES, KNOWN_ITEM_IDS
from bot.player_names import buildPlayerSelector, validateServerPlayerName


# minecraft: 접두사를 뺀 아이템/효과/인챈트 ID의 안전한 형태.
_RESOURCE_ID_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")

# 월드 경계(참고: 마인크래프트 X/Z 한계 ±30,000,000, Y는 넉넉히 ±2048).
_MAX_HORIZONTAL = 30_000_000
_MAX_VERTICAL = 2_048

# 드롭다운에 노출하는 자주 쓰는 포션 효과: (ID, 한글 라벨, 지속 초, 증폭 단계).
# 지속 시간을 바꾸려면 여기 숫자만 바꾸면 됩니다. 증폭 0 = I 단계.
COMMON_EFFECTS = (
    ("speed", "신속", 300, 0),
    ("strength", "힘", 300, 0),
    ("regeneration", "재생", 300, 0),
    ("resistance", "저항", 300, 0),
    ("fire_resistance", "화염 저항", 300, 0),
    ("night_vision", "야간 투시", 600, 0),
    ("water_breathing", "수중 호흡", 300, 0),
    ("jump_boost", "점프 강화", 300, 0),
    ("haste", "성급함", 300, 0),
    ("slow_falling", "느린 낙하", 300, 0),
    ("invisibility", "투명화", 300, 0),
)

# 드롭다운에 노출하는 자주 쓰는 인챈트: (ID, 한글 라벨, 부여 레벨).
# 들고 있는 아이템에 적용되므로 호환되지 않으면 서버가 거부합니다.
COMMON_ENCHANTS = (
    ("sharpness", "날카로움 V", 5),
    ("efficiency", "효율 V", 5),
    ("unbreaking", "내구성 III", 3),
    ("mending", "수선", 1),
    ("fortune", "행운 III", 3),
    ("silk_touch", "섬세한 손길", 1),
    ("looting", "약탈 III", 3),
    ("protection", "보호 IV", 4),
    ("power", "힘(활) V", 5),
    ("infinity", "무한", 1),
)

GAMEMODES = {
    "survival": "서바이벌",
    "creative": "크리에이티브",
    "spectator": "관전",
}

DIFFICULTIES = {
    "peaceful": "평화로움",
    "easy": "쉬움",
    "normal": "보통",
    "hard": "어려움",
}

# 빠른 명령 패널의 게임룰 토글: 키 → (게임룰 이름, 한글 라벨).
# 아래 세 개(즉시 리스폰·자연 재생·플레이 일수)는 서버 시작 시 기본 ON으로
# 맞춥니다 — DEFAULT_ON_GAMERULES 참고.
GAMERULES = {
    "keepInventory": ("keepInventory", "죽어도 아이템 유지"),
    "mobGriefing": ("mobGriefing", "몹의 블록 파괴(그리핑)"),
    "doImmediateRespawn": ("doImmediateRespawn", "즉시 리스폰"),
    "naturalRegeneration": ("naturalRegeneration", "자연 체력 재생"),
    "showDaysPlayed": ("showDaysPlayed", "플레이 일수 표시"),
    "doDaylightCycle": ("doDaylightCycle", "낮밤 시간 흐름"),
    "doWeatherCycle": ("doWeatherCycle", "날씨 변화"),
}

# 봇이 서버에 연결될 때 한 번 기본 ON으로 적용하는 게임룰(운영자 요청).
# showDaysPlayed는 구버전 마인크래프트에 없을 수 있으며, 그 경우 적용
# 실패를 로그로만 남기고 넘어갑니다.
DEFAULT_ON_GAMERULES = ("doImmediateRespawn", "naturalRegeneration", "showDaysPlayed")

# 서버가 명령을 거부했을 때 응답에 나타나는 문구 → 한글 안내.
_SERVER_FAILURE_MESSAGES = {
    "no player was found": "플레이어가 게임에 접속 중이 아닙니다.",
    "no entity was found": "플레이어가 게임에 접속 중이 아닙니다.",
    "unknown item": "존재하지 않는 아이템 ID입니다. 이름을 다시 확인하세요.",
    "unknown effect": "존재하지 않는 포션 효과 ID입니다.",
    "unknown enchantment": "존재하지 않는 인챈트 ID입니다.",
    "cannot support that enchantment": "들고 있는 아이템에 걸 수 없는 인챈트입니다.",
    "is not a valid enchantment": "들고 있는 아이템에 걸 수 없는 인챈트입니다.",
    "higher than the maximum": "인챈트 최대 레벨을 넘었습니다.",
    "incorrect argument": "명령 형식이 잘못되었습니다. 입력값을 확인하세요.",
    "expected whitespace": "명령 형식이 잘못되었습니다. 입력값을 확인하세요.",
    "unknown or incomplete command": "서버가 지원하지 않는 명령입니다(버전 확인 필요).",
    "unknown command": "서버가 지원하지 않는 명령입니다(버전 확인 필요).",
    "unknown game rule": "이 서버 버전에는 없는 게임룰입니다.",
}


# 게임룰 이름이 그 서버 버전에 없으면 Brigadier가 'Incorrect argument'를
# 돌려줍니다(#59). 일반 매핑은 '명령 형식 오류'라고만 말해 원인을 숨기므로
# 게임룰 명령에는 이 함수를 대신 사용하세요.
GAMERULE_UNSUPPORTED_MESSAGE = (
    "이 서버 버전에는 없는 게임룰입니다. 서버를 업데이트하면 쓸 수 있어요."
)


def ensureGameruleAccepted(output: str) -> str:
    """Validate a gamerule command reply with version-aware Korean errors."""
    lowered = (output or "").casefold()
    if "incorrect argument" in lowered or "unknown game rule" in lowered:
        raise ValueError(GAMERULE_UNSUPPORTED_MESSAGE)
    return ensureServerAccepted(output)


def ensureServerAccepted(output: str) -> str:
    """Raise a Korean error when the server's reply is a known rejection.

    RCON은 실패도 일반 텍스트로 돌려주므로, 버튼이 "성공"이라고 말하기 전에
    반드시 이 함수를 통과시켜야 합니다(스폰 귀환 버그와 같은 원리).
    """
    lowered = (output or "").casefold()
    for marker, koreanMessage in _SERVER_FAILURE_MESSAGES.items():
        if marker in lowered:
            raise ValueError(koreanMessage)
    return output or ""


def _validateResourceId(rawId: str, kindLabel: str) -> str:
    """Normalize one item/effect/enchant ID and reject unsafe characters."""
    cleaned = (rawId or "").strip().lower().removeprefix("minecraft:")
    if not _RESOURCE_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            f"{kindLabel} ID는 영문 소문자·숫자·밑줄만 사용할 수 있습니다 (예: diamond, speed)"
        )
    return cleaned


def resolveItemId(rawName: str) -> str:
    """Turn free-form input (Korean alias or English ID) into one item ID.

    1) 한글 별칭 표에 있으면 그 ID를 사용
    2) 영어 ID 형태면 그대로 통과(최종 검증은 서버의 give가 수행)
    3) 그 외에는 비슷한 후보를 제시하며 거부
    """
    cleaned = (rawName or "").strip().lower().removeprefix("minecraft:")
    compact = cleaned.replace(" ", "")
    if compact in ITEM_ALIASES:
        return ITEM_ALIASES[compact]
    candidate = cleaned.replace(" ", "_")
    if _RESOURCE_ID_PATTERN.fullmatch(candidate):
        return candidate
    suggestions = difflib.get_close_matches(
        compact, list(ITEM_ALIASES) + KNOWN_ITEM_IDS, n=3, cutoff=0.5
    )
    hint = (
        " 혹시 이것인가요? " + ", ".join(f"`{name}`" for name in suggestions)
        if suggestions
        else " 영어 아이템 ID(예: diamond, iron_sword)나 등록된 한글 별칭을 입력하세요."
    )
    raise ValueError(f"아이템 이름을 찾지 못했습니다: `{(rawName or '').strip()}`.{hint}")


def parseItemCount(rawCount: str) -> int:
    """Validate the optional give count (기본 1, 최대 6400 = 100셋)."""
    cleaned = (rawCount or "").strip()
    if not cleaned:
        return 1
    if not cleaned.isdigit() or not 1 <= int(cleaned) <= 6400:
        raise ValueError("수량은 1~6400 사이의 숫자여야 합니다.")
    return int(cleaned)


def buildGiveCommand(playerName: str, rawItemName: str, rawCount: str = "") -> str:
    itemId = resolveItemId(rawItemName)
    count = parseItemCount(rawCount)
    return f"give {buildPlayerSelector(playerName)} minecraft:{itemId} {count}"


def buildEffectCommand(
    playerName: str,
    effectId: str,
    seconds: int = 300,
    amplifier: int = 0,
    hideParticles: bool = True,
) -> str:
    """포션 효과 부여. 기본적으로 파티클(거품)을 숨깁니다(#57).

    hideParticles는 바닐라 `effect give`의 마지막 인자로, true면 거품이
    보이지 않습니다. 표시를 원할 때만 False를 넘기세요.
    """
    safeEffect = _validateResourceId(effectId, "효과")
    safeSeconds = max(1, min(int(seconds), 1_000_000))
    safeAmplifier = max(0, min(int(amplifier), 255))
    return (
        f"effect give {buildPlayerSelector(playerName)} "
        f"minecraft:{safeEffect} {safeSeconds} {safeAmplifier}"
        f" {'true' if hideParticles else 'false'}"
    )


def buildEffectClearCommand(playerName: str) -> str:
    return f"effect clear {buildPlayerSelector(playerName)}"


def buildEnchantCommand(playerName: str, enchantId: str, level: int = 1) -> str:
    safeEnchant = _validateResourceId(enchantId, "인챈트")
    safeLevel = max(1, min(int(level), 255))
    return (
        f"enchant {buildPlayerSelector(playerName)} "
        f"minecraft:{safeEnchant} {safeLevel}"
    )


def buildForceEnchantCommand(playerName: str, enchantId: str, level: int = 1) -> str:
    """든 아이템에 호환·최대레벨 무시하고 인챈트 (RaspiMcOps 플러그인, #62).

    바닐라 `enchant`는 곡괭이에 날카로움을 못 걸고 레벨 상한도 강제하지만,
    이 명령은 플러그인의 `/enchantheld`를 호출해 제한 없이 부여합니다.
    플러그인이 정확한 이름(선택자 아님)을 받으므로 검증된 이름을 그대로 씁니다.
    """
    safeName = validateServerPlayerName(playerName)
    safeEnchant = _validateResourceId(enchantId, "인챈트")
    safeLevel = max(1, min(int(level), 255))
    return f"enchantheld {safeName} {safeEnchant} {safeLevel}"


def buildGamemodeCommand(playerName: str, mode: str) -> str:
    if mode not in GAMEMODES:
        raise ValueError("지원하지 않는 게임모드입니다.")
    return f"gamemode {mode} {buildPlayerSelector(playerName)}"


def buildTeleportToPlayerCommand(playerName: str, targetName: str) -> str:
    """Teleport one selected player to another online player."""
    if validateServerPlayerName(playerName) == validateServerPlayerName(targetName):
        raise ValueError("본인에게는 순간이동할 수 없습니다. 다른 대상을 선택하세요.")
    return f"tp {buildPlayerSelector(playerName)} {buildPlayerSelector(targetName)}"


def buildTeleportToCoordsCommand(
    playerName: str, dimension: str, x: float, y: float, z: float
) -> str:
    """Teleport a player to a saved coordinate-book place."""
    dimensionIds = {
        "overworld": "minecraft:overworld",
        "nether": "minecraft:the_nether",
        "the_end": "minecraft:the_end",
    }
    if dimension not in dimensionIds:
        raise ValueError("좌표의 차원 정보가 올바르지 않습니다.")
    if abs(x) > _MAX_HORIZONTAL or abs(z) > _MAX_HORIZONTAL or abs(y) > _MAX_VERTICAL:
        raise ValueError("좌표가 월드 경계를 벗어났습니다.")
    coordinates = " ".join(f"{value:g}" for value in (x, y, z))
    return (
        f"execute in {dimensionIds[dimension]} run "
        f"tp {buildPlayerSelector(playerName)} {coordinates}"
    )


def buildXpCommand(playerName: str, levels: int) -> str:
    safeLevels = max(1, min(int(levels), 1000))
    return f"experience add {buildPlayerSelector(playerName)} {safeLevels} levels"


def buildHealCommands(playerName: str) -> list[str]:
    """체력과 배고픔을 함께 회복시키는 두 개의 즉발 효과."""
    selector = buildPlayerSelector(playerName)
    return [
        f"effect give {selector} minecraft:instant_health 1 10 true",
        f"effect give {selector} minecraft:saturation 1 10 true",
    ]


# 무적(#75): 대미지 무효화(저항 5)에 재생·화염 저항·포화를 함께 걸어 체력이
# 줄지 않게 합니다. 저항은 증폭 4단계(=저항 V)가 대부분의 피해를 100% 막습니다.
# 모든 효과는 파티클을 숨겨(#57 원리) 게임 화면에 거품이 보이지 않습니다.
_INVINCIBILITY_EFFECTS = (
    ("resistance", 4),
    ("regeneration", 1),
    ("fire_resistance", 0),
    ("saturation", 0),
)

# 무적 지속 시간(초)의 안전 범위: 최소 1초, 최대 1시간.
MIN_INVINCIBLE_SECONDS = 1
MAX_INVINCIBLE_SECONDS = 3600


def parseInvincibleSeconds(rawSeconds: str | int) -> int:
    """Validate the invincibility duration (기본 5초, 1~3600초)."""
    if isinstance(rawSeconds, int):
        cleaned = str(rawSeconds)
    else:
        cleaned = (rawSeconds or "").strip()
    if not cleaned:
        return 5
    if not cleaned.isdigit():
        raise ValueError("무적 시간은 초 단위 숫자여야 합니다 (예: 5, 30, 300).")
    seconds = int(cleaned)
    if not MIN_INVINCIBLE_SECONDS <= seconds <= MAX_INVINCIBLE_SECONDS:
        raise ValueError("무적 시간은 1초에서 3600초(1시간) 사이여야 합니다.")
    return seconds


def buildInvincibilityCommands(playerName: str, seconds: int = 5) -> list[str]:
    """무적 세트를 한 번에 거는 effect 명령들(파티클 숨김)."""
    safeSeconds = max(MIN_INVINCIBLE_SECONDS, min(int(seconds), MAX_INVINCIBLE_SECONDS))
    return [
        buildEffectCommand(playerName, effectId, safeSeconds, amplifier, hideParticles=True)
        for effectId, amplifier in _INVINCIBILITY_EFFECTS
    ]


def buildInvincibilityClearCommands(playerName: str) -> list[str]:
    """무적을 즉시 해제 — 걸어 둔 효과만 골라 지웁니다."""
    selector = buildPlayerSelector(playerName)
    return [
        f"effect clear {selector} minecraft:{effectId}"
        for effectId, _ in _INVINCIBILITY_EFFECTS
    ]


# 내 통계(#68): 스코어보드 목표로 사망·처치 수를 집계합니다. 목표를 만든
# '시점부터' 집계되며 과거 기록은 소급되지 않습니다. (키, 목표명, 기준, 한글 라벨)
SCOREBOARD_STATS = (
    ("deaths", "mc_deaths", "deathCount", "사망 횟수"),
    ("kills", "mc_kills", "totalKillCount", "몹·플레이어 처치 수"),
    ("playerKills", "mc_pk", "playerKillCount", "플레이어 처치 수"),
)


def buildScoreboardSetupCommands() -> list[str]:
    """봇 시작 시 통계용 스코어보드 목표를 만드는 명령(이미 있으면 서버가 무시)."""
    return [
        f"scoreboard objectives add {objective} {criterion}"
        for _, objective, criterion, _ in SCOREBOARD_STATS
    ]


def buildScoreboardGetCommand(playerName: str, objective: str) -> str:
    """한 플레이어의 스코어보드 값을 조회하는 명령."""
    safeName = validateServerPlayerName(playerName)
    if objective not in {obj for _, obj, _, _ in SCOREBOARD_STATS}:
        raise ValueError("지원하지 않는 통계 목표입니다.")
    return f"scoreboard players get {safeName} {objective}"


def parseScoreboardValue(output: str) -> int:
    """'... has N [obj]' 형태의 응답에서 값을 읽습니다. 기록 없으면 0.

    주의(#84): 응답의 "아무 숫자"를 집으면 안 됩니다. 점수가 없을 때
    Paper는 "Can't get value of mc_deaths for QUI203; none is set"처럼
    플레이어 이름이 포함된 문장을 돌려주는데, 이름 속 숫자(203)를 점수로
    읽는 버그가 있었습니다. 반드시 'has N' 형태만 값으로 인정하고,
    '점수 없음' 응답은 0, 그 외 알 수 없는 응답은 오류로 처리합니다.
    """
    lowered = (output or "").casefold()
    if not lowered.strip():
        return 0
    # 점수가 아직 없는 플레이어: 바닐라/Paper의 두 가지 문구를 모두 처리.
    if "no score" in lowered or "none is set" in lowered:
        return 0
    match = re.search(r"\bhas\s+(-?\d+)\b", output or "")
    if match:
        return int(match.group(1))
    raise ValueError(
        f"통계 값을 읽지 못했습니다. 서버 응답: {(output or '').strip()[:120]}"
    )


def buildKickCommand(playerName: str, reason: str = "서버장이 퇴장시켰습니다.") -> str:
    safeName = validateServerPlayerName(playerName)
    safeReason = re.sub(r"[\r\n]", " ", reason).strip()[:100]
    return f"kick {safeName} {safeReason}"


def buildWorldSpawnAtPlayerCommand(playerName: str) -> str:
    """선택한 접속자가 서 있는 자리를 월드 스폰으로 지정.

    execute at은 그 플레이어가 있는 월드에서 setworldspawn을 실행하므로,
    호출 전에 반드시 플레이어가 오버월드에 있는지 확인해야 합니다
    (네더에서 실행하면 네더 월드의 스폰이 바뀌어 의미가 없습니다).
    """
    return (
        f"execute at {buildPlayerSelector(playerName)} run setworldspawn ~ ~ ~"
    )


def buildWorldSpawnCommand(x: int, y: int, z: int) -> str:
    """좌표를 직접 입력해 오버월드 스폰을 지정."""
    if abs(x) > _MAX_HORIZONTAL or abs(z) > _MAX_HORIZONTAL:
        raise ValueError("X/Z가 마인크래프트 월드 경계(±30,000,000)를 벗어났습니다.")
    if not -_MAX_VERTICAL <= y <= _MAX_VERTICAL:
        raise ValueError("Y가 안전한 범위(±2048)를 벗어났습니다.")
    return f"execute in minecraft:overworld run setworldspawn {x} {y} {z}"


# 스폰을 옮긴 뒤 정확히 그 지점에 리스폰되도록 분산 반경을 0으로 맞춥니다.
SPAWN_RADIUS_ZERO_COMMAND = "gamerule spawnRadius 0"


def buildGameruleQueryCommand(gameruleKey: str) -> str:
    if gameruleKey not in GAMERULES:
        raise ValueError("지원하지 않는 게임룰입니다.")
    return f"gamerule {GAMERULES[gameruleKey][0]}"


def buildGameruleSetCommand(gameruleKey: str, enabled: bool) -> str:
    if gameruleKey not in GAMERULES:
        raise ValueError("지원하지 않는 게임룰입니다.")
    return f"gamerule {GAMERULES[gameruleKey][0]} {'true' if enabled else 'false'}"


def parseGameruleValue(output: str) -> bool:
    """'Gamerule X is currently set to: true' 형태의 응답에서 값을 읽습니다."""
    lowered = (output or "").casefold()
    if lowered.rstrip().endswith("true") or ": true" in lowered:
        return True
    if lowered.rstrip().endswith("false") or ": false" in lowered:
        return False
    raise ValueError(f"게임룰 값을 읽지 못했습니다. 서버 응답: {(output or '').strip()[:120]}")


def buildDifficultyCommand(difficulty: str) -> str:
    if difficulty not in DIFFICULTIES:
        raise ValueError("지원하지 않는 난이도입니다.")
    return f"difficulty {difficulty}"


def parseDaysPlayed(timeQueryOutput: str) -> int | None:
    """'The time is N' 응답에서 플레이 일수를 읽습니다(`time query day`)."""
    match = re.search(r"(-?\d+)", timeQueryOutput or "")
    return int(match.group(1)) if match else None
