# Death Box(Paper 플러그인)

Death Box는 사망 시 드롭 아이템을 용암·폭발·디스폰으로 잃지 않도록, 소유자만 열 수
있는 보호된 상자에 보관합니다. [`plugin/deathbox`](../../plugin/deathbox)에 있는 작은
**Paper 플러그인**으로 구현되어 있으며, Discord RCON 봇으로는 구현하지 **않습니다**.
RCON은 사망 로그가 도착한 뒤에야 반응할 수 있어 그사이 아이템이 사라질 수 있고,
아이템 메타데이터·중첩 컨테이너·인챈트·소유권을 안전하게 복원할 수 없기 때문입니다.

## 동작 방식

플러그인은 이벤트 기반이며 사망·상자 접근·가벼운 시간당 만료 정리 시점에만
동작합니다. RCON 폴링, 로그 파싱, 엔티티 전체 검색, 강제 청크 로딩은 하지 않습니다.

1. 플레이어 사망 이벤트를 **일반(normal)** 우선순위로 받고, `keepInventory`이거나
   드롭이 없는 사망은 무시합니다. 더 높은 우선순위의 묘비 플러그인이 우선합니다.
2. 이벤트의 전체 `ItemStack`(인벤토리·방어구·보조 손 모두 드롭에 포함)을 메모리로
   복사합니다.
3. 복사한 드롭을 비워 아이템이 위험한 바닥 엔티티로 생성되지 않게 합니다.
4. 사망 블록 주변만 **제한 범위**로 탐색합니다(기본 반경 4, 최대 8로 하드 제한).
   청크나 월드 전체는 절대 검색하지 않습니다.
5. 이중 상자(54칸, 가득 찬 인벤토리도 수용)를 놓고 아이템을 넣습니다. 두 상자가
   실제로 합쳐졌는지 런타임에 확인합니다. 공허·용암·월드 경계·빈자리 부족으로
   안전한 블록이 없으면 아이템을 지우지 않고 플러그인 내부 **가상 상자**로 보관한 뒤
   플레이어에게 알립니다.
6. Paper 영속 데이터 API로 상자 블록에 사망 플레이어 UUID와 고유 상자 ID를
   기록하고, 좌표는 해당 플레이어에게만 표시합니다.
7. 상자가 비면(닫을 때 감지) 레코드를 삭제합니다. 선택적 만료 시간은 서버장이
   설정하며 기본값은 비활성화입니다.

물리 상자는 소유자·ID 태그를 블록 자체에 담아 두므로(인덱스 없이도 재시작 후 접근
검사가 유지됨), 원자적으로 기록되는 작은 `boxes.yml` 인덱스는 `/deathbox list|locate`
질의 응답과 가상 상자 보관에만 쓰이며 월드를 검색하지 않습니다. 시작 시 알고 있는
레코드만 로드하고 청크를 강제로 로드하지 않습니다.

## 소유권과 안전

- 기본 접근자는 사망한 플레이어와 관리자(`deathbox.admin`)뿐입니다.
  `friends-can-open`을 켜면 `deathbox.friend` 권한이 있는 플레이어도 열 수 있습니다.
- 상자는 권한 없는 열람, 호퍼 흡입, 폭발, 피스톤 이동, 수동 파괴로부터 보호됩니다.
  아이템을 되찾으려면 소유자가 상자를 열어 비우면 되고, 그러면 상자가 스스로
  제거됩니다.
- 아이템 메타데이터는 그대로 보존합니다. 실제 `ItemStack`으로 저장하며(가상 상자는
  Bukkit 객체 직렬화 사용) 명령 문자열로 직렬화하지 않습니다.
- 배치는 월드 경계·높이 제한·기존 블록·액체를 존중합니다. 다른 묘비 플러그인
  (Graves, GravesX, AngelChest, DeadChest, SavageDeathChest 등)이 감지되면 아이템
  복제를 피하기 위해 시작 시 DeathBox를 스스로 비활성화합니다.

> 구역/토지 보호 플러그인: DeathBox는 이미 있는 블록에는 배치하지 않지만, 아직
> WorldGuard/GriefPrevention 등의 토지 소유권 검사와는 연동하지 않습니다. 보호
> 플러그인을 쓴다면 배치 동작을 먼저 확인하거나(아래 체크리스트 참고),
> `search-radius`를 작게 유지하세요.

## 빌드

JDK 21과 Maven이 필요하며, PaperMC Maven 저장소에 접근할 수 있어야 합니다.

```bash
cd plugin/deathbox
mvn -B package
# → target/DeathBox-1.0.0.jar
```

Pi에서 돌리는 Paper 버전에 맞춰 `plugin/deathbox/pom.xml`의 `<paper.api.version>`을
설정하세요. `plugin/deathbox/` 아래가 바뀔 때마다 CI도
`.github/workflows/plugin-build.yml`로 플러그인을 빌드합니다.

## 설치

1. `target/DeathBox-1.0.0.jar`를 서버의 `plugins/` 폴더에 복사합니다.
2. 서버를 한 번 시작(또는 재시작)해 `plugins/DeathBox/config.yml`을 생성합니다.
3. 필요하면 설정을 수정한 뒤 재시작합니다.

## 설정

`plugins/DeathBox/config.yml` (이 값들은 봇의 `.env`나 `server.properties`가 아니라
플러그인 자체 설정에 둡니다):

```yaml
enabled: true
container: double-chest   # double-chest | chest | barrel
search-radius: 4          # 제한 범위, 1~8로 clamp
expire-hours: 0           # 0이면 만료하지 않음
friends-can-open: false
fallback-virtual-box: true
```

## 명령

| 명령 | 권한 | 용도 |
|---|---|---|
| `/deathbox locate` | 상자 소유자 | 자신의 최신 상자 좌표 표시. |
| `/deathbox list` | 상자 소유자 | 자신의 활성 상자 목록 표시. |
| `/deathbox recover <id>` | 관리자 | 가상 대체 상자를 인벤토리로 복구. |
| `/deathbox purge <id> confirm` | 관리자 | 명시적 확인 후 상자 삭제. |

권한: `deathbox.use`(기본: 전체), `deathbox.friend`(기본: 없음),
`deathbox.admin`(기본: op). Discord에는 나중에 상자 좌표를 **읽기 전용**으로만 노출할
수 있으며, 생성·캡처·복구·삭제는 플러그인 내부에 유지합니다.

## 검증 체크리스트(실서버에서 확인)

정적 검토와 CI 컴파일만으로는 실제 플레이 동작을 확인할 수 없습니다. 실제 Pi에서
신뢰하기 전에 다음을 확인하세요.

- 일반 인벤토리, 방어구, 보조 손, 인챈트, 번들, 셜커 상자.
- 용암, 공허, 폭발, 좁은 동굴, 물, 월드 경계, 보호 구역.
- 27칸 초과 사용과 완전히 가득 찬 인벤토리.
- 사망 직후 재시작과 상자를 연 상태에서 재시작.
- 동시 사망, 연속 사망, 같은 좌표에 여러 상자 생성.
- `keepInventory=true`, 다른 사망 플러그인, 호퍼 접근, 폭발, 권한 없는 플레이어.
- Paper timings/profile 비교로 유휴 틱·청크 로드 부하가 없음을 확인.
