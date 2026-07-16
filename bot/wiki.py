"""In-game help wiki registry for the `/위키` command (issue #71).

각 항목은 저장소의 `docs/` 마크다운 문서 하나를 가리킵니다. 봇은 문서를
직접 붙여넣지 않고 GitHub의 렌더된 `.md` 주소로 안내만 합니다 — 문서는
이미 한국어/영어로 관리되고 있으므로 링크만 최신으로 유지하면 됩니다.

새 문서를 노출하려면 WIKI_PAGES에 (키, 한글 라벨, 문서 파일명)만 추가하세요.
문서 파일은 docs/ko 와 docs/en 양쪽에 같은 이름으로 존재해야 합니다.
"""

import os

# 저장소 문서 링크의 기본 주소. 운영 중 포크나 브랜치가 바뀌면 Pi의 .env에서
# MC_WIKI_BASE_URL 로 덮어쓸 수 있습니다(끝의 슬래시는 없어도 됩니다).
DEFAULT_WIKI_BASE_URL = (
    "https://github.com/pachir1su/raspi-mc-server/blob/main/docs"
)

# (키, 한글 라벨, 문서 파일명) — 플레이어에게 가장 도움이 되는 안내서만 골랐습니다.
WIKI_PAGES = (
    ("brewing", "🧪 양조(포션)", "brewing.md"),
    ("enchantments", "✨ 인챈트", "enchantments.md"),
    ("status-effects", "🌀 상태 효과", "status-effects.md"),
    ("food", "🍖 음식", "food.md"),
    ("farming", "🌾 농사·번식", "farming-and-breeding.md"),
    ("ores", "⛏️ 광물·자원", "ores-and-resources.md"),
    ("villager", "🧑‍🌾 주민 거래", "villager-trading.md"),
    ("friend-tools", "🧰 친구 도구 사용법", "friend-tools.md"),
    ("server-features", "🗺️ 서버 기능 안내", "server-features.md"),
)

_PAGES_BY_KEY = {key: (label, doc) for key, label, doc in WIKI_PAGES}


def wikiBaseUrl() -> str:
    """Return the configured docs base URL without a trailing slash."""
    configured = os.getenv("MC_WIKI_BASE_URL", "").strip()
    return (configured or DEFAULT_WIKI_BASE_URL).rstrip("/")

def _localePath(language: str) -> str:
    """Map a language code to its docs subdirectory (default Korean)."""
    return "en" if language == "en" else "ko"


def wikiPageUrl(key: str, language: str = "ko") -> str:
    """Build the GitHub URL for one wiki page in the requested language."""
    if key not in _PAGES_BY_KEY:
        raise ValueError(f"등록되지 않은 위키 문서입니다: {key}")
    _, doc = _PAGES_BY_KEY[key]
    return f"{wikiBaseUrl()}/{_localePath(language)}/{doc}"


def wikiPageLabel(key: str) -> str:
    """Return the human-readable Korean label for one wiki page."""
    return _PAGES_BY_KEY[key][0]
