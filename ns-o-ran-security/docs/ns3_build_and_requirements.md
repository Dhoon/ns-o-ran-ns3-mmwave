# ns-O-RAN v1.0 빌드 & 필요사항 정리

가이드 §2~§9 + v1.0 README + OpenRAN Gym 튜토리얼 기준으로, **baseline(scenario-one
Traffic Steering)을 돌릴 수 있게** 하기까지 필요한 것들을 순서대로 정리.

---

## 0. 지금까지 상태

| 항목 | 상태 |
|---|---|
| ns-O-RAN **v1.0** 코드 | ✅ 포크(`Dhoon/ns-o-ran-ns3-mmwave`) + `temporal-misalignment-baseline` 브랜치, `code/ns-o-ran-ns3-mmwave`에 clone |
| contrib/oran-interface (E2 모듈) | ✅ 추가 (가이드 §7) |
| RIC / E2Sim / kpimon·rc xApp | ✅ clone 완료 (WSL `~/research/nsoran`) |
| **Docker** | ❌ 미설치 — **baseline 실행의 핵심 선행조건** |
| ns-3 빌드 | ⬜ 아직 (아래 2단계) |

- ns-3 베이스 버전: **3.33**, 빌드 시스템: **`waf`** (v1.0은 CMake/`ns3` 런처 없음)

---

## 1. 빌드 위치 결정 (중요)

ns-3는 C++ 수백 파일 빌드라 **파일시스템 성능이 빌드 시간을 좌우**함.

| 위치 | 빌드 속도 | VSCode 가시성 | 권장 |
|---|---|---|---|
| `/mnt/c/...` (지금 code/ 폴더) | **느림(5~10배)**, 가끔 권한/CRLF 문제 | 탐색기에서 바로 보임 | △ |
| WSL 네이티브 `~/research/...` | 빠름 | `\\wsl$\Ubuntu-22.04\...` 또는 Remote-WSL | ◎ |

**권장: VSCode에 "Remote - WSL" 확장 설치** → WSL 폴더를 직접 열면
가시성 + 빌드속도 둘 다 해결. (code/ 사본은 열람/백업용으로 둬도 됨)

---

## 2. ns-3 빌드 (baseline 쓰려면 필수)

### 2-1. 빌드 의존성 (가이드 §2, WSL Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential git cmake libsctp-dev lksctp-tools \
    autoconf automake libtool bison flex libboost-all-dev \
    g++ python3 python3-pip sqlite3 libsqlite3-dev
```
> ⚠ WSL에서 `sudo`에 **비밀번호 필요** — 이 단계는 당신이 직접 터미널에서 실행해야 함.
> SCTP(`libsctp-dev`)는 E2 통신 필수. sqlite는 ns-O-RAN 트레이스 저장에 쓰임.

### 2-2. 빌드 (가이드 §8, README)
```bash
cd <ns-o-ran-ns3-mmwave>        # waf 있는 디렉토리
./waf configure --enable-examples --enable-tests
./waf build
```
디버그 빌드가 필요하면 (run-simulations.sh 기본값):
```bash
./waf configure --build-profile=debug --out=build/debug
./waf build
```

### 2-3. 빌드 검증
```bash
./waf --run scratch/scratch-simulator     # ns-3 자체 동작 확인
```
→ 여기까지가 "**baseline 코드가 빌드되는 상태**". 단, 아직 *실행*은 RIC 필요(3단계).

---

## 3. baseline을 실제로 "실행"하려면 추가로 필요한 것 (가이드 §3~§11)

빌드만으론 scenario-zero/one이 안 돎 — E2가 RIC에 붙어야 하기 때문.

### 3-1. Docker 설치 ❌ (현재 없음, 선행 필수)
```bash
# Docker Engine (WSL Ubuntu) 또는 Docker Desktop + WSL integration
```

### 3-2. Near-RT RIC 기동 (가이드 §3)
```bash
cd ~/research/nsoran/colosseum-near-rt-ric/setup-scripts
./import-wines-images.sh
./setup-ric-bronze.sh
docker ps                      # e2term 떠있나 확인
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' e2term
#  → 이 E2TERM_IP 를 기록 (scenario 실행 시 --e2TermIp 에 사용)
```

### 3-3. 샘플 xApp 기동 (가이드 §4)
```bash
./start-xapp-ns-o-ran.sh       # → 컨테이너 안에서
cd /home/sample-xapp && ./run_xapp.sh
```

### 3-4. E2Sim 빌드 (가이드 §5)
```bash
cd ~/research/nsoran/oran-e2sim/e2sim
mkdir -p build && ./build_e2sim.sh 3   # 3 = 디버그 로깅
sudo ldconfig
```

### 3-5. Scenario Zero 스모크 테스트 (가이드 §9)
```bash
./waf --run "scratch/scenario-zero --e2TermIp=<E2TERM_IP>"
```
PASS 기준: E2 Setup → Subscription → Indication 메시지가 xApp까지 도달.

### 3-6. Scenario One = baseline (가이드 §11)
```bash
# controlFile 빈 파일 먼저 생성 (안 하면 크래시)
: > ts_actions_for_ns3.csv
./run-simulations.sh           # use_case=1 로 바꾸고 e2TermIp 교체 후
```
TS 설정: handoverMode=NoAuto, indicationPeriodicity=0.1s, controlPath=ts_actions_for_ns3.csv

---

## 4. 전체 선행조건 체크리스트 (순서대로)

```
[x] ns-O-RAN v1.0 clone + 브랜치 + contrib/oran-interface
[x] RIC/E2Sim/xApp repo clone
[ ] (당신) sudo apt 로 빌드 의존성 설치        ← 2-1
[ ] ./waf configure && ./waf build             ← 2-2  (baseline 빌드 완료 지점)
[ ] Docker 설치                                 ← 3-1  (실행 선행 필수)
[ ] RIC/E2Term 기동 + E2TERM_IP 확보           ← 3-2
[ ] 샘플 xApp 기동                              ← 3-3
[ ] E2Sim 빌드 (./build_e2sim.sh 3, ldconfig)  ← 3-4
[ ] Scenario Zero 통과 (E2 setup/sub/ind)      ← 3-5
[ ] Scenario One 실행 = aligned baseline        ← 3-6
[ ] baseline 커밋 + 태그 baseline-aligned-v1    ← 가이드 §14
```

---

## 5. 지금 당장 당신이 해줘야 하는 것 (sudo/설치 = 내가 못 함)

1. **빌드 의존성 설치** (2-1) — WSL 터미널에서 직접
2. **Docker 설치** (3-1) — baseline 실행하려면 필수

이 둘만 되면, 그 다음 빌드·기동·스모크테스트는 내가 스크립트로 진행 가능.
현재 내 권한으로는 WSL `sudo`(비번)와 Docker가 막혀 있어서 거기까지는 대신 못 함.
```
