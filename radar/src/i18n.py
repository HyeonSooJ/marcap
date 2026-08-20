# -*- coding: utf-8 -*-
"""app.py용 UI 문구 번역 테이블 ('ko'/'en'). 화면 문구만 다루고, 개인화 관련 문구
(설문/성향 설명/LLM 프롬프트)는 investor_profile.py·llm_report.py가 각자의 lang
파라미터로 처리한다 — 중복 없이 관심사를 분리하기 위함.

Dept(소속부) 컬럼의 실제 값(관리종목, 벤처기업부 등)은 KRX가 정한 공식 분류
문자열이라 여기서 번역하지 않는다(전체 변형을 다 알 수 없어 임의 번역 시
오히려 부정확할 위험). 컬럼 헤더만 번역하고 셀 값은 원문 그대로 둔다.
"""

TRANSLATIONS = {
    'page_title': {'ko': '마캡레이더', 'en': 'MarcapRadar'},
    'title': {
        'ko': '📡 마캡레이더 — 상장기업 이상변동 조기경보',
        'en': '📡 MarcapRadar — Early Warning for Listed-Company Anomalies',
    },
    'top_caption': {
        'ko': (
            'marcap 일별 시가총액/주가/거래량 데이터를 통계적으로 스캔해 이상신호를 잡아내고, '
            '실제 관리종목·투자주의환기종목 지정 이력과 대조해 조기경보 성능을 검증합니다.'
        ),
        'en': (
            'Statistically scans marcap daily market-cap/price/volume data to catch anomaly '
            'signals, and validates early-warning performance against real KRX risk-designation '
            '(administrative issue / investment-alert) history.'
        ),
    },
    'tab1_name': {'ko': '오늘의 이상신호', 'en': "Today's Anomalies"},
    'tab2_name': {'ko': '데일리 리포트', 'en': 'Daily Report'},
    'tab3_name': {'ko': '백테스트 결과', 'en': 'Backtest Results'},
    'tab4_name': {'ko': '밈스탁 확산 진단 + 맞춤 경고', 'en': 'Meme-Stock Diffusion Diagnosis + Personalized Alert'},

    'tab1_explain': {
        'ko': (
            '**롤링 윈도우**: "오늘 값이 평소와 다른가"를 판단할 때 기준으로 삼는 과거 기간이에요. '
            '예를 들어 90일이면, 최근 90일간의 흐름과 비교해서 오늘 값이 튀는지를 봅니다. '
            '아래 조회 기간의 시작~종료 날짜 사이가 이 기간이 됩니다.  \n'
            '**이상신호 임계값(z-score)**: 오늘 값이 평소 흐름에서 표준편차 몇 배만큼 벗어났는지를 '
            '나타내는 기준선이에요. 값이 클수록(예: 5.0) 아주 극단적인 경우만 잡아내고, '
            '작을수록(예: 2.0) 더 많이 잡히지만 평범한 변동까지 오탐할 위험이 커집니다.'
        ),
        'en': (
            '**Rolling window**: the past period used as the baseline for "is today unusual?". '
            'E.g. 90 days means today is compared against the trend of the last 90 days. '
            "This is exactly the span between the start and end dates you pick below.  \n"
            '**Anomaly threshold (z-score)**: how many standard deviations today\'s value must '
            'deviate from the recent baseline to count as "unusual." A higher value (e.g. 5.0) '
            'flags only extreme cases; a lower value (e.g. 2.0) flags more, but risks false '
            'positives from ordinary fluctuations.'
        ),
    },
    'date_range_label': {'ko': '조회 기간 (시작일 ~ 기준일)', 'en': 'Date range (start ~ reference date)'},
    'date_range_help': {
        'ko': '끝 날짜가 분석 기준일이 되고, 시작~끝 날짜 사이 데이터로 "평소" 흐름(롤링 윈도우)을 계산합니다.',
        'en': 'The end date is treated as "today." Data between start and end forms the rolling-window baseline.',
    },
    'threshold_label': {'ko': '이상신호 임계값(z-score)', 'en': 'Anomaly threshold (z-score)'},
    'threshold_help': {
        'ko': '표준편차 몇 배만큼 벗어나야 "이상신호"로 볼지 정하는 값. 기본 3.0 = 통계적으로 1000번 중 1~3번 정도만 일어나는 수준.',
        'en': 'How many standard deviations away counts as "unusual." Default 3.0 = statistically happens only 1-3 times in 1000.',
    },
    'top_n_label': {'ko': '표시 종목 수', 'en': 'Number of stocks to show'},
    'scan_button': {'ko': '스캔 실행', 'en': 'Run scan'},
    'need_both_dates': {'ko': '시작일과 종료일을 모두 선택해주세요.', 'en': 'Please select both a start and an end date.'},
    'loading_scan': {'ko': 'marcap 데이터 로딩 및 이상탐지 실행 중...', 'en': 'Loading marcap data and running anomaly detection...'},
    'no_data': {'ko': '불러올 데이터가 없습니다.', 'en': 'No data available for this range.'},
    'scan_success': {'ko': '{date} 기준 {n}개 종목 플래그', 'en': '{n} stocks flagged as of {date}'},
    'date_col': {'ko': '날짜', 'en': 'Date'},

    'tab2_no_report': {
        'ko': '아직 생성된 리포트가 없습니다. `python radar/src/pipeline.py` 를 먼저 실행하세요.',
        'en': 'No report generated yet. Run `python radar/src/pipeline.py` first.',
    },
    'tab2_select_date': {'ko': '날짜 선택', 'en': 'Select date'},
    'tab2_lang_note': {
        'ko': '',
        'en': 'Note: reports are generated offline in Korean regardless of this language toggle.',
    },

    'tab3_no_backtest': {
        'ko': '백테스트 결과가 없습니다. `python radar/scripts/backtest.py` 를 먼저 실행하세요.',
        'en': 'No backtest results yet. Run `python radar/scripts/backtest.py` first.',
    },
    'tab3_metric_events': {'ko': '위험지정 이벤트 수', 'en': 'Risk-designation events'},
    'tab3_metric_coverage': {'ko': '조기탐지 커버리지', 'en': 'Early-detection coverage'},
    'tab3_metric_lead': {'ko': '평균 리드타임', 'en': 'Avg. lead time'},
    'tab3_unit_events': {'ko': '건', 'en': ''},
    'tab3_unit_lead': {'ko': '영업일', 'en': 'trading days'},

    'tab4_subheader': {'ko': '밈스탁 버블 확산 진단 + 맞춤 경고', 'en': 'Meme-Stock Bubble Diffusion Diagnosis + Personalized Alert'},
    'tab4_caption': {
        'ko': (
            '1차로 이상탐지를 통과한 종목에 한해, 감염병 확산모델(SIR)의 실효재생산수(Rt) 개념을 '
            '시장 관심(거래대금 회전율 + 검색량) 확산에 적용해 지금 어느 단계인지 진단합니다. '
            '재무·신용 지표가 아니라 "정보 확산의 속도"로 보는 보조 지표이며, 투자 성향 설문과 '
            '결합해 개인화된 주의 메시지를 만듭니다. 특정 종목의 매수·매도를 추천하지 않습니다.'
        ),
        'en': (
            'For stocks that pass initial anomaly screening only, applies the effective '
            'reproduction number (Rt) from an epidemic diffusion model (SIR) to market '
            'attention (turnover ratio + search volume) to diagnose the current diffusion stage. '
            'A supplementary indicator based on "speed of information diffusion," not financial or '
            'credit metrics — combined with an investor-profile survey to produce a personalized '
            'caution message. Does not recommend buying or selling any specific stock.'
        ),
    },
    'tab4_explain': {
        'ko': (
            '**조회 기간**: 시작~종료 날짜 사이 데이터를 "평소" 흐름 비교 기준으로 삼습니다. '
            '기간이 너무 짧으면 비교 기준이 부족해 진단이 불안정해질 수 있어요.  \n'
            '**1차 이상신호 임계값(z-score)**: "오늘의 이상신호" 탭과 같은 개념이에요 — 이 값을 넘는 '
            '종목만 2단계 확산 진단(검색량 API 호출)까지 진행해서 비용과 오탐을 줄입니다.'
        ),
        'en': (
            '**Date range**: data between start and end forms the "normal" baseline for comparison. '
            'Too short a range gives an unstable baseline.  \n'
            '**Initial anomaly threshold (z-score)**: same concept as in the "Today\'s Anomalies" tab — '
            'only stocks above this value proceed to stage-2 diffusion diagnosis (which calls the '
            'search-volume API), to control cost and false positives.'
        ),
    },
    'diff_date_range_help': {
        'ko': '끝 날짜가 분석 기준일이 됩니다. 검색량/뉴스 데이터도 이 기간에 맞춰 조회됩니다.',
        'en': 'The end date is treated as "today." Search-volume and news data are also fetched for this range.',
    },
    'diff_threshold_help': {
        'ko': '표준편차 몇 배만큼 벗어나야 1차 스크리닝을 통과시킬지 정하는 값 (기본 3.0).',
        'en': 'How many standard deviations away are needed to pass initial screening (default 3.0).',
    },
    'diff_scan_button': {'ko': '확산 진단 스캔 실행', 'en': 'Run diffusion diagnosis scan'},
    'diff_loading': {
        'ko': 'marcap 데이터 로딩 + 이상탐지 + 확산 진단 실행 중 (검색량 API 호출 포함, 다소 시간이 걸릴 수 있습니다)...',
        'en': 'Loading marcap data + running anomaly detection + diffusion diagnosis '
              '(includes search-volume API calls, may take a while)...',
    },
    'diff_waiting': {'ko': '스캔을 실행하면 결과가 여기 표시됩니다.', 'en': 'Results will appear here after you run a scan.'},
    'diff_none_flagged': {'ko': '이상신호로 플래그된 종목이 없습니다.', 'en': 'No stocks were flagged as anomalies.'},
    'diff_none_diagnosable': {
        'ko': '확산 단계를 진단할 수 있는 종목이 없습니다 (검색량 데이터 부족 등으로 Rt 산출 불가).',
        'en': 'No stocks could be diffusion-diagnosed (e.g. insufficient search-volume data to estimate Rt).',
    },
    'alert_section_header': {'ko': '#### 맞춤 경고 메시지 생성', 'en': '#### Generate Personalized Alert'},
    'pick_stock_label': {'ko': '종목 선택', 'en': 'Select a stock'},
    'survey_header': {'ko': '**투자 성향 설문 (5문항)**', 'en': '**Investor Profile Survey (5 questions)**'},
    'generate_alert_button': {'ko': '맞춤 경고 생성', 'en': 'Generate personalized alert'},
    'your_profile': {'ko': '당신의 투자 성향: **{profile}** (점수: {scores})', 'en': 'Your investor profile: **{profile}** (scores: {scores})'},
    'llm_call_failed': {
        'ko': 'LLM 호출 실패, 규칙 기반 메시지로 대체합니다: {error}',
        'en': 'LLM call failed, falling back to a rule-based message: {error}',
    },

    'lang_popover_label': {'ko': '🌐', 'en': '🌐'},
    'lang_picker_label': {'ko': '언어 / Language', 'en': 'Language / 언어'},

    'tab5_name': {'ko': '차트 모양 조건검색', 'en': 'Chart Shape Screener'},
    'tab5_subheader': {'ko': '📐 차트 모양 조건검색', 'en': '📐 Chart Shape Screener'},
    'tab5_explain': {
        'ko': (
            '기준일과 조회 개월 수를 고르면 그 기간 동안의 종가 흐름을 3가지 차트 모양(①우상향 '
            '②박스권 V자 반등 ③V자 반등 후 상승돌파)과 비교해, 선택한 모양과 가장 비슷하게 움직인 '
            '국내 보통주(우선주·스팩·리츠·코넥스 제외, 기준일 시가총액 상위 2,000 종목 이내)를 '
            '찾아줍니다. ④거래정지 종목은 모양 비교 대신, 기준일 현재 거래정지 중인 종목을 그대로 '
            '찾아줍니다. 업종/PER은 KRX(pykrx)에서 별도로 조회하며, 조회에 실패하면 해당 칸이 '
            '비어있을 수 있습니다.  \n'
            '⑤급등 전조 패턴형과 ⑥상한가 지속형은 "급등주 찾기" 관련 세부 조건들을 성격별로 묶은 '
            '메뉴입니다. ⑤는 아직 상한가가 확정되지 않은 종목 중 횡보 후 급등형·바닥 찍고 연속 '
            '반등형·급등 후 눌림목형 모양에 가까운 후보를, ⑥은 이미 상한가를 기록한 종목 중 오늘 '
            '상한가+모양 필터·상한가 후 거래량 지속형 조건으로 다음 상한가로 이어질 가능성이 상대적 '
            '으로 높은 후보를 찾습니다. 어떤 세부 조건에 걸렸는지는 결과 표의 "매칭된 세부 유형" '
            '칼럼에서 확인할 수 있고, 각각 실제 백테스트 검증 결과에 따른 별도 설명·경고 문구가 '
            '있습니다.'
        ),
        'en': (
            "Pick an end date and a lookback period, and this compares each stock's closing-price "
            'movement over that period against 3 chart shapes (① uptrend ② range-bound V-shape '
            'rebound ③ V-shape rebound + breakout) to find domestic common stocks (excluding '
            'preferred shares, SPACs, REITs, KONEX; limited to the top 2,000 by market cap as of the '
            'end date) that moved most like the shape you picked. ④ Trading-halted Stocks skips '
            'shape matching and instead lists stocks currently halted as of the end date. Sector/PER '
            'are fetched separately from KRX (pykrx); those cells may be blank if that lookup fails.  \n'
            '⑤ Pre-surge Pattern and ⑥ Limit-Up Continuation group several "find surging stocks" '
            'sub-conditions by character. ⑤ looks for stocks that have not yet hit the daily limit '
            'but resemble Sideways-then-Breakout, Bottom-then-Rebound, or Rally-then-Pullback. ⑥ '
            'looks for stocks that already hit the daily limit and are relatively more likely to hit '
            'it again, via the Today Limit-Up + Shape Filter and Sustained Volume After Limit-Up '
            'conditions. The "Matched Sub-type" column in the results shows which sub-condition '
            'matched, and each has its own caption/warning based on actual backtest results.'
        ),
    },
    'tab5_end_date_label': {'ko': '① 기준일(종료일) 선택', 'en': '① Pick end date'},
    'tab5_months_label': {'ko': '② 조회 개월 수', 'en': '② Lookback (months)'},
    'tab5_pattern_label': {'ko': '③ 차트 모양 선택', 'en': '③ Pick chart shape'},
    'tab5_confirm_button': {'ko': '④ 확인 — 종목 찾기', 'en': '④ Confirm — Find stocks'},
    'tab5_loading': {'ko': '조건에 맞는 종목을 찾는 중...', 'en': 'Searching for matching stocks...'},
    'tab5_no_data': {'ko': '해당 기간에 데이터가 없습니다.', 'en': 'No data for that period.'},
    'tab5_no_match': {'ko': '조건에 맞는 종목을 찾지 못했습니다.', 'en': 'No matching stocks found.'},
    'tab5_result_caption': {
        'ko': '{start} ~ {end} 기간, {n}개 종목 매칭',
        'en': '{start} ~ {end}, {n} stocks matched',
    },
    'tab5_price_col': {'ko': '현재가', 'en': 'Price'},
    'tab5_chart_col': {'ko': '실시간 차트', 'en': 'Live Chart'},
    'tab5_chart_link_text': {'ko': '📈 네이버에서 보기(실시간)', 'en': '📈 Open on Naver (live)'},
    'tab5_chart_viewer_header': {
        'ko': '#### 📊 조회 기간 기준 차트',
        'en': '#### 📊 Chart for the Queried Period',
    },
    'tab5_chart_pick_label': {'ko': '종목 선택', 'en': 'Select a stock'},
    'tab5_chart_viewer_caption': {
        'ko': '{start} ~ {end} 기간의 종가만 표시합니다 (오늘 날짜 데이터 아님, 위 실시간 차트 링크와는 다릅니다).',
        'en': 'Shows closing prices only for {start} ~ {end} (not today — different from the live chart link above).',
    },
    'tab5_halt_note': {
        'ko': (
            '④ 거래정지 종목은 조회 종료일 기준 거래정지 중인 종목입니다. 현재가는 정지 직전 '
            '마지막 체결가로 고정된 값이고, 정지 시작일이 조회 시작일과 같다면 실제로는 그보다 '
            '더 이전부터 정지 중이었을 수 있습니다(조회 범위 밖이라 정확한 시작일을 알 수 없음).'
        ),
        'en': (
            '④ Trading-halted Stocks lists stocks currently halted as of the end date. Price is '
            'frozen at the last trade before the halt. If the halt start date equals the query '
            'start date, the halt may actually have begun earlier — outside the queried range.'
        ),
    },
    'tab5_today_momentum_empty': {
        'ko': '선택하신 날짜(최근 2개월 기준) 안에 상한가를 기록한 종목이 없어서 결과가 없습니다. 다른 날짜로 다시 시도해보세요.',
        'en': 'No stocks hit the daily limit within the fixed 2-month window ending on the selected date, so there are no results. Try a different date.',
    },
    'tab5_presurge_note': {
        'ko': (
            '⑤ 급등 전조 패턴형은 세 가지 하위 조건(횡보 후 급등형·바닥 찍고 연속 반등형·급등 후 '
            '눌림목형)을 합쳐서 보여줍니다. "매칭된 세부 유형" 칼럼에서 어떤 조건에 걸렸는지 확인할 '
            '수 있고, 한 종목이 여러 조건에 동시에 해당하면 그중 하나만 표시됩니다. 아직 상한가가 '
            '확정되지 않은 종목 중 모양만으로 후보를 추정하는 용도입니다.'
        ),
        'en': (
            '⑤ Pre-surge Pattern combines three sub-conditions (Sideways-then-Breakout, '
            'Bottom-then-Rebound, Rally-then-Pullback). The "Matched Sub-type" column shows which '
            'condition matched; if a stock matches more than one, only one is shown. This is for '
            'stocks that have not yet hit the daily limit — candidates estimated from chart shape '
            'alone.'
        ),
    },
    'tab5_presurge_disclaimer': {
        'ko': (
            '⚠️ 세 조건 모두 2026년 데이터 워크포워드 백테스트로 검증했지만 결과가 엇갈립니다. '
            '**횡보 후 급등형**은 다음날 상한가 확률이 0.6%로 사실상 예측 불가능했고, 한 달 내로 '
            '넓히면 약 10%(무작위 5.2%)였습니다. **바닥 찍고 연속 반등형**은 다음날~한 달 내 상한가 '
            '확률이 23.1%로 무작위(2.7%) 대비 높았지만, 정작 매수 후 1개월 보유 수익률은 -17.0%로 '
            '무작위(-8.2%)보다 나빴습니다. **급등 후 눌림목형**은 1개월 보유 수익률이 -13.2%로 '
            '무작위(-15.7%)보다 근소하게 나은 수준에 그쳤습니다. 셋 다 상한가를 보장하지 않으며 '
            '특히 "매수 후 장기 보유"에는 적합하지 않으니 참고용으로만 활용하세요.'
        ),
        'en': (
            '⚠️ All three conditions were walk-forward backtested on 2026 data, with mixed results. '
            '**Sideways-then-Breakout**: next-day limit-up probability was 0.6% (essentially '
            'unpredictable), rising to ~10% within a month (vs. 5.2% random). '
            '**Bottom-then-Rebound**: next-day-to-1-month limit-up probability was 23.1% (vs. 2.7% '
            'random), but the average 1-month return after buying was -17.0%, worse than random '
            '(-8.2%). **Rally-then-Pullback**: average 1-month return was -13.2%, only marginally '
            'better than random (-15.7%). None of the three guarantees a limit-up, and none is '
            'suited for buy-and-hold — reference only.'
        ),
    },
    'tab5_limitup_continuation_note': {
        'ko': (
            '⑥ 상한가 지속형은 두 가지 하위 조건(오늘 상한가+모양 필터·상한가 후 거래량 지속형)을 '
            '합쳐서 보여줍니다. 둘 다 "이미 상한가를 기록한 종목 중 다음 상한가로 이어질 가능성이 '
            '상대적으로 높은 것"을 찾는 용도라, 최근 상한가 종목이 없으면 결과가 비어있을 수 '
            '있습니다. ②개월수 선택과 무관하게 항상 최근 2개월 흐름으로 계산합니다(검증된 조건과 '
            '동일하게 맞추기 위함).'
        ),
        'en': (
            '⑥ Limit-Up Continuation combines two sub-conditions (Today Limit-Up + Shape Filter, '
            'Sustained Volume After Limit-Up). Both look for stocks that already hit the daily limit '
            'and are relatively more likely to hit it again — an empty result is expected if no '
            'stock hit the limit recently. This always uses a fixed 2-month lookback regardless of '
            'the ② months selector, to match the validated backtest conditions exactly.'
        ),
    },
    'tab5_limitup_continuation_disclaimer': {
        'ko': (
            '⚠️ "확률이 더 높다"는 뜻이지 보장이 아닙니다. **오늘 상한가+모양 필터**는 실제 상한가 '
            '647건 검증 결과 다음날도 상한가 갈 확률이 평균 16.7%였고, 최근 2개월 흐름이 특정 모양과 '
            '상관계수 0.5~0.6 이상이면 20.0~23.8%까지 올라갔습니다(여전히 대부분은 이어지지 않음). '
            '**상한가 후 거래량 지속형**은 실제 상한가 846건 검증 결과 상한가 3일 뒤 거래량이 1.5배 '
            '이상 유지되면 2~7일 내 재상한가 확률이 31.7%로 전체 평균(17.4%)의 약 1.8배였습니다. '
            '두 조건 모두 투자 조언이 아닌 참고 자료입니다.'
        ),
        'en': (
            '⚠️ This means "higher probability," not a guarantee. **Today Limit-Up + Shape Filter**: '
            'validated on 647 real limit-up events, the average next-day continuation rate was '
            '16.7%, rising to 20.0-23.8% when the recent 2-month trend correlated ≥0.5-0.6 with a '
            'specific shape (most cases still do not continue). **Sustained Volume After Limit-Up**: '
            'validated on 846 real limit-up events, stocks whose volume stayed ≥1.5x 3 days after '
            'the limit-up had a 31.7% chance of hitting the limit again within 2-7 days, about 1.8x '
            'the overall average (17.4%). Both are reference only, not investment advice.'
        ),
    },
    'tab5_sector_fail': {
        'ko': '업종/PER 조회에 실패했습니다 (KRX 접속 불가 등). 종목/현재가/시가총액만 표시합니다: {error}',
        'en': 'Sector/PER lookup failed (e.g. KRX unreachable). Showing name/price/market cap only: {error}',
    },
}

