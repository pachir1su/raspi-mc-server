# 친구 도구: 계정 연동, 구조, 좌표북, 일지, 건강 점수

Discord 봇은 관리자가 승인한 친구에게 범위가 좁은 셀프서비스 기능만 제공합니다.
친구를 마인크래프트 op로 만들지 않으며, 친구가 입력한 임의 RCON 문자열을 실행하지
않습니다.

## 1. Raspberry Pi 설정

Pi에 있는 기존 `.env`를 수정합니다. 실제 값이 든 파일은 커밋하지 마세요.

```bash
cd ~/raspi-mc-server
nano .env
```

다음 값을 추가하거나 수정합니다.

```dotenv
# 친구용 cog 활성화. 기존 관리 명령은 계속 관리자 허용목록으로 보호됨.
PUBLIC_COMMANDS_ENABLED=true

# 런타임 JSON과 업로드 사진을 마운트된 HDD에 저장.
MC_STATE_DIR=/mnt/minecraft/bot-state

# /구조 스폰이 사용하는 고정 목적지. 기본 좌표는 사용하지 않음.
MC_SPAWN_DIMENSION=overworld
MC_SPAWN_X=0.5
MC_SPAWN_Y=80
MC_SPAWN_Z=0.5

# 선택 사항: 외부 웹 지도 URL. 웹 지도를 배포하기 전에는 비워 둠.
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
```

스폰 차원은 `overworld`, `nether`, `the_end` 중 하나입니다. 좌표는 숫자여야 하며
X/Z는 ±30,000,000, Y는 -2048…2048 범위여야 합니다.

구조 스폰 위치를 고르는 방법:

1. 서버장 마인크래프트 계정으로 서버에 접속합니다.
2. 구조된 친구가 도착할 안전한 블록 위에 정확히 섭니다.
3. **F3**을 눌러 XYZ를 확인하거나, 관리자 `/플레이어` 위치 보기로 좌표를 확인합니다.
4. 그 값을 `MC_SPAWN_X/Y/Z`에 넣습니다. 블록 경계에 걸리지 않게 X/Z에 `.5`를
   더해 블록 중앙으로 맞추는 것을 권장합니다.
5. 목적지가 밝고 막혀 있지 않으며 월드 경계 안인지 확인합니다.

`MC_MAP_URL_TEMPLATE`은 실제 배포한 웹 지도의 URL 형식과 맞아야 합니다.
`{dimension}`, `{x}`, `{y}`, `{z}` 자리표시자를 쓸 수 있습니다. 봇은 링크만 만들고
지도를 렌더링하거나 폴링하지 않습니다. 지도 URL 형식이 다르면 브라우저에서 한
좌표를 연 뒤 URL을 복사하고 좌표 값을 해당 자리표시자로 바꾸세요. 웹 지도가 없으면
값을 비워 두면 되며, 지도 링크 없이 좌표북은 그대로 사용할 수 있습니다.

`.env` 저장 후 봇을 재시작하고 로그를 확인합니다.

