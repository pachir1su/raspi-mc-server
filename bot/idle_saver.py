"""무인 절전(#91)의 상태 전이 판단 — RCON 없이 순수 함수로 검증 가능.

서버가 비어 있을 때 라즈베리파이의 CPU·발열·전력을 낮추기 위해, 접속자가
한동안 0명이면 절전(eco) 모드로 들어가고 누군가 접속하면 즉시 빠져나옵니다.
실제 RCON 명령·게임룰 복원은 bot/cogs/admin.py의 스케줄러가 담당하고,
여기서는 "지금 무엇을 해야 하는가"만 결정합니다.
"""

# 상태 전이 결과.
ENTER = "enter"  # 절전 모드로 진입(랜덤 틱·스폰 청크 정지)
EXIT = "exit"    # 절전 모드 해제(원래 값 복원)
NONE = "none"    # 아무 것도 하지 않음


def decideIdleAction(
    playersOnline: int | None,
    emptyForMinutes: float,
    ecoActive: bool,
    thresholdMinutes: float,
) -> str:
    """무인 절전 상태 머신의 다음 동작을 결정합니다.

    - playersOnline is None: RCON을 못 읽은 것이므로 현재 상태를 그대로 둡니다
      (섣불리 복원했다가 서버가 죽은 사이 값이 꼬이는 것을 피함).
    - 접속자가 1명이라도 있으면: 절전 중이었다면 해제, 아니면 그대로.
    - 비어 있고 임계 시간 이상 지났으며 아직 절전 전이면: 진입.
    """
    if playersOnline is None:
        return NONE
    if playersOnline > 0:
        return EXIT if ecoActive else NONE
    if not ecoActive and emptyForMinutes >= thresholdMinutes:
        return ENTER
    return NONE
