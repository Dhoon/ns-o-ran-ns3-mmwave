# 다른 PC에서 baseline sweep 돌리기

TMC 2024 논문 재현용 baseline 시뮬레이션(RAN RRM / SON1 / SON2)을 새 PC에서 처음부터
설치해 돌리는 절차. RIC, xApp, Docker는 필요 없다(offline 실행).

작성 2026-11-09. 기준 PC: i9-11900(8코어/16스레드), WSL2 Ubuntu 22.04, RAM 15 GB.

## 0. 무엇을 돌리나

| 항목 | 값 |
|---|---|
| 주파수 | 850 MHz (`--configuration=0`, ISD 1700 m) |
| UE | gNB당 6 / 9 / 12명 (총 42 / 63 / 84) |
| baseline | `Threshold`(RAN RRM), `FixedTtt`(SON1), `DynamicTtt`(SON2) |
| seed | 1~10 |
| 시뮬레이션 길이 | 30 s |
| 총 실행 수 | 3 × 3 × 10 = **90** |

논문 규모(UE 5단계 × 주파수 2 × 67 seed = 2,010회) 대비 계산량 약 3%로 줄인 범위다.
배경과 근거: `paper_reproduction_spec.md`, `../experiment_metadata.txt`.

예상 비용: 단일 코어 속도 기준 약 640 코어·시간. 기준 PC(16개 동시 실행 = 단독 대비 처리량
8.4배)에서 1.6~3.2일. 코어가 많을수록 거의 비례해서 줄어든다. GPU는 쓰지 않는다
(ns-3는 단일 스레드 CPU 프로그램).

## 1. 새 PC 요구사항

- Ubuntu 22.04 (네이티브 또는 WSL2). 다른 배포판은 검증 안 함.
- **물리 코어 수가 속도를 좌우한다.** 실행 하나가 코어 하나를 쓴다.
- RAM: 동시 실행 수 × 약 1~1.5 GB + 여유 3 GB (UE 84명 × 30 s 메모리는 아직 미측정, 추정치).
- 디스크: 결과 약 50 GB + 빌드 약 10 GB.
- **절전 모드 끄기.** 절전에 들어가면 실행이 멈춘다.

## 2. 패키지 설치 (sudo 필요)

```bash
sudo apt-get update
sudo apt-get install -y build-essential g++ git cmake python3 \
    libsctp-dev lksctp-tools autoconf automake libtool bison flex \
    libboost-all-dev sqlite3 libsqlite3-dev time
```

`time`은 `/usr/bin/time`(실행 시간·메모리 기록)용이다. 빠지면 스크립트가 실패한다.
기준 PC 버전: GCC 11.4.0, CMake 3.22.1, Python 3.10.12.

## 3. e2sim 설치

ns-O-RAN의 E2 모듈이 `libe2sim`에 링크되므로, offline 실행이라도 먼저 설치해야 빌드된다.

```bash
mkdir -p ~/research/nsoran && cd ~/research/nsoran
git clone https://github.com/wineslab/ns-o-ran-e2-sim.git oran-e2sim
cd oran-e2sim && git checkout 951b3e9        # develop 브랜치, 기준 PC와 같은 커밋
cd e2sim && mkdir -p build
./build_e2sim.sh 2                            # .deb 생성 후 e2sim-dev 설치, ldconfig (sudo 물어봄)
```

## 4. ns-O-RAN 받기

```bash
cd ~/research/nsoran
git clone -b paper-repro-master https://github.com/Dhoon/ns-o-ran-ns3-mmwave.git
cd ns-o-ran-ns3-mmwave
git log --oneline -1        # paper-repro-master 최신 커밋인지 확인

cd contrib
git clone https://github.com/o-ran-sc/sim-ns3-o-ran-e2.git oran-interface
git -C oran-interface checkout cf1a4bc
cd ..
```

`paper-repro-master`는 upstream master `8c42089d`에 아래 두 패치를 얹은 브랜치다.
1. `scratch/scenario-one.cc:430`: 850 MHz ISD 1000 → 1700 m (논문 값).
2. `src/network/model/byte-tag-list.cc:27`: `USE_FREE_LIST` 비활성화. 없으면 full-buffer
   부하에서 메모리가 시간에 따라 초선형으로 늘어난다. 출력 결과는 패치 전과 동일함을 확인했다.

경로를 `~/research/nsoran/ns-o-ran-ns3-mmwave`가 아닌 곳에 두면, 아래 스크립트 실행 전에
`export NSORAN=<경로>`를 해 둔다.

## 5. 빌드 (optimized)

```bash
cd ~/research/nsoran/ns-o-ran-ns3-mmwave
./ns3 configure --build-profile=optimized --enable-examples
./ns3 build scenario-one
ls build/optimized/scratch/ns3.38.rc1-scenario-one-optimized    # 있어야 함
```

- 반드시 이 PC에서 빌드한다. optimized 프로필은 `-march=native`라서 다른 CPU에서 만든
  바이너리를 복사해 오면 안 돌 수 있다.
