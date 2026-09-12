# 바이낸스 상장 "국가·기업 테마" 자산 정리 (TradFi 무기한 선물)

> **정정 안내**: 이 문서의 최초 버전은 "국가 지수·개별주를 추종하는 코인은
> 바이낸스에 없다"고 서술했으나 이는 **틀린 정보**였습니다. 실제로 바이낸스는
> 2026년 1월부터 **USDT 마진 무기한 선물(Perpetual Futures)** 형태로 미국·한국·
> 중국·일본·대만·유럽 등 각국 주식·ETF 가격을 추종하는 상품을 대거 상장했고,
> 이 문서는 그 내용을 국가별·종목별 레버리지·한국인 거래 가능 여부까지
> 반영해 정리한 것입니다.

## 이 상품의 정체: "코인"이 아니라 "무기한 선물(Perp)"

바이낸스 앱에서 보이는 `SAMSUNGUSDT`, `EWYUSDT`, `KORUUSDT` 같은 티커는
**현물 코인이 아니라 USDT로 증거금을 넣는 파생상품(무기한 선물)**입니다.
정식 명칭은 "Margined TradFi Perpetual Contracts"입니다.

- 기초자산(삼성전자 주가, EWY ETF 가격 등)을 **추종하는 파생상품**이지,
  실제 주식을 보유하는 것이 아닙니다.
- **USDT로 결제**되고, 8시간마다 펀딩비가 정산됩니다.
- 24시간 거래 가능(원 증시가 열려있지 않은 시간에도 거래됨).
- 2026년 1월 TSLA 단일 종목으로 시작해 2026년 9월 초 기준 **약 180개
  TradFi 무기한 선물 계약** + 1,000개 미국 주식·ETF 옵션 상품까지 확장.
  월간 거래대금 4,330억 달러(2026년 8월 기준)에 달하는 급성장 카테고리.
- 레버리지는 상장 초기보다 나중에 상향되는 경우가 많아(예: 20배→50배)
  아래 표의 수치도 계속 바뀔 수 있습니다.

## 바이낸스 앱 목록에서 TradFi(주식) 종목 구분하는 법

Futures "All" 탭은 크립토·TradFi·Pre-IPO가 전부 섞여서 알파벳순으로
나열됩니다. 티커 밑에 작게 표시되는 이름으로 구분하세요.

- **TradFi(주식) 종목**: 밑에 실제 회사명이 뜸 — 예) SAMSUNGUSDT 밑에
  "Samsung Electronics", ZSUSDT 밑에 "Zscaler", ZMUSDT 밑에 "Zoom".
- **일반 크립토 종목**: 밑에 블록체인 프로젝트명이 뜸 — 예) ZRXUSDT 밑에
  "0x", ZILUSDT 밑에 "Zilliqa", ZECUSDT 밑에 "Zcash". 이런 것들은 국가
  주식과 무관한 순수 암호화폐입니다.
- 또는 상단 필터에서 **TradFi** 탭이나 **Pre-IPO** 탭을 누르면 크립토를
  제외하고 주식/ETF/비상장기업 관련 계약만 걸러볼 수 있습니다.

## 한국인 거래 가능 여부의 핵심 규칙

바이낸스는 **한국거래소(KRX)에 원주가 상장된 종목/ETF를 그대로 추종하는
계약**은 한국 IP·한국 신분증 KYC 계정에서 거래하지 못하도록 자체적으로
막아뒀습니다(국내 금융당국 요청이 아니라 바이낸스 자체 판단으로 알려짐).

반면 **미국 뉴욕증시(NYSE)에 상장된 ETF를 기초자산으로 삼는 계약**은,
그 ETF가 한국 관련 종목(코스피)을 추종하더라도 "해외(미국) 상장 파생상품
연계 상품"으로 분류되어 한국인도 거래할 수 있습니다. 대표적으로
`EWYUSDT`(MSCI 한국 ETF, NYSE 상장), `KORUUSDT`(코스피 3배 레버리지 ETF,
NYSE 상장)가 이에 해당합니다.

## 국가·종목별 정리 (레버리지 · 한국인 거래 가능 여부)