REASON_LABELS = {
    'VolumeZ': {'ko': '거래량 급변', 'en': 'Volume Spike'},
    'ChangesRatioZ': {'ko': '등락률 급변', 'en': 'Price Change Spike'},
    'MarcapReturnZ': {'ko': '시가총액 급변', 'en': 'Market Cap Change Spike'},
    'RankChangeZ': {'ko': '시총순위 급변', 'en': 'Cap Rank Change Spike'},
}


def reason_label(val, lang):
    """AnomalyReason 컬럼 값(VolumeZ 등)을 표시용 라벨로 바꾼다 (매핑에 없으면 원래 값 유지)."""
    return REASON_LABELS.get(val, {}).get(lang, val)


COLUMN_LABELS = {
    'Code': {'ko': '종목코드', 'en': 'Code'},
    'Name': {'ko': '종목명', 'en': 'Name'},
    'Close': {'ko': '종가', 'en': 'Close'},
    'ChangesRatio': {'ko': '등락률(%)', 'en': 'Change (%)'},
    'Volume': {'ko': '거래량', 'en': 'Volume'},
    'Rank': {'ko': '시총순위', 'en': 'Cap Rank'},
    'Dept': {'ko': '소속부', 'en': 'Segment'},
    'AnomalyScore': {'ko': '이상점수', 'en': 'Anomaly Score'},
    'AnomalyReason': {'ko': '주요원인', 'en': 'Reason'},
    'Attention': {'ko': '관심도', 'en': 'Attention'},
    'Rt': {'ko': 'Rt(실효재생산수)', 'en': 'Rt (Eff. Reproduction #)'},
    'Stage': {'ko': '확산단계', 'en': 'Diffusion Stage'},
    'EventDate': {'ko': '지정일', 'en': 'Event Date'},
    'Detected': {'ko': '조기탐지 여부', 'en': 'Detected'},
    'FirstFlagDate': {'ko': '최초 탐지일', 'en': 'First Flagged'},
    'LeadDaysApprox': {'ko': '리드타임(영업일)', 'en': 'Lead Time (days)'},
    'Marcap': {'ko': '시가총액(백만원)', 'en': 'Market Cap (KRW mn)'},
    'Sector': {'ko': '분야(업종)', 'en': 'Sector'},
    'PER': {'ko': 'PER', 'en': 'PER'},
    'BreakoutReturn': {'ko': '마지막 구간 상승률(%)', 'en': 'Last-segment Return (%)'},
    'HaltStartDate': {'ko': '거래정지 시작일', 'en': 'Halt Start Date'},
    'HaltDays': {'ko': '정지 영업일수', 'en': 'Halt Trading Days'},
    'MatchedPattern': {'ko': '매칭된 세부 유형', 'en': 'Matched Sub-type'},
    'ReboundReturn': {'ko': '저점 대비 반등률(%)', 'en': 'Rebound from Low (%)'},
    'VolumeRatio': {'ko': '거래량 유지비율', 'en': 'Volume Retention Ratio'},
}


def pattern_label(pattern_key, lang):
    """chart_pattern.PATTERN_DEFINITIONS의 key를 화면 표시용 라벨로 바꾼다."""
    from .chart_pattern import PATTERN_DEFINITIONS
    return PATTERN_DEFINITIONS[pattern_key]['label'][lang]


def t(key, lang, **kwargs):
    """번역 문자열을 가져온다. kwargs가 있으면 .format()으로 채워 넣는다."""
    text = TRANSLATIONS[key][lang]
    return text.format(**kwargs) if kwargs else text


def col_label(col, lang):
    """데이터프레임 컬럼명을 표시용 라벨로 바꾼다 (매핑에 없으면 원래 이름 유지)."""
    return COLUMN_LABELS.get(col, {}).get(lang, col)
