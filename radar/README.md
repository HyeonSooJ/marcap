# 마캡레이더 (MarcapRadar)

marcap 일별 시가총액/주가/거래량 데이터를 이용해 상장기업의 이상변동을 조기에
탐지하고, DART 공시·뉴스와 결합한 LLM(Claude)이 원인을 설명해주는 리스크 모니터링
서비스입니다. KODATA·BDAI 공모전 출품작입니다. 자세한 배경과 근거는
[`proposal/제안서.md`](proposal/제안서.md) 참고.

## 구성

```
radar/
├── src/
│   ├── anomaly_detector.py   # 통계 기반 이상탐지 + 백테스트
│   ├── dart_collector.py     # OpenDART 공시 목록 수집
│   ├── news_collector.py     # 네이버 뉴스 검색
│   ├── llm_report.py         # Claude 기반 원인 해설 리포트 생성
│   └── pipeline.py           # 전체 파이프라인 오케스트레이션
├── scripts/
│   └── backtest.py           # 조기경보 성능 백테스트 CLI
├── app.py                    # Streamlit 데모 대시보드
├── proposal/제안서.md         # 공모전 제안서
└── output/                   # 생성된 리포트/백테스트 결과 (reports/*.md, backtest_result.csv)
```

## 설치

```bash
pip install -r radar/requirements.txt
```

## API 키 설정

`radar/.env.example`을 참고해 아래 키를 발급받아 환경변수로 설정하세요. 전부 무료입니다.

| 변수 | 발급처 | 없으면 |
|---|---|---|
| `DART_API_KEY` | https://opendart.fss.or.kr | 공시 정보 없이 진행 |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | https://developers.naver.com/apps | 뉴스 정보 없이 진행 |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | 이상탐지 수치만 표시, LLM 리포트 생략 |

키가 없어도 이상탐지 엔진 자체는 정상 동작합니다(단계적으로 기능이 줄어드는 구조).

```bash
cp radar/.env.example radar/.env
# .env 편집 후
set -a && source radar/.env && set +a
```

## 실행

```bash
# 조기경보 성능 백테스트 (marcap 데이터만으로 실행 가능, API 키 불필요)
python radar/scripts/backtest.py --start 2022-01-01 --end 2026-07-01

# 오늘자 데일리 리포트 생성
python radar/src/pipeline.py

# 대시보드 실행
streamlit run radar/app.py
```

## 검증된 결과

`radar/scripts/backtest.py`로 2022-01-01~2026-07-01 기간의 관리종목/투자주의환기종목
지정 이벤트 482건을 대상으로 백테스트한 결과, 공식 지정 20영업일 전부터의 조기탐지
커버리지는 45.4%, 평균 리드타임은 11.8영업일이었습니다. 재현 가능하며 파라미터
(`--lookback-days`, `--threshold`)를 바꿔 재검증할 수 있습니다.

## 자동화

`.github/workflows/radar_daily.yml`이 기존 marcap 데이터 자동 업데이트 워크플로우
직후 실행되어 매일 데일리 리포트를 생성·커밋합니다. 저장소 Secrets에 위 API 키들을
등록하면 활성화됩니다.
