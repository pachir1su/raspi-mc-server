"""Parsing and presentation helpers for player data returned by RCON."""

import re

from bot.player_names import (
    FLOODGATE_SERVER_NAME,
    JAVA_PLAYER_NAME,
    validateJavaName,
)

PLAYER_NAME = JAVA_PLAYER_NAME
ONLINE_PLAYER_NAME = re.compile(
    rf"(?:{JAVA_PLAYER_NAME.pattern}|{FLOODGATE_SERVER_NAME.pattern})"
)

# 아이템 블록 내부에서 개별 필드를 찾는 패턴들(필드 순서와 무관하게 검색).
_SLOT_FIELD = re.compile(r"\bSlot:\s*(-?\d+)b?", re.IGNORECASE)
_ID_FIELD = re.compile(r"\bid:\s*[\"'](?:minecraft:)?([^\"']+)[\"']", re.IGNORECASE)
_COUNT_FIELD = re.compile(r"\bcount:\s*(\d+)b?", re.IGNORECASE)

# active_effects 필드 패턴.
_EFFECT_ID_FIELD = _ID_FIELD
_AMPLIFIER_FIELD = re.compile(r"\bamplifier:\s*(-?\d+)b?", re.IGNORECASE)
_DURATION_FIELD = re.compile(r"\bduration:\s*(-?\d+)", re.IGNORECASE)

# data get 단일 값 응답("... entity data: 19.0f")에서 숫자만 추출.
_NUMBER_TAIL = re.compile(r"(-?\d+(?:\.\d+)?)[bsfdL]?\s*$")

# 자주 나오는 포션 효과의 한글 이름(그 밖에는 영어 ID를 그대로 보여줌).
EFFECT_LABELS = {
    "speed": "신속",
    "slowness": "구속",
    "haste": "성급함",
    "mining_fatigue": "채굴 피로",
    "strength": "힘",
    "instant_health": "즉시 회복",
    "instant_damage": "즉시 피해",
    "jump_boost": "점프 강화",
    "nausea": "멀미",
    "regeneration": "재생",
    "resistance": "저항",
    "fire_resistance": "화염 저항",
    "water_breathing": "수중 호흡",
    "invisibility": "투명화",
    "blindness": "실명",
    "night_vision": "야간 투시",
    "hunger": "허기",
    "weakness": "나약함",
    "poison": "독",
    "wither": "시듦",
    "health_boost": "체력 증가",
    "absorption": "흡수",
    "saturation": "포만감",
    "glowing": "발광",
    "levitation": "공중 부양",
    "luck": "행운",
    "unluck": "불운",
    "slow_falling": "느린 낙하",
    "conduit_power": "전달체의 힘",
    "dolphins_grace": "돌고래의 우아함",
    "bad_omen": "불길한 징조",
    "hero_of_the_village": "마을의 영웅",
    "darkness": "어둠",
}

GAMEMODE_LABELS = {
    0: "서바이벌",
    1: "크리에이티브",
    2: "어드벤처",
    3: "관전",
}


def validatePlayerName(name: str) -> str:
    """Return a safe Java username or reject command-injection characters."""
    return validateJavaName(name)


def parseOnlinePlayers(output: str) -> list[str]:
    """Parse Paper's `list` response while preserving valid usernames only."""
    if ":" not in output:
        return []
    namesPart = output.rsplit(":", 1)[1].strip()
    if not namesPart:
        return []
    return [
        name for rawName in namesPart.split(",")
        if ONLINE_PLAYER_NAME.fullmatch(name := rawName.strip())
    ]


def _splitTopLevelBlocks(text: str) -> list[str]:
    """Extract each top-level `{...}` block from an SNBT list response.

    정규식 대신 중괄호 깊이를 따라가며 자릅니다. 최신 Paper는 아이템 필드
    순서가 제각각이고(components 등) 중첩 SNBT가 흔해서, 순서를 가정한
    패턴 매칭은 아이템을 통째로 건너뛰는 버그를 만들었습니다(#56).
    """
    blocks: list[str] = []
    depth = 0
    start = -1
    quote = ""
    previous = ""
    for index, character in enumerate(text):
        if quote:
            if character == quote and previous != "\\":
                quote = ""
        elif character in "\"'":
            quote = character
        elif character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                blocks.append(text[start : index + 1])
                start = -1
        previous = character
    return blocks


