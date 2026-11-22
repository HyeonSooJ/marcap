# KIS Trader — 주식 매매 웹사이트

한국투자증권 Open API(KIS Developers)를 이용한 국내주식 **현재가 조회 · 매수/매도** 웹사이트입니다.
백엔드는 Python **FastAPI**, 프론트엔드는 **HTML / CSS / JavaScript**(프레임워크 없음)로 만들었습니다.
API 호출 방식은 [koreainvestment/open-trading-api](https://github.com/koreainvestment/open-trading-api) 샘플코드(`kis_auth.py`)의 토큰 발급·헤더 구성을 따릅니다.

## 기능

| 영역 | 기능 | 사용 API (TR_ID) |
|---|---|---|
| 종목 검색 | 종목명/코드 자동완성 (이 저장소의 `data/marcap-*.parquet` 최신일 기준) | - |
| 현재가 | 현재가·등락·시고저·상하한가·거래량·PER/PBR 등, 3초 주기 갱신 | 주식현재가 시세 `FHKST01010100` |
| 호가 | 10단 매도/매수 호가·잔량, 가격 클릭 시 주문가격 자동 입력 | 주식현재가 호가/예상체결 `FHKST01010200` |
| 차트 | 일/주/월/년 캔들 + 거래량 + 이동평균(5/20/60) | 국내주식기간별시세 `FHKST03010100` |
| 매수/매도 | 지정가·시장가·최유리, 즉시체결가 자동입력, 10/25/50/최대 수량, 확인창(생략 가능) | 주식주문(현금) `TTTC0012U`/`TTTC0011U` |
| 미수 매수 | '미수 허용' 체크 시 미수 포함 최대수량까지 현금주문 (증거금 40% 계좌 필요) | 주식주문(현금), 매수가능조회 `max_buy_qty` |
| 신용 (실전 전용) | 신용매수 자기융자(21)/유통융자(23), 신용잔고 상환매도 자기융자(25)/유통융자(27) | 주식주문(신용) `TTTC0052U`/`TTTC0051U`, 신용매수가능조회 `TTTC8909R` |
| 주문가능 | 매수 가능 금액·수량 / 매도 가능 수량 | 매수가능조회 `TTTC8908R` |
| 잔고 | 예수금·평가금액·손익, 보유종목 (클릭하면 매도 화면) | 주식잔고조회 `TTTC8434R` |
| 주문·체결 | 당일 주문 내역, 미체결 **정정/취소** | 주식일별주문체결조회 `TTTC0081R`, 정정취소 `TTTC0013U` |
| 거래량 상위 | 거래량 순위 30 (실전 전용 API, 모의투자에서는 안내 문구 표시) | 거래량순위 `FHPST01710000` |
| 관심종목 | 브라우저(localStorage)에 저장 | - |

모의투자(`KIS_ENV=vps`)에서는 주문·계좌 TR_ID 의 앞 글자 `T` 를 `V` 로 바꿔 호출합니다 (예: `VTTC0012U`).

## 실행 방법

```bash
cd trading_web
pip install -r requirements.txt
cp .env.example .env      # 앱키 / 시크릿 / 계좌번호 입력
uvicorn app.main:app --reload
```

브라우저에서 http://127.0.0.1:8000 접속.

- `.env` 에 키가 없으면 자동으로 **DEMO 모드**(증권사 호출 없이 가상 시세·가상 체결, 시작 예수금 1,000만원)로 실행되어 화면을 바로 확인할 수 있습니다.
- 처음에는 반드시 **모의투자(vps)** 로 테스트하세요. `KIS_ENV=prod` 는 실제 주문이 체결됩니다.
- 접근토큰은 24시간 유효하고 1분에 1회만 발급되므로 `trading_web/.tokens/` 에 캐시해 재사용합니다.
- 모의투자는 초당 2건 호출 제한이 있어 서버에서 호출 간격을 자동 조절합니다.

## 실전투자로 전환

1. KIS Developers 에서 **실전 계좌용** 앱키/앱시크릿을 발급받습니다 (모의투자 키와 다릅니다).
2. Render → kis-trader → Environment 에서 `KIS_ENV=prod`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT`(실전 계좌) 를 바꾸고 저장합니다.
3. 신용주문은 계좌에 신용약정이, 미수 매수는 증거금 40% 계좌 설정이 되어 있어야 합니다.
4. 매도담보대출(매도대금 담보대출)은 주문 API 가 없어 이 사이트에서 지원하지 않습니다 (한국투자 앱에서 신청).

## 속도 관련

- 시세·호가·차트는 동시에 요청하며, 검색 결과에서 고른 종목의 차트는 미리 불러옵니다.
- 주문·정정·취소는 시세 조회 대기열을 건너뛰고 바로 전송됩니다.
- 실전 계좌는 1초, 모의투자는 3초마다 시세를 갱신합니다 (모의투자 초당 2건 제한).
- Render 무료 플랜은 15분 미사용 시 잠들어 첫 접속이 50초 이상 걸립니다. 실전 매매용으로는 유료(Starter) 플랜을 권장합니다.

## 보안 주의

- 앱키·시크릿·접근토큰은 **서버에만** 있고 브라우저로 전달되지 않습니다.
- 이 서버에는 로그인 기능이 없습니다. 기본값처럼 `127.0.0.1` 에서만 열어 두고,
  외부(`--host 0.0.0.0`)에 공개하지 마세요. 접속하는 누구나 주문을 낼 수 있게 됩니다.

## 구조

```
trading_web/
├── app/
│   ├── main.py         # FastAPI 라우트 (/api/...)
│   ├── kis_client.py   # KIS REST 클라이언트 (토큰, 시세, 주문, 잔고)
│   ├── demo_client.py  # API 키 없이 동작하는 가상 시뮬레이터
│   ├── stocks.py       # 종목명 검색 (marcap 데이터)
│   └── config.py       # .env / 환경변수 설정
└── static/
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

## REST 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/status` | 실행 모드, 계좌(마스킹) |
| GET | `/api/stocks/search?q=삼성` | 종목 검색 |
| GET | `/api/quote/{code}` | 현재가 |
| GET | `/api/orderbook/{code}` | 호가 |
| GET | `/api/chart/{code}?period=D` | 기간별 시세 (D/W/M/Y) |
| GET | `/api/ranking/volume` | 거래량 순위 |
| GET | `/api/balance` | 잔고 |
| GET | `/api/buyable/{code}?price=&ord_dvsn=00` | 매수가능 |
| POST | `/api/order` | 주문 `{"side":"buy","code":"005930","qty":1,"price":70000,"ord_dvsn":"00"}` |
| GET | `/api/orders` | 당일 주문·체결 |
| POST | `/api/order/revise` | 정정/취소 `{"org_no":"","order_no":"","action":"cancel"}` |

FastAPI 자동 문서: http://127.0.0.1:8000/docs