### 🇰🇷 한국 — KRX 원주 직접 추종 (한국인 거래 **불가**)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 | 한국인 거래 |
|---|---|---|---|---|
| SAMSUNGUSDT | 삼성전자 | 2026-06-02 | 20배 → 50배로 확대 | ✗ 불가 |
| SKHYNIXUSDT | SK하이닉스 | 2026-06-02 | 20배 → 50배로 확대 | ✗ 불가 |
| HYUNDAIUSDT | 현대자동차 | 2026-06-02 | 20배(50배 확대 여부 미확인) | ✗ 불가 |
| NAVERUSDT | 네이버 | 2026-08-14 | 최대 20배 | ✗ 불가 |
| SAMSUNGEMUSDT | 삼성전기(Samsung Electro-Mechanics) | 미확인 | 미확인 | ✗ 불가 |
| LGELECTRONICSUSDT | LG전자 | 2026-08-14 | 미확인(20배 추정) | ✗ 불가 |
| (한미반도체 계약) | 한미반도체 | 2026-08-14 전후 | 미확인 | ✗ 불가 |
| KODEX200USDT | 삼성 KODEX 200 ETF(코스피200 추종) | 미확인 | 미확인 | ✗ 불가 |

### 🇰🇷 한국 관련이지만 미국(NYSE) 상장 ETF·ADR 경유 (한국인 거래 **가능**)

같은 회사를 추종해도 **KRX 원주 직접 상품은 차단**, **미국 상장 ADR·
레버리지 ETF 경유 상품은 허용**되는 패턴이 SK하이닉스에서도 그대로
확인됩니다.

| 티커 | 기초자산 | 최대 레버리지 | 한국인 거래 |
|---|---|---|---|
| EWYUSDT | iShares MSCI South Korea ETF(EWY, NYSE) | 최대 10배 | ✓ 가능 |
| KORUUSDT | Direxion Daily South Korea Bull 3X ETF(KORU, NYSE) | 20배 → 50배 (ETF 자체 3배와 겹치면 이론상 코스피 등락률의 최대 **150배** 효과) | ✓ 가능 |
| SKHYUSDT | SK Hynix ADR(미국 상장 주식예탁증서) | 미확인 | ✓ 가능 |
| SKUUSDT | GraniteShares 2x Long SK Hynix ETF(2배 레버리지) | 미확인 | ✓ 가능 |
| SKDDUSDT | GraniteShares 2x Short SK Hynix ETF(2배 인버스) | 미확인 | ✓ 가능 |

같은 "SK하이닉스"라도 `SKHYNIXUSDT`(KRX 원주 직접)는 위 표처럼 한국인
차단, `SKHYUSDT`/`SKUUSDT`/`SKDDUSDT`(미국 상장 ADR·레버리지ETF 경유)는
거래 가능— 헷갈리기 쉬우니 주의.