```bash
sudo systemctl restart mc-discord-bot.service
sudo systemctl status mc-discord-bot.service --no-pager
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

## 2. 친구 계정 연동

친구가 실행:

```text
/연동 요청 마크닉:<정확한 닉네임> 에디션:<Java 또는 Bedrock>
```

서버장이 대기 요청 확인:

```text
/연동 목록
```

서버장이 해당 Discord 사용자를 선택해 승인:

```text
/연동 승인 사용자:<Discord 멤버>
```

친구는 `/연동 상태`로 결과를 확인합니다. Discord 계정이나 마크닉이 바뀌면
`/연동 해제`로 기존 연결을 해제하세요. Java 이름은 일반적인 1~16자 형식을
따르고, Bedrock 게이머태그는 공백도 받을 수 있습니다. 두 경우 모두 명령 삽입에
사용될 수 있는 문자는 거부합니다.

승인 전에 Java는 `whitelist add`, Bedrock은 Floodgate의 `fwhitelist add`를
자동 실행합니다. 서버 변경이므로 `/연동 승인`은 계속 `ADMIN_USER_IDS` 뒤에
있습니다. 친구 입장 허용을 위해 두 번째 작업을 할 필요는 없습니다.

## 3. 연결된 본인 계정만 구조

- `/구조 스폰`은 명령을 실행한 Discord 사용자에게 승인된 마크닉만 이동합니다.
  플레이어가 온라인이어야 합니다. 목적지는 고정 `MC_SPAWN_*` 설정이며 친구가
  대상·좌표·RCON 명령을 입력할 수 없습니다.
- `/구조 내위치`는 연결된 본인 온라인 플레이어의 차원과 XYZ만 읽습니다.

관리자의 계정 연동 승인이 이 고정 TP 한 가지에 대한 위임 권한입니다. 일반 서버
변경, 원시 `/마크명령`, 시작·정지, 백업, 화이트리스트, 사고 대응, 월드 관리 명령은 모두
계속 `ADMIN_USER_IDS` 뒤에 있습니다.

## 4. 좌표북과 사진

승인된 친구와 관리자는 다음 명령을 사용합니다.

```text
/좌표 추가 이름:<이름> 차원:<선택> x:<x> y:<y> z:<z> 설명:<선택> 사진:<선택>
/좌표 목록
/좌표 보기 이름:<이름>
/좌표 삭제 이름:<이름>
```

사진은 PNG, JPEG, WebP, GIF 형식과 5MiB 이하만 받습니다. 봇은 사진을 한 번
다운로드해 `MC_STATE_DIR/friend-media`에 보관하므로 만료될 수 있는 Discord 첨부 URL에
의존하지 않습니다. 친구는 자신이 등록한 좌표만 삭제할 수 있고 관리자는 모두 삭제할
수 있습니다. Pi에서 읽기 비용과 Discord 출력을 작게 유지하려고 좌표는 250곳으로
제한합니다.

## 5. 서버 일지

승인된 친구와 관리자는 다음 명령을 사용합니다.

```text
/일지 추가 메시지:<내용> 사진:<선택>
/일지 최근 개수:<1-20>
/일지 보기 일지번호:<최근에 표시된 ID>
```

구조와 좌표 저장 이벤트는 자동으로 일지에 추가됩니다. 일지는 쓰기 비용이 작은
추가 전용 JSONL을 사용하고, 2MiB를 넘으면 최신 1,000개만 남기도록 정리합니다.
선택 사진은 같은 5MiB 로컬 저장 정책을 사용합니다.

## 6. 요청할 때만 계산하는 서버 건강 점수

`/서버점수`는 Paper TPS, RCON 연결, CPU 온도, 5분 부하, 메모리, HDD 여유 공간,
Raspberry Pi 저전압·스로틀 플래그를 한 번 측정합니다. 0~100점, 등급, 모든 감점
이유를 보여줍니다. 명령을 실행할 때만 동작하며 새 백그라운드 루프, 청크 검색,
추가 서버 틱 작업은 없습니다.

## 런타임 파일과 백업

권장 HDD 설정을 사용하면 다음 파일이 `/mnt/minecraft/bot-state` 아래에 생깁니다.

- `player-links.json`
- `places.json`
- `server-diary.jsonl`
- `friend-media/`

Discord 사용자 ID, 마크닉, 좌표, 일지 내용, 사진이 들어 있으므로 다른 사설 서버
데이터처럼 보호하고 호스트 수준 HDD 백업에 이 폴더를 포함하세요. Git에서는
무시됩니다.

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 친구에게 기능 비활성화 메시지가 표시됨 | `PUBLIC_COMMANDS_ENABLED=true` 설정 후 봇 재시작. |
| 연동이 계속 승인 대기 | 서버장이 `/연동 목록` 확인 후 `/연동 승인` 실행. |
| 구조 스폰 미설정 오류 | `MC_SPAWN_DIMENSION/X/Y/Z` 네 값을 모두 설정하고 재시작. |
| Bedrock 승인에서 화이트리스트 명령을 모른다고 나옴 | `python -m bot.main --setup`을 다시 실행해 Java+Bedrock을 고르고 두 플러그인 설정 생성 여부 확인. |
| 구조/위치 조회가 플레이어를 못 찾음 | 연결된 정확한 Java/Floodgate 계정으로 현재 접속 중인지 확인. |
| 사진 업로드 실패 | 5MiB 미만 지원 이미지인지, `MC_STATE_DIR` 권한·용량이 충분한지 확인. |
| 지도 링크가 없음 | `MC_MAP_URL_TEMPLATE` 설정. 지도 플러그인이 없으면 실시간 지도 링크도 없음. |
| 지도 링크가 엉뚱한 곳을 엶 | 배포한 지도의 실제 URL 형식에 템플릿을 맞춤. |
| 건강 점수에서 HDD 여유가 0으로 표시됨 | `/mnt/minecraft` 마운트 확인. 필수 마운트가 없으면 비정상으로 판정함. |

### 완전히 새로운 Bedrock 계정의 최초 접속

Floodgate 공식 안내에 따르면 `fwhitelist add <게이머태그>`는 이전에 어떤 Geyser
서버에든 접속한 기록이 있는 계정만 바로 찾을 수 있습니다. 완전히 새 Xbox 계정은
Floodgate가 아직 이름을 몰라 첫 승인이 실패할 수 있습니다.

가능하면 외부 Bedrock 포트포워딩을 열기 전 LAN에서 처리합니다. 정확한 친구가 바로
접속할 준비를 한 짧은 점검 시간에:

```text
whitelist off
# 친구가 Bedrock으로 한 번 접속을 시도해 Floodgate가 계정을 인식하게 함
fwhitelist add 정확한게이머태그
whitelist on
whitelist reload
```

로컬 RCON 또는 관리자 전용 `/마크명령`으로만 실행하고 친구에게 이 명령 권한을 주지 않습니다.
중간 단계가 실패해도 즉시 화이트리스트를 다시 켜고 `whitelist list`로 확인한 다음
`/연동 승인`을 다시 실행합니다. 화이트리스트를 끈 상태로 계속 운영하지 마세요.
공식 [Geyser 화이트리스트 FAQ](https://geysermc.org/wiki/geyser/faq/)도 참고합니다.

Death Box는 의도적으로 분리했습니다. Paper 플러그인 설계와 테스트 계획은
[death-box-design.md](death-box-design.md)를 참고하세요.
