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
}

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
}


def t(key, lang, **kwargs):
    """번역 문자열을 가져온다. kwargs가 있으면 .format()으로 채워 넣는다."""
    text = TRANSLATIONS[key][lang]
    return text.format(**kwargs) if kwargs else text


def col_label(col, lang):
    """데이터프레임 컬럼명을 표시용 라벨로 바꾼다 (매핑에 없으면 원래 이름 유지)."""
    return COLUMN_LABELS.get(col, {}).get(lang, col)