### 🇺🇸 미국 (한국인 거래 가능)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 |
|---|---|---|---|
| TSLAUSDT | 테슬라 | 2026-01-28 (최초 종목) | 자료마다 10~25배로 엇갈림, 재확인 필요 |
| AAPLUSDT / NVDAUSDT / METAUSDT / GOOGLUSDT | 애플/엔비디아/메타/알파벳 | TSLA 이후 순차 상장 | 대체로 10배 |
| MSFTUSDT / AVGOUSDT | 마이크로소프트/브로드컴 | 2026-04-20 | 10배 |
| DDOGUSDT / TEAMUSDT / MDBUSDT / ZSUSDT / GTLBUSDT | Datadog/Atlassian/MongoDB/Zscaler/GitLab | 2026-09-02 | 20배 |
| NVDLUSDT / TSLLUSDT | NVDA 2배 레버리지 ETF / TSLA 2배 레버리지 ETF | 2026-09-02 | 20배 |
| ZMUSDT | 줌(Zoom) | 미확인 | 미확인 (바이낸스 앱 자체가 "Zoom"으로 표시) |
| MRVLUSDT / CRWVUSDT / WMTUSDT / JPMUSDT / VUSDT / BRKBUSDT | 마벨/코어위브/월마트/JP모건/비자/버크셔해서웨이 | 2026-05-15~18 | 미확인 |
| DJTUSDT / MRNAUSDT | 트럼프미디어(Trump Media)/모더나(Moderna) | 2026-08-25 | 미확인 (같은 날 반도체 ETF 3종도 추가) |
| SNDKUSDT | 샌디스크(SanDisk) | 미확인 | 미확인 (나스닥 대비 거래량 비중 20%+로 활발) |
| WENUSDT | 웬디스(Wendy's) | 미확인 | 미확인 |
| WDCUSDT | 웨스턴디지털(Western Digital) | 미확인 | 미확인(타 거래소 기준 10배 사례 있음) |
| SMCIUSDT | 슈퍼마이크로컴퓨터(Super Micro Computer) | 미확인 | 미확인 |
| SOFIUSDT | 소파이(SoFi Technologies, 핀테크) | 미확인 | 미확인 |
| SNOWUSDT | 스노우플레이크(Snowflake) | 미확인 | 미확인 |
| STXXUSDT | 시게이트(Seagate Technology) | 미확인 | 미확인 |
| STRCUSDT | 스트래티지(Strategy Inc, 옛 마이크로스트래티지) Series A 우선주 | 미확인 | 미확인 |
| TERUSDT | 테라다인(Teradyne, 반도체 검사장비) | 미확인 | 미확인 |
| TEMUSDT | 템퍼스AI(Tempus AI) | 미확인 | 미확인 |

**미국 채권 ETF** — 주식이 아니라 국채 가격을 추종하는 상품도 있습니다:

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| TBTUSDT | ProShares UltraShort 20+ Year Treasury(20년 이상 미국 국채 **-2배** 인버스) | 미확인 |
| TMFUSDT | Direxion Daily 20+ Year Treasury Bull 3X(20년 이상 미국 국채 **+3배** 레버리지) | 미확인 |

**미국 지수 추종 ETF** — 개별 종목·섹터가 아니라 시장 전체 지수를 추종
(사용자가 처음 예시로 든 "코루/EWY"와 가장 유사한 성격의 상품):

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| SPYUSDT | State Street SPDR S&P 500 ETF(S&P500 지수) | 미확인 |
| QQQUSDT | Invesco QQQ Trust(나스닥100 지수, 레버리지 없는 기본형) | 미확인 |
| SQQQUSDT | ProShares UltraPro Short QQQ(나스닥100 **-3배** 인버스) | 미확인 |
| TQQQUSDT | ProShares UltraPro QQQ(나스닥100 **+3배** 레버리지) | 미확인 |
| TZAUSDT | Direxion Small Cap Bear 3X(미국 스몰캡 지수 **-3배** 인버스) | 미확인 |
| RAMUSDT | Roundhill T-REX 2X Long 계열(개별 종목 2배 레버리지, 정확한 기초자산 미확인) | 미확인 |

**주의**: `SPXUSDT`는 S&P500과 무관한 밈코인 "SPX6900"입니다. 티커가
비슷해 헷갈리기 쉬우니 진짜 S&P500 상품은 `SPYUSDT`인 점에 유의하세요.
마찬가지로 `TRUMPUSDT`/`TRUMPUSDC`("OFFICIAL TRUMP")도 트럼프미디어
주식(DJTUSDT)과 무관한 별개의 밈코인입니다.

**미국 섹터 ETF** — 개별 종목이 아니라 산업 섹터 전체를 추종:

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| XLEUSDT | Energy Select Sector SPDR Fund(에너지 섹터 ETF) | 미확인 |
| XBIUSDT | SPDR S&P Biotech ETF(바이오테크 섹터 ETF) | 최대 20배 |
| SMHUSDT | VanEck Semiconductor ETF(반도체 섹터 ETF) | 미확인 |
| SOXLUSDT | Direxion Daily Semiconductor Bull 3X(반도체 **3배 롱**) | 미확인 |
| SOXSUSDT | Direxion Daily Semiconductor Bear 3X(반도체 **3배 숏/인버스**) | 미확인 |
| SNXXUSDT | Tradr 2X Long SNDK ETF(샌디스크 2배 롱) | 미확인 |
| MVLLUSDT | GraniteShares 2x Long MRVL Daily ETF(마벨 2배 롱) | 미확인 |
| MUUUSDT | Direxion Daily MU Bull 2X(마이크론 2배 롱) | 미확인 |
| URNMUSDT | Sprott Uranium Miners ETF(우라늄 채굴 섹터 ETF) | 미확인 |
| LYTEUSDT | Roundhill Photonics & Optics ETF(광학·포토닉스 섹터 ETF) | 미확인 |

**미국 변동성(VIX) ETF**:

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| UVXYUSDT | ProShares Ultra VIX Short-Term Futures ETF(VIX 변동성지수 레버리지) | 미확인 |

**미국 개별주 추가**:

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| UBERUSDT | 우버(Uber Technologies) | 미확인 |
| TTWOUSDT | 테이크투 인터랙티브(Take-Two Interactive, GTA 제작사) | 미확인 |
| TXNUSDT | 텍사스 인스트루먼트(Texas Instruments, 반도체) | 미확인 |
| VSTUSDT | 비스트라(Vistra Corp., 발전·에너지) | 미확인 |
| VRTUSDT | 버티브(Vertiv Holdings, 데이터센터 인프라) | 미확인 |
| USARUSDT | USA Rare Earth(희토류 채굴) | 미확인(회사명 표시 기준, 재확인 권장) |
| PANWUSDT | 팔로알토 네트웍스(Palo Alto Networks, 보안) | 미확인 |
| ORCLUSDT | 오라클(Oracle) | 미확인 |
| PENGUSDT | 펭귄솔루션즈(Penguin Solutions) | 미확인 |
| PLTRUSDT | 팔란티어(Palantir Technologies) | 미확인 |
| PYPLUSDT | 페이팔(PayPal) | 미확인 |
| QCOMUSDT | 퀄컴(Qualcomm) | 미확인 |
| RDDTUSDT | 레딧(Reddit) | 미확인 |
| RKLBUSDT | 로켓랩(Rocket Lab) | 미확인 |
| RIVNUSDT | 리비안(Rivian Automotive) | 미확인 |
| KLACUSDT | KLA(반도체 장비) | 미확인 |
| KOUSDT | 코카콜라(Coca-Cola) | 미확인 |
| LLYUSDT | 일라이릴리(Eli Lilly, 제약) | 미확인 |
| LITEUSDT | 루멘텀(Lumentum, 광학부품) | 미확인 |
| LRCXUSDT | 램리서치(Lam Research, 반도체 장비) | 미확인 |
| MARAUSDT | 마라홀딩스(MARA Holdings, 비트코인 채굴) | 미확인 |
| MRKUSDT | 머크(Merck & Co., 제약) | 미확인 |
| MSTRUSDT | 스트래티지(Strategy Inc, 옛 마이크로스트래티지) 보통주 | 미확인 |
| MUUSDT | 마이크론(Micron Technology, 메모리반도체) | 미확인 |
| NFLXUSDT | 넷플릭스(Netflix) | 미확인 |
| NETUSDT | 클라우드플레어(Cloudflare) | 미확인 |
| NOWUSDT | 서비스나우(ServiceNow) | 미확인 |
| ONDSUSDT | 온다스홀딩스(Ondas Holdings, 드론) | 미확인(회사명 표시 기준, 재확인 권장) |

**주의**: `PAXGUSDT`("PAX Gold")는 XAUUSDT(금 선물)와 다른 **크립토
토큰**입니다. 금 1온스를 담보로 발행된 스테이블코인형 토큰이라, XAUT와
같은 종류의 상품이니 혼동하지 마세요. 마찬가지로 `ONDOUSDT`("Ondo")는
위 `ONDSUSDT`(Ondas)와 전혀 다른 **크립토** 프로젝트(RWA 토큰화
플랫폼)이니 혼동하지 마세요.

### 🇨🇦 캐나다 (한국인 거래 가능)

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| SHOPUSDT | 쇼피파이(Shopify, 캐나다 이커머스 기업) | 미확인 |

이 외에도 180개 계약 중 대다수가 미국 개별주·ETF라 전부 나열하기는
어렵습니다. 한국인 계정에 대한 별도 차단 보도는 없습니다.

### 🇨🇳 중국 / 홍콩 상장 (한국인 거래 가능)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 |
|---|---|---|---|
| BABAUSDT | 알리바바 | 2026-04-20 | 10배 |
| TENCENTUSDT | 텐센트 | 2026-07-17 | 미확인 |
| MEITUANUSDT | 메이투안 | 미확인 | 미확인 |
| XIAOMIUSDT | 샤오미 | 미확인 | 미확인 |
| KUAISHOUUSDT | 콰이쇼우 | 미확인 | 미확인 |
| POPMARTUSDT | 팝마트 | 미확인 | 미확인 |
| ZHONGJIUSDT | 중제쉬촹(ZhongJi Innolight, 中際旭創, 광모듈 제조사) | 미확인 | 20배 |
| ZHIPUUSDT | 즈푸AI(Zhipu AI) 기업가치 | 2026-07-17 | Pre-IPO 계열 상품 특성상 10배 추정, 정확한 수치 미확인 |
| UNITREEUSDT | 유니트리(Unitree Technology, 로봇 제조사) 기업가치 | 미확인 | Pre-IPO 계열 추정, 미확인 |
| PDDUSDT | PDD Holdings(핀둬둬·테무 모기업, 나스닥 상장) | 미확인 | 미확인 |
| KSTRUSDT | KraneShares STAR Market 50 ETF(상하이 커촹반 지수) | 미확인 | 미확인 |

### 🇯🇵 일본 (한국인 거래 가능)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 |
|---|---|---|---|
| SONYUSDT | 소니 | 2026-06-22 | 20배 |
| PAYPUSDT | 페이페이(PayPay, 소프트뱅크·야후재팬 계열 핀테크) | 미확인 | 미확인 |

일본 관련 종목이 더 있을 가능성이 있으나 이번 조사에서는 위 2개만 확인.

### 🇹🇼 대만 (한국인 거래 가능)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 |
|---|---|---|---|
| TSMUSDT | TSMC(대만반도체) | 2026-04-06 | 10배 |

### 🇳🇱 네덜란드 (한국인 거래 가능, 세부 미확인)

- ASML(유럽 최대 반도체 장비사) 관련 계약이 존재한다는 언급은 있으나
  정확한 티커명·상장일·레버리지는 이번 조사에서 확정하지 못함.
- NBISUSDT("Nebius", 옛 얀덱스(Yandex) 계열 AI클라우드 기업, 나스닥
  상장)도 회사명 표시로 볼 때 TradFi로 추정되나 국가·레버리지 재확인 필요.

### 🇫🇮 핀란드 (한국인 거래 가능)

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| NOKUSDT | 노키아(Nokia) | 미확인 |

### 🇩🇰 덴마크 (한국인 거래 가능)

| 티커 | 기초자산 | 최대 레버리지 |
|---|---|---|
| NVOUSDT | 노보노디스크(Novo Nordisk, 제약) | 미확인 |

### 🪙 원자재 (한국인 거래 가능)

| 티커 | 기초자산 | 상장일 | 최대 레버리지 |
|---|---|---|---|
| XAUUSDT | 금(Gold) | 2026-01-05 | 최대 50배 |
| XAGUSDT | 은(Silver) | 2026-01-07 | 최대 50배 |
| XPTUSDT | 백금(Platinum) | 2026-01-30 | 최대 100배 |
| XPDUSDT | 팔라듐(Palladium) | 2026-01-30 | 최대 100배 |
| NATGASUSDT | 천연가스(Natural Gas) | 미확인 | 미확인 |

이 넷이 TradFi 무기한 선물 카테고리의 최초 상품군이며, 국가·기업 테마는
아니지만 같은 상품군이라 참고로 기재.

**주의**: `XAUTUSDT`(밑에 "Tether Gold"로 표시)는 별개의 **크립토 토큰**
입니다. 테더가 발행한 금 1온스 담보 스테이블코인형 토큰이지, 바이낸스의
TradFi 금 선물(XAUUSDT)과는 다른 상품이니 혼동하지 마세요.

### ⚽ 참고: 팬토큰(별개 상품군)

목록 중 `SANTOSUSDT`("Santos FC Fan Token")처럼 스포츠 구단 팬토큰이
섞여 나올 때가 있습니다. 이는 Chiliz/Socios 계열의 **팬토큰**으로 이
문서가 다루는 TradFi 무기한 선물과는 완전히 다른 상품군입니다(브라질
구단 산투스 FC 팬토큰). 국가 연관성은 있지만 주가·지수를 추종하진
않으므로 레버리지 개념 자체가 다릅니다.

### 비상장 기업 (Pre-IPO 프록시, 한국인 거래 가능 추정)

- SpaceX(미국, `SPCXUSDT`/`SPCXUSD1`) — 상장 전 기업가치에 노출되는 계약.
  2026년 7월 출시, USD1 스테이블코인으로 결제하는 버전도 있음. 레버리지
  미확인.
- OpenAI(미국) — 2026-05-26 출시, Pre-IPO Perpetual Contracts 계열
  두 번째 상품. 레버리지 미확인.
- 즈푸AI(중국, ZHIPUUSDT) — 위 중국 표 참고.

## 요약: 국가별 한 줄 정리

| 국가 | 대표 종목(바이낸스 티커) | 한국인 거래 가능? |
|---|---|---|
| 한국(KRX 원주) | SAMSUNGUSDT, SKHYNIXUSDT, HYUNDAIUSDT, NAVERUSDT, SAMSUNGEMUSDT 등 | ✗ 불가 |
| 한국(미국 상장 ETF·ADR 경유) | EWYUSDT, KORUUSDT, SKHYUSDT, SKUUSDT, SKDDUSDT | ✓ 가능 |
| 미국 | TSLAUSDT, AAPLUSDT, NVDAUSDT, SMCIUSDT 등 다수 | ✓ 가능 |
| 미국(지수 전체) | SPYUSDT(S&P500), SQQQUSDT(나스닥100 인버스) | ✓ 가능 |
| 미국(국채) | TBTUSDT(20년+ 국채 인버스) | ✓ 가능 |
| 캐나다 | SHOPUSDT(쇼피파이) | ✓ 가능 |
| 중국 | BABAUSDT, TENCENTUSDT, XIAOMIUSDT 등 | ✓ 가능 |
| 일본 | SONYUSDT, PAYPUSDT | ✓ 가능 |
| 대만 | TSMUSDT | ✓ 가능 |
| 네덜란드 | ASML 관련(세부 미확인), NBISUSDT(추정) | ✓ 가능(추정) |
| 핀란드 | NOKUSDT(노키아) | ✓ 가능 |
| 덴마크 | NVOUSDT(노보노디스크) | ✓ 가능 |
| 원자재 | XAU/XAG/XPT/XPD/NATGAS(금·은·백금·팔라듐·천연가스) | ✓ 가능 |

## 유의사항 (반드시 읽어주세요)

1. **파생상품이지 실물 코인/주식이 아닙니다.** 레버리지가 걸려 있어
   가격이 반대로 움직이면 원금 이상 손실(청산)이 발생할 수 있습니다.
   특히 KORUUSDT처럼 "3배 레버리지 ETF + 바이낸스 자체 레버리지"가
   중첩되는 상품은 변동성이 극단적으로 커집니다.
2. **한국 거주자는 KRX 원주를 직접 추종하는 상품(삼성전자·SK하이닉스·
   현대차·네이버 등)을 이용할 수 없습니다.** 반면 미국 상장 ETF를 경유하는
   EWYUSDT·KORUUSDT는 규제 사각지대에 있어 한국인도 거래 가능한 상태이며,
   이 때문에 "150배 코스피 레버리지" 논란과 국내 금융당국의 규제 공백
   지적이 이어지고 있습니다.
3. 표의 레버리지 수치는 상장 이후 상향 조정되는 경우가 많고, "미확인"으로
   표시한 항목은 이번 조사에서 확실한 근거를 찾지 못한 것입니다. 실제
   거래 전 바이낸스 앱/공식 공지("Margined TradFi Perpetual Contracts"
   시리즈)에서 최신 수치를 반드시 재확인하세요.
4. 이 문서는 정보 정리 목적이며 투자 조언이 아닙니다.