def _stripNestedStructures(block: str) -> str:
    """Drop nested `{...}`/`[...]` bodies so field regexes only see depth 1.

    셜커 상자·번들처럼 아이템 안에 또 아이템이 들어 있으면 안쪽의 id/count가
    바깥 아이템으로 잘못 읽히므로, 최상위 필드만 남깁니다.
    """
    result: list[str] = []
    depth = 0
    quote = ""
    previous = ""
    inner = block[1:-1] if block.startswith("{") and block.endswith("}") else block
    for character in inner:
        if quote:
            if depth == 0:
                result.append(character)
            if character == quote and previous != "\\":
                quote = ""
        elif character in "\"'":
            quote = character
            if depth == 0:
                result.append(character)
        elif character in "{[":
            depth += 1
        elif character in "}]":
            depth -= 1
        elif depth == 0:
            result.append(character)
        previous = character
    return "".join(result)


def parseInventoryItems(output: str) -> list[tuple[int | None, str, int]]:
    """Return (slot, itemId, count) tuples from a `data get ... Inventory` reply.

    Slot이 없는 목록(엔더상자 EnderItems 등)은 등장 순서를 슬롯 번호로
    사용할 수 있도록 slot을 None으로 돌려줍니다.
    """
    items: list[tuple[int | None, str, int]] = []
    for block in _splitTopLevelBlocks(output or ""):
        surface = _stripNestedStructures(block)
        idMatch = _ID_FIELD.search(surface)
        if not idMatch:
            continue
        slotMatch = _SLOT_FIELD.search(surface)
        countMatch = _COUNT_FIELD.search(surface)
        items.append(
            (
                int(slotMatch.group(1)) if slotMatch else None,
                idMatch.group(1),
                int(countMatch.group(1)) if countMatch else 1,
            )
        )
    return items


def slotLabel(slot: int) -> str:
    """Map Java inventory slot numbers to concise player-facing labels."""
    if 0 <= slot <= 8:
        return f"핫바 {slot + 1}"
    if 9 <= slot <= 35:
        return f"인벤토리 {slot - 8}"
    return {
        100: "부츠",
        101: "레깅스",
        102: "흉갑",
        103: "투구",
        -106: "왼손",
    }.get(slot, f"슬롯 {slot}")


def _formatItemLine(label: str, itemId: str, count: int) -> str:
    return f"**{label}** — `{itemId}` × {count}"


def summarizeInventorySections(output: str) -> list[tuple[str, str]]:
    """Group a full `Inventory` reply into (섹션 제목, 본문) embed fields.

    갑옷·왼손 / 핫바 / 인벤토리 순서로 나눠서 어느 칸에 무엇이 있는지
    한눈에 보이게 합니다(#56).
    """
    items = parseInventoryItems(output)
    equipment: list[tuple[int, str]] = []
    hotbar: list[tuple[int, str]] = []
    main: list[tuple[int, str]] = []
    for slot, itemId, count in items:
        if slot is None:
            continue
        line = _formatItemLine(slotLabel(slot), itemId, count)
        if 0 <= slot <= 8:
            hotbar.append((slot, line))
        elif 9 <= slot <= 35:
            main.append((slot, line))
        else:
            equipment.append((slot if slot >= 0 else 1000 + slot, line))
    sections: list[tuple[str, str]] = []
    for title, entries in (
        ("🛡️ 장비 (갑옷·왼손)", equipment),
        ("🔥 핫바", hotbar),
        ("🎒 인벤토리", main),
    ):
        if entries:
            body = "\n".join(line for _, line in sorted(entries))
            sections.append((title, body[:1000]))
    return sections