- 확인용: `grep -E "CMAKE_BUILD_TYPE|NS3_LOG|NS3_ASSERT" cmake-cache/CMakeCache.txt`
  → `release`, `OFF`, `OFF`이어야 한다. debug 빌드나 로그가 켜져 있으면 크게 느려진다.

## 6. 짧은 점검 (약 5분)

스크립트와 출력이 제대로 나오는지 9개 실행(0.3 s)으로 확인한다.

```bash
cd ~/research/nsoran/ns-o-ran-ns3-mmwave
SIMTIME=0.3 SEEDS=1 OUT=/tmp/sweep_check bash ns-o-ran-security/scripts/run_baseline_sweep.sh 9
find /tmp/sweep_check -name DONE | wc -l        # 9 이어야 함
cat /tmp/sweep_check/progress.log
ls /tmp/sweep_check/Threshold/ues6/seed01       # cu-cp/cu-up/du-cell-*.txt, UeHandover*.txt 등
```

## 7. 동시 실행 수 정하기 (약 15~30분)

```bash
bash ns-o-ran-security/scripts/measure_parallel_throughput.sh "1 8 16 24 32"
```

- 괄호 안 목록은 코어 수에 맞게 바꾼다(예: 물리 32코어면 `"1 16 32 48 64"`).
- `sim-s_per_wall-hour`(처리량)가 가장 큰 N을 고른다. 보통 논리 코어 수 근처다.
- 기준 PC 결과: 1개 17.7, 8개 96.6, 12개 127.8, 16개 148.5 (16개가 최적, 단독 대비 8.4배).
- 측정 결과는 `results/raw/throughput/`에 남는다. 끝나면 지워도 된다.

## 8. 본 실행

```bash
cd ~/research/nsoran/ns-o-ran-ns3-mmwave
nohup setsid bash ns-o-ran-security/scripts/run_baseline_sweep.sh <N> > /dev/null 2>&1 &
```

- `setsid`로 띄우면 터미널이나 SSH를 닫아도 계속 돈다.
- 스크립트는 메모리 여유(MemAvailable)가 3 GB 아래면 새 실행을 시작하지 않고 기다린다
  (`MIN_FREE_MB`로 조정).

진행 확인:
```bash
R=ns-o-ran-security/results/raw/baseline
tail -5 $R/progress.log
find $R -name DONE | wc -l            # 90이면 끝
grep FAIL $R/progress.log             # 실패 목록
```

중단과 재개:
```bash
pkill -f run_baseline_sweep.sh; pkill -f scenario-one-optimized    # 중단
# 다시 8번 명령을 실행하면 DONE 있는 실행은 건너뛰고 나머지만 돈다 (중단된 실행은 처음부터)
```

## 9. 결과

폴더 구조: `results/raw/baseline/{Threshold|FixedTtt|DynamicTtt}/ues{6|9|12}/seed{01..10}/`

| 파일 | 내용 |
|---|---|
| `cmd.txt` | 실행 명령, 커밋 해시 |
| `time.txt` | 실제 시간(s), 최대 메모리(kB) |
| `DONE` | 정상 종료 표시 |
| `cu-cp-cell-*.txt`, `cu-up-cell-*.txt`, `du-cell-*.txt` | E2 KPM (100 ms 간격) |
| `UeHandover*.txt`, `EnbHandover*.txt`, `CellIdStats*.txt` | 핸드오버 로그 |
| 기타 `*Stats.txt`, `*Trace.txt` | ns-3 trace |

가져오기(약 50 GB): `rsync -a --info=progress2 <새PC>:~/research/nsoran/ns-o-ran-ns3-mmwave/ns-o-ran-security/results/raw/baseline/ <이PC 경로>/`
또는 `tar` 후 복사.

## 10. 알아둘 점

- **제어 파일이 필요하다.** scenario-one은 `ts_actions_for_ns3.csv`를 항상 열기 때문에 없으면
  exit 250으로 끝난다. 스크립트가 실행 폴더마다 빈 파일을 만든다.
- **KPM 타임스탬프는 실행 시작 시각(실제 시계, ms) 기준이다.** 실행마다 다르므로 분석할 때는
  `시뮬레이션 시간 = timestamp − 첫 timestamp`로 쓴다.
- **gNB의 CU-UP KPM은 비어 있다.** EN-DC 구조라 PDCP가 LTE eNB에 있어, 처리량 KPM은
  `cu-up-cell-1.txt`(LTE)에서 나온다.
- **CU-CP의 "SINR"은 사실 SNR이다.** `mmwave-enb-phy.cc:717`에서 간섭 항이 주석 처리되어 있다.
- **trafficModel 3에서 full-buffer(25%)만 하향 UDP이고, 나머지 75%는 UE에서 보내는 상향 TCP다.**
  논문 서술과 다를 수 있다. 확인 필요 항목.
- 실행 시간은 거의 전부 PHY/MAC/3GPP 채널 계산이다. trace(약 1%)나 E2 로깅은 병목이 아니다.
