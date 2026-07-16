"""Discord에 보여줄 오류 문구를 한글로 통일하는 헬퍼.

[유지보수 안내]
버튼·명령이 실패했을 때 영어 예외 메시지가 그대로 노출되지 않도록,
사용자에게 보내기 직전에 반드시 describeError()를 거칩니다.
- ValueError는 이 저장소 안에서 이미 한글로 만들어 던지므로 그대로 사용
- RCON 계열은 원인별 한글 안내로 변환 (영어 원문은 로그에만 남김)
- 새 예외 유형을 추가하면 여기에도 대응 문구를 추가하세요
"""

from bot.rcon import RconAuthError, RconConnectionError, RconError, RconTimeout


def describeError(error: BaseException) -> str:
    """Return one short, friend-readable Korean sentence for an exception."""
    if isinstance(error, RconAuthError):
        return (
            "서버 원격 접속 비밀번호가 일치하지 않습니다. "
            "`.env`의 `RCON_PASSWORD`와 `server.properties`의 `rcon.password`를 확인하세요."
        )
    if isinstance(error, RconTimeout):
        return "서버 응답이 늦습니다 — 서버가 켜지는 중이거나 과부하일 수 있습니다. 잠시 후 다시 시도하세요."
    if isinstance(error, (RconConnectionError, RconError)):
        return "서버에 연결할 수 없습니다 — 서버가 꺼져 있거나 시작 중입니다."
    if isinstance(error, ValueError):
        # 저장소 안의 검증 오류는 이미 한글 문장으로 만들어 던집니다.
        return str(error) or "입력값이 올바르지 않습니다."
    if isinstance(error, PermissionError):
        return "파일 접근 권한이 없습니다. 라즈베리파이의 폴더 권한을 확인하세요."
    if isinstance(error, OSError):
        detail = str(error).strip()
        return f"시스템 작업에 실패했습니다{f' ({detail[:120]})' if detail else ''}."
    detail = str(error).strip()
    return f"작업을 완료하지 못했습니다{f': {detail[:200]}' if detail else '.'}"