def summarizeEnderChest(output: str) -> str:
    """Format a `data get ... EnderItems` reply as one embed field body."""
    items = parseInventoryItems(output)
    lines = [
        _formatItemLine(
            f"칸 {slot + 1}" if slot is not None else f"칸 {index + 1}", itemId, count
        )
        for index, (slot, itemId, count) in enumerate(sorted(
            items, key=lambda item: (item[0] is None, item[0] or 0)
        ))
    ]
    return "\n".join(lines)[:1000]


def summarizeInventory(output: str, limit: int = 40) -> str:
    """Turn an `Inventory` reply into readable lines (flat, legacy callers)."""
    items = parseInventoryItems(output)
    if not items:
        cleaned = " ".join((output or "").split())
        return cleaned[:1800] or "인벤토리가 비어 있거나 확인할 수 없습니다."
    lines = [
        _formatItemLine(slotLabel(slot) if slot is not None else "칸 ?", itemId, count)
        for slot, itemId, count in items[:limit]
    ]
    if len(items) > limit:
        lines.append(f"…외 {len(items) - limit}칸 더")
    return "\n".join(lines)


def parseNumericData(output: str) -> float | None:
    """Read the numeric tail of a `data get entity <p> <path>` reply."""
    match = _NUMBER_TAIL.search((output or "").strip())
    return float(match.group(1)) if match else None


def _romanLevel(amplifier: int) -> str:
    """Turn an effect amplifier (0-based) into the in-game level text."""
    numerals = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
    level = amplifier + 1
    return numerals[level - 1] if 1 <= level <= len(numerals) else str(level)


def _formatDurationTicks(ticks: int) -> str:
    if ticks < 0:
        return "무한"
    totalSeconds = ticks // 20
    minutes, seconds = divmod(totalSeconds, 60)
    if minutes:
        return f"{minutes}분 {seconds}초" if seconds else f"{minutes}분"
    return f"{seconds}초"


def summarizeEffects(output: str) -> str:
    """Turn an `active_effects` reply into `신속 II — 4분 12초` lines (#61)."""
    lines: list[str] = []
    for block in _splitTopLevelBlocks(output or ""):
        surface = _stripNestedStructures(block)
        idMatch = _EFFECT_ID_FIELD.search(surface)
        if not idMatch:
            continue
        effectId = idMatch.group(1)
        amplifierMatch = _AMPLIFIER_FIELD.search(surface)
        durationMatch = _DURATION_FIELD.search(surface)
        amplifier = int(amplifierMatch.group(1)) if amplifierMatch else 0
        label = EFFECT_LABELS.get(effectId, effectId)
        line = f"✨ **{label} {_romanLevel(amplifier)}**"
        if durationMatch:
            line += f" — {_formatDurationTicks(int(durationMatch.group(1)))} 남음"
        lines.append(line)
    return "\n".join(lines)[:1500] or "적용 중인 포션 효과가 없습니다."


def summarizePlayerStats(
    healthOutput: str, foodOutput: str, levelOutput: str, gamemodeOutput: str
) -> str:
    """Combine four `data get` replies into a friendly status block (#61)."""
    health = parseNumericData(healthOutput)
    food = parseNumericData(foodOutput)
    level = parseNumericData(levelOutput)
    gamemode = parseNumericData(gamemodeOutput)
    lines = []
    if health is not None:
        hearts = health / 2
        heartsText = f"{hearts:g}" if hearts != int(hearts) else f"{int(hearts)}"
        lines.append(f"❤️ **체력** {health:g}/20 (하트 {heartsText}개)")
    else:
        lines.append("❤️ **체력** 확인 불가")
    lines.append(
        f"🍗 **허기** {food:g}/20" if food is not None else "🍗 **허기** 확인 불가"
    )
    lines.append(
        f"⭐ **레벨** {int(level)}" if level is not None else "⭐ **레벨** 확인 불가"
    )
    modeLabel = GAMEMODE_LABELS.get(int(gamemode)) if gamemode is not None else None
    lines.append(f"🎮 **게임모드** {modeLabel or '확인 불가'}")
    return "\n".join(lines)
