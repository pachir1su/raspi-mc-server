# RaspiMcOps Paper 플러그인

Release ZIP에는 Java 25용 `RaspiMcOps` 플러그인과 `DeathBox` 플러그인
([death-box-design.md](death-box-design.md) 참고)이 포함됩니다. 봇 시작 시
각 번들 JAR을 검증하고 `/mnt/minecraft/live/plugins/`에 원자적으로
복사합니다. JAR이 바뀐 경우에만 Paper를 재시작합니다. Release 빌드 JAR이 없는
일반 소스 체크아웃에서는 이 단계를 건너뜁니다.

플러그인 설정은
`/mnt/minecraft/live/plugins/RaspiMcOps/config.yml`에 생성됩니다. 이 설정은
`.env`에 넣지 않습니다.

## 채팅 로그

`chat-log.enabled: true`이면 실제 게임 채팅을
`plugins/RaspiMcOps/chat.log`에 기록합니다. 이벤트 방식이므로 폴링하지 않고,
채팅이 없으면 쓰지 않으며, 첫 채팅이 발생할 때만 파일을 만듭니다. Discord
`/관리자` → **로그** 패널에서 미리 보거나 파일을 받을 수 있습니다.

## 스폰 자동 귀환

`MC_SPAWN_X/Y/Z`는 서버장이 특정 좌표를 강제할 때만 사용하는 선택 설정입니다.
값이 비어 있으면 Discord 스폰 구조 버튼이 제한된 `raspiops rescue` 명령을
호출합니다. 플러그인은 검증된 온라인 플레이어 정확히 한 명만 찾아 Paper의 실제
주 월드 스폰으로 이동합니다.

## 스폰 안전 구역

기본값은 주 월드의 현재 스폰을 중심으로 반경 16블록의 정사각형 구역입니다.
우회 권한이 없는 플레이어의 블록 파괴·설치·상호작용, 양동이 사용, 엔티티 공격,
피스톤 이동과 폭발 블록 피해를 막습니다. OP는
`raspimcops.spawn.bypass` 권한으로 우회합니다.

단, DeathBox 플러그인이 놓은 죽음 상자는 예외로 구역 안에서도 열 수 있습니다.
스폰에서 죽어도 본인 아이템을 회수할 수 있게 하기 위해서이며, 상자를 주인만
열 수 있게 하는 것은 DeathBox가 계속 담당합니다.

비공개 `/관리자` → **스폰 보호** 버튼이나 콘솔 명령을 사용합니다.

```text
spawnprotection status
spawnprotection on
spawnprotection off
spawnprotection toggle
```

토글 상태는 플러그인 설정에 저장됩니다. 반경이나 월드를 바꾸려면 서버를 정지한
뒤 `spawn-protection.radius` 또는 `spawn-protection.world`를 수정하고 Paper를
다시 시작합니다.

## 상자 잠금

`chest-lock.enabled: true`이면 상자·덫 상자·통·셜커 상자를 설치한 사람을
기록하고, 다른 플레이어가 열거나 부수지 못하게 막습니다. 남의 잠긴 상자에
붙여서 상자를 설치해 겹상자로 여는 것도 거부합니다. OP는
`raspimcops.chestlock.bypass` 권한으로 우회합니다. 호퍼를 통한 아이템 이동은
막지 않으므로, 중요하면 통이나 셜커 상자를 사용하세요.

비공개 `/관리자` → **상자 잠금** 버튼이나 콘솔 명령을 사용합니다.

```text
chestlock status
chestlock on
chestlock off
chestlock toggle
```

토글 상태는 플러그인 설정에 저장됩니다. 기능을 꺼도 기록된 소유자는 유지되어
다시 켜면 잠금이 그대로 살아납니다.

Death Box는 [death-box-design.md](death-box-design.md)에 설명된 별도
[`plugin/deathbox`](../../plugin/deathbox) 구현을 그대로 사용합니다. 다른 사망
보관 구현을 중복 설치하지 마세요.

## 빌드 검증

Paper API `26.1.2.build.74-stable`, Java 25, Gradle 9.1을 기준으로 합니다.
Release 워크플로는 JAR을 검증된 배포 ZIP에 넣기 전에 `clean test jar`를 실행합니다.
