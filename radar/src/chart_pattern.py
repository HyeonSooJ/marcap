# -*- coding: utf-8 -*-
"""마캡 데이터에서 지정한 기간 동안 특정 "차트 모양"과 비슷하게 움직인 종목을 찾는다.

방식: 종목별 종가 흐름을 정해진 개수(N_POINTS)의 점으로 리샘플링 + 0~1 정규화한 뒤,
4개의 기준 패턴(PATTERN_DEFINITIONS)과 피어슨 상관계수를 구해 가장 비슷한 순으로
정렬한다. 사용자가 그때그때 이미지를 그려서 인식시키는 대신, 패턴 자체를 미리
숫자로 정의해두고 전종목을 한 번에 빠르게(무료로) 비교하기 위함이다.

4개 패턴은 사용자가 직접 그려 전달한 손그림을 그대로 옮긴 것이다(키포인트만
숫자로 옮겼을 뿐 계산 로직과는 무관):
  1. 우상향형 - 완만하게 꾸준히 오르는 직선형
  2. 박스권 V자 반등형 - 저항선 부근에서 시작 -> 중간에 저점 -> 다시 원래 수준으로 복귀
  3. V자 반등 후 상승돌파형 - 2번처럼 저점을 찍지만, 원래 수준을 뚫고 더 높이 상승
  4. 횡보 후 급등형 - 대부분 구간은 옆으로 횡보하다가 막판에 거의 수직으로 급등
"""

import numpy as np
import pandas as pd

N_POINTS = 20


def _keypoints_to_shape(keypoints, n_points=N_POINTS):
    """[(x, y), ...] 키포인트(0~1 구간)를 길이 n_points인 배열로 보간한다."""
    xs, ys = zip(*keypoints)
    x_new = np.linspace(0, 1, n_points)
    return np.interp(x_new, xs, ys)


PATTERN_DEFINITIONS = {
    'uptrend': {
        'label': {'ko': '① 우상향형', 'en': '① Uptrend'},
        'shape': _keypoints_to_shape([(0, 0.0), (1, 1.0)]),
    },
    'range_v_rebound': {
        'label': {'ko': '② 박스권 V자 반등형', 'en': '② Range-bound V-shape Rebound'},
        'shape': _keypoints_to_shape([(0, 1.0), (0.15, 0.85), (0.55, 0.0), (0.85, 0.85), (1.0, 1.0)]),
    },
    'v_rebound_breakout': {
        'label': {'ko': '③ V자 반등 후 상승돌파형', 'en': '③ V-shape Rebound + Breakout'},
        'shape': _keypoints_to_shape([(0, 0.4), (0.2, 0.3), (0.55, 0.0), (0.75, 0.4), (1.0, 1.0)]),
    },
    'sideways_breakout': {
        'label': {'ko': '횡보 후 급등형', 'en': 'Sideways then Sudden Breakout'},
        'shape': _keypoints_to_shape([(0, 0.05), (0.4, 0.1), (0.75, 0.05), (0.8, 0.1), (1.0, 1.0)]),
    },
    # 거래정지 종목은 "모양"이 아니라 상태(거래정지 여부)로 찾는 것이라 shape가 없다.
    # find_matching_stocks가 아니라 find_halted_stocks가 별도로 처리한다.
    'trading_halt': {
        'label': {'ko': '④ 거래정지 종목', 'en': '④ Trading-halted Stocks'},
        'shape': None,
    },
    # 사용자 예시(해성옵틱스, RF머트리얼즈)로 검증: 기간 중반쯤 고점을 찍고 그 이후
    # 조회 종료일까지 계속 흘러내려 끝나는 모양. "눌림목 매수" 대상 — 아직 바닥을
    # 다지거나 반등하지 않고 하락이 진행 중인 상태를 찾는다.
    'rally_pullback': {
        'label': {'ko': '급등 후 눌림목형', 'en': 'Rally then Pullback'},
        'shape': _keypoints_to_shape([(0, 0.2), (0.55, 1.0), (1.0, 0.0)]),
    },
    # "조용한 종목이 내일 터질지"를 예측하는 게 아니라, "오늘 이미 상한가 간 종목 중
    # 내일도 이어질 가능성이 좀 더 높은 것"을 걸러주는 용도라 shape 상관계수 하나로
    # 표현되지 않는다. find_matching_stocks가 아니라 find_today_momentum_stocks가
    # 별도로 처리한다.
    'today_momentum': {
        'label': {'ko': '오늘 상한가 + 모양 필터', 'en': 'Today Limit-Up + Shape Filter'},
        'shape': None,
    },
    # 사용자 예시(코오롱티슈진, 한라캐스트)로 확인: 장기간(고점 대비 30%+) 하락하다가
    # 최근 구간에서 저점을 찍고, 그 이후 여러 날에 걸쳐 반등 중인 상태. 전체 기간
    # 대비 정규화한 모양 상관계수로는 하락폭이 워낙 커서 최근 반등이 잘 안 드러나
    # (예: 88% 하락 후 97% 반등해도 정규화값은 0.12 수준), _bottom_rebound_metrics가
    # "저점 대비 반등률"을 직접 계산하는 별도 로직으로 처리한다.
    'bottom_rebound': {
        'label': {'ko': '바닥 찍고 연속 반등형', 'en': 'Bottom then Rebound'},
        'shape': None,
    },
    # 사용자 가설("상한가 후 물량이 정리되면 다시 오른다")을 실제 상한가 846건으로
    # 검증했더니 정반대였다: 상한가 3일 뒤 거래량이 스파이크 당일 대비 많이 남아있을수록
    # (=거래량이 안 줄고 유지될수록) 2~7일 내 재상한가 확률이 훨씬 높았다(최상위
    # 분위 32.5% vs 최하위 분위 5.7%). find_sustained_volume_stocks가 처리한다.
    'sustained_volume': {
        'label': {'ko': '상한가 후 거래량 지속형', 'en': 'Sustained Volume After Limit-Up'},
        'shape': None,
    },
    # 사용자 예시(2026-09-04 급등: TPC로보틱스, E8)로 확인: 전체 조회 기간(1~수개월)
    # 기준 모양 상관계수로는 안 잡히지만, 최근 며칠(RECENT_PULLBACK_LOOKBACK_DAYS)
    # 안에서만 보면 "짧게 오르고(≥13%) - 살짝 눌리고(3~40%) - 아직 그 눌림목 저점보다는
    # 높은 채로 마감" 구조가 보인다. 전체 기간 모양 비교(sideways_breakout 등)는
    # 이런 짧은 구간의 등락을 20개 점으로 리샘플링하는 과정에서 뭉개버려서 못 잡는다.
    # 2026-04~09 상한가 데이터로 워크포워드 검증: 다음날 재상한가 확률 1.14%(무작위
    # 0.47%, 약 2.4배), 5거래일 내 4.6%(무작위 1.7%, 약 2.8배) — find_recent_pullback_stocks가
    # 처리한다.
    'recent_pullback': {
        'label': {'ko': '최근 눌림목 후 재상승형', 'en': 'Recent Pullback then Continuation'},
        'shape': None,
    },
    # 아래 2개는 사용자가 "종류가 너무 많다"고 해서, 위 6개(sideways_breakout/
    # rally_pullback/bottom_rebound/today_momentum/sustained_volume/recent_pullback
    # 중 성격이 비슷한 것끼리) 묶어 메뉴에는 이 2개만 노출한다(MENU_PATTERN_KEYS).
    # 원본 6개 함수는 그대로 두고, find_presurge_pattern_stocks/
    # find_limitup_continuation_stocks가 각각을 호출해 결과를 합친다.
    'presurge_pattern': {
        'label': {'ko': '⑤ 급등 전조 패턴형', 'en': '⑤ Pre-surge Pattern'},
        'shape': None,
    },
    'limitup_continuation': {
        'label': {'ko': '⑥ 상한가 지속형', 'en': '⑥ Limit-Up Continuation'},
        'shape': None,
    },
}

# 화면 드롭다운에 실제로 노출할 패턴 목록(순서대로). PATTERN_DEFINITIONS에는
# 내부적으로 재사용되는 개별 패턴(sideways_breakout 등)도 같이 들어있지만,
# 그건 메뉴에 안 보이고 presurge_pattern/limitup_continuation 안에서만 쓰인다.
MENU_PATTERN_KEYS = [
    'uptrend', 'range_v_rebound', 'v_rebound_breakout', 'trading_halt',
    'presurge_pattern', 'limitup_continuation',
]
PRESURGE_PATTERN_KEY = 'presurge_pattern'
LIMITUP_CONTINUATION_KEY = 'limitup_continuation'

# ⑤⑥ 두 메뉴는 "급등주 찾기"가 목적이라 다른 메뉴(①②③④)보다 넓은 종목군을
# 봐야 한다. 실제 사례(2026-09-04 급등: TPC로보틱스/E8/KS인더스트리/원익홀딩스)를
# 검증해보니, E8(시총 87억)·KS인더스트리(시총 83억)는 시총 순위 2000위 밖(각각
# 2767위/2781위)이라 애초에 검색 대상에도 못 들어가고 있었다. 또한 관리종목/
# 투자주의환기종목처럼 KRX가 공식적으로 위험 표시한 종목도 급등주에 자주
# 등장한다(E8=관리종목, KS인더스트리=투자주의환기종목이었음) — 사용자 선택에 따라
# 제외하지 않고 대신 결과 표에 위험 표시를 달아서 보여준다.
SURGE_TOP_MARCAP_N = 3000            # 사실상 전종목(단일종목 전체가 약 2900개 수준)
SURGE_MIN_MARCAP = 5_000_000_000     # 시총 50억원 미만만 제외 (④/⑧ 기본 300억원보다 훨씬 낮춤)
SURGE_MIN_RECENT_AMOUNT = 100_000_000  # 최근 거래대금 1억원 미만만 제외 (④/⑧ 기본 10억원보다 낮춤)
RISK_DEPT_KEYWORDS = ['관리종목', '투자주의환기종목', '투자경고종목', '투자위험종목', '거래정지']

RECENT_PULLBACK_PATTERN_KEY = 'recent_pullback'
RECENT_PULLBACK_LOOKBACK_DAYS = 6     # 최근 6거래일(약 1주일)만 본다 — 전체 기간 모양과는 별개
RECENT_PULLBACK_MIN_PRIOR_RISE = 13.0  # 눌림목 직전 고점까지 최소 13% 이상 올랐어야 함
RECENT_PULLBACK_MIN_PULLBACK = 3.0    # 고점 대비 최소 3% 이상은 눌려야 함(그래야 "눌림목")
RECENT_PULLBACK_MAX_PULLBACK = 40.0   # 40% 넘게 눌리면 눌림목이 아니라 그냥 반락으로 봄
RECENT_PULLBACK_TOP_N = 100

HALT_PATTERN_KEY = 'trading_halt'
RALLY_PULLBACK_PATTERN_KEY = 'rally_pullback'
TODAY_MOMENTUM_PATTERN_KEY = 'today_momentum'
BOTTOM_REBOUND_PATTERN_KEY = 'bottom_rebound'
SUSTAINED_VOLUME_PATTERN_KEY = 'sustained_volume'
SUSTAINED_VOLUME_TOP_N = 50
SUSTAINED_VOLUME_LOOKBACK_DAYS = 10  # 최근 며칠 이내의 상한가만 탐색 대상으로 삼음
SUSTAINED_VOLUME_CONFIRM_DAYS = 3    # 상한가 후 며칠 뒤 거래량을 비교할지
# 실제 검증(2026년 상한가 846건): 상한가 3일 뒤 거래량 / 상한가 당일 거래량 비율이
# 1.5 이상인 종목의 2~7일 내 재상한가 확률은 31.7%(243건) — 전체 평균 17.4%의
# 약 1.8배, 최하위 분위(0.27 미만) 대비 약 5.5배.
SUSTAINED_VOLUME_MIN_RATIO = 1.5
BOTTOM_REBOUND_TOP_N = 100
BOTTOM_REBOUND_SEARCH_WINDOW_FRACTION = 0.4  # 저점 탐색: 최근 40% 구간
BOTTOM_REBOUND_MIN_PRE_DECLINE = 30.0        # 저점까지 최소 30% 이상 하락(장기 하락 확인용)
BOTTOM_REBOUND_MIN_RISE = 15.0               # 저점 대비 최소 15% 이상 반등
BOTTOM_REBOUND_MIN_MARCAP = 30_000_000_000   # 시가총액 300억원 미만 제외 (④번과 동일 기준)
BOTTOM_REBOUND_MIN_RECENT_AMOUNT = 1_000_000_000  # 최근 1개월 평균 거래대금 10억원 미만 제외
# 실제 검증(2026년 5~7월, 조회 종료일에 상한가를 기록한 종목 647건): 다음날도
# 상한가를 갈 확률은 평균 16.7%였는데, 최근 2개월 흐름이 ④번 모양과 상관계수
# 0.6 이상이면 20.0%(195건), ⑥번 모양과 0.5 이상이면 23.8%(42건)로 올라갔다.
# "조용한 종목의 다음날 급등"은 예측이 안 됐지만(다른 백테스트 참고), "오늘 이미
# 상한가 간 종목 중 어떤 게 내일도 이어질지"는 이 조건으로 어느 정도 걸러진다.
TODAY_MOMENTUM_LOOKBACK_MONTHS = 2
TODAY_MOMENTUM_MIN_SCORE4 = 0.6
TODAY_MOMENTUM_MIN_SCORE6 = 0.5

# sideways_breakout 패턴 전용 랭킹/표시 로직에서 쓰는 값들.
BREAKOUT_PATTERN_KEY = 'sideways_breakout'
# 사용자 예시 종목들을 검증해보니(2025-09-03~2026-03-03), 고점(돌파 완료 시점)이
# 조회 종료일 기준 최근 1개월 안에 몰려있었다("오래전에 이미 급등했다가 식은 종목"은
# 제외하고 "최근에 막 급등한 종목"만 원하는 것). 그래서 고점은 반드시 최근 1개월
# 이내여야 하고, 저점은 그 이전 구간 전체에서 찾는다(급등 시작점은 더 이를 수 있음).
BREAKOUT_RECENT_MONTHS = 1
# 이 패턴은 "상승률이 큰 종목을 최대한 폭넓게 보여주는" 용도라 다른 패턴보다 기본
# 표시 개수를 늘린다 (검증 결과: 상관계수 기준 상위 20개만으로는 실제 사용자가
# 원하는 종목 다수가 순위 밖으로 밀려남).
BREAKOUT_TOP_N = 100
# "너무 작은 잡주는 안 된다"는 요청으로 처음엔 1,000억원으로 잡았으나, 실제 상한가
# 종목의 69%가 시총 1,000억 미만이라 오히려 상한가 종목 대부분을 걸러내는 부작용이
# 있었음(2026년 7월 상한가 243건 검증). 300억원으로 낮춰서 커버리지 28%->58%로 개선.
BREAKOUT_MIN_MARCAP = 30_000_000_000        # 시가총액 300억원 미만 제외
BREAKOUT_MIN_RECENT_AMOUNT = 1_000_000_000  # 최근 1개월 평균 거래대금 10억원 미만 제외


def resolve_date_range(end_date, months):
    """선택한 종료일 + 개월 수로 조회 시작일을 계산한다 (달력 개월 기준).

    예: 종료일 4/1, 3개월 -> 1/1. 종료일 7/25, 6개월 -> 1/25.
    """
    end_date = pd.to_datetime(end_date)
    start_date = end_date - pd.DateOffset(months=months)
    return start_date, end_date


def filter_single_stocks(df):
    """marcap DataFrame에서 국내 보통주 단일종목만 남긴다.

    우선주(코드 끝자리가 0이 아님)/스팩/리츠/코넥스를 제외한다. 정교한 종목
    분류 체계는 아니고, 이름/코드 규칙에 기반한 실용적 필터다.
    """
    mask = (
        df['Market'].isin(['KOSPI', 'KOSDAQ', 'KOSDAQ GLOBAL'])
        & df['Code'].str.endswith('0')
        & ~df['Dept'].str.contains('SPAC', na=False)
        & ~df['Name'].str.contains('스팩|리츠', na=False)
    )
    return df[mask]


TOP_MARCAP_N = 2000


def filter_top_marcap(df, top_n=TOP_MARCAP_N):
    """조회 기간의 마지막 거래일 기준 시가총액 상위 top_n 종목만 남긴다.

    marcap 데이터의 Rank 컬럼(당일 전체 시가총액 순위, 코스피+코스닥+코넥스+
    우선주 등 전체 상장종목 기준)을 그대로 이용한다. 이 함수는 보통
    filter_single_stocks 이후에 적용해서 "코스피/코스닥 보통주 중 시가총액
    상위 top_n"이 되도록 한다.
    """
    if df.empty:
        return df
    last_date = df.index.max()
    snapshot = df[df.index == last_date]
    top_codes = set(snapshot.loc[snapshot['Rank'] <= top_n, 'Code'])
    return df[df['Code'].isin(top_codes)]


def _resample_normalize(values, n_points=N_POINTS):
    """종가 배열을 n_points 길이로 리샘플링 + 0~1 정규화. 데이터가 너무 적거나
    (거래정지 등) 완전히 평평하면 None을 반환한다."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 5:
        return None
    x_old = np.linspace(0, 1, len(values))
    x_new = np.linspace(0, 1, n_points)
    y = np.interp(x_new, x_old, values)
    y_min, y_max = y.min(), y.max()
    if y_max - y_min < 1e-9:
        return None
    return (y - y_min) / (y_max - y_min)


def _breakout_surge(
    group, window_end, recent_months=BREAKOUT_RECENT_MONTHS,
    min_marcap=BREAKOUT_MIN_MARCAP, min_amount=BREAKOUT_MIN_RECENT_AMOUNT,
):
    """"횡보 후 급등"의 상승 폭(%)을 계산한다. 고점이 최근에 없으면 None.

    조회 종료일(window_end) 기준 최근 recent_months(기본 1개월) 안에서 고점을
    찾고, 그 이전 구간 전체에서 저점(급등 시작 전 최저가)을 찾아 상승률을
    계산한다. 고점이 최근 1개월보다 더 예전에 있었던(=이미 오래전에 급등이
    끝나고 식은) 종목은 지금 시점에서 찾을 필요가 없으므로 None을 반환해
    제외한다.

    :param group: 한 종목의 marcap 데이터 (DatetimeIndex, Close/Amount/Marcap
        컬럼, 날짜순 정렬됨)
    :param window_end: 조회 종료일
    :param min_marcap: 시가총액 최소 기준. find_presurge_pattern_stocks는 더
        작은 종목까지 잡기 위해 SURGE_MIN_MARCAP으로 낮춰서 호출한다.
    :param min_amount: 최근 평균 거래대금 최소 기준(위와 동일한 이유로 오버라이드 가능).
    """
    if len(group) < 10:
        return None
    if group['Marcap'].iloc[-1] < min_marcap:
        return None
    recent_start = window_end - pd.DateOffset(months=recent_months)
    recent = group[group.index >= recent_start]
    if recent.empty:
        return None
    if recent['Amount'].mean() < min_amount:
        return None
    peak_date = recent['Close'].idxmax()
    peak_val = recent.loc[peak_date, 'Close']
    pre_peak = group.loc[:peak_date, 'Close']
    if len(pre_peak) < 5:
        return None
    trough_val = pre_peak.min()
    if trough_val <= 0:
        return None
    return (peak_val / trough_val - 1) * 100


def find_matching_stocks(
    price_df, pattern_key, top_n=None, min_coverage=0.6, min_marcap=None, min_amount=None,
):
    """기간 내 종가 흐름이 지정한 차트 패턴과 가장 비슷한 종목을 찾는다.

    :param price_df: marcap_data(start, end)로 불러온 DataFrame (여러 종목,
        DatetimeIndex, Code/Name/Close/Market/Dept 컬럼 포함). filter_single_stocks
        적용 여부는 호출하는 쪽에서 결정한다.
    :param pattern_key: PATTERN_DEFINITIONS의 키
    :param top_n: 반환할 종목 수. None이면 패턴별 기본값(BREAKOUT_PATTERN_KEY는
        BREAKOUT_TOP_N, 그 외는 20)을 쓴다.
    :param min_coverage: 조회 기간의 영업일 대비 최소 데이터 보유 비율
        (거래정지/상장폐지 등으로 데이터가 너무 적은 종목은 제외)
    :param min_marcap: BREAKOUT_PATTERN_KEY 전용. None이면 BREAKOUT_MIN_MARCAP을
        쓴다(find_presurge_pattern_stocks가 더 작은 종목까지 잡기 위해 낮춰서 호출).
    :param min_amount: 위와 동일한 이유의 거래대금 기준 오버라이드.
    :return: DataFrame [Code, Name, Close, Marcap, Score]. pattern_key가
        BREAKOUT_PATTERN_KEY이면 BreakoutReturn(저점 대비 이후 고점 상승률, %)
        컬럼이 추가되고, 정렬 기준도 Score가 아니라 BreakoutReturn 내림차순이
        된다 — 이 패턴은 "모양이 비슷한 정도"보다 "실제로 얼마나 급등했는지"가
        사용자가 찾으려는 핵심이기 때문이다.
    """
    if pattern_key not in PATTERN_DEFINITIONS:
        raise ValueError(f'알 수 없는 패턴: {pattern_key}')
    reference = PATTERN_DEFINITIONS[pattern_key]['shape']
    show_breakout = pattern_key == BREAKOUT_PATTERN_KEY
    if top_n is None:
        top_n = BREAKOUT_TOP_N if show_breakout else 20
    if min_marcap is None:
        min_marcap = BREAKOUT_MIN_MARCAP
    if min_amount is None:
        min_amount = BREAKOUT_MIN_RECENT_AMOUNT

    expected_days = price_df.index.normalize().nunique()
    window_end = price_df.index.max()
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        coverage = len(group) / expected_days if expected_days else 0
        if coverage < min_coverage:
            continue
        normalized = _resample_normalize(group['Close'].values)
        if normalized is None:
            continue
        score = np.corrcoef(normalized, reference)[0, 1]
        if np.isnan(score):
            continue
        if show_breakout:
            # 최근 1개월 내 고점 + 최소 시가총액/거래대금을 만족 못하면 애초에
            # "④ 횡보 후 급등형" 후보 자격이 없는 것으로 보고 제외한다(등수만
            # 밀어내는 게 아니라 목록에서 아예 뺀다).
            breakout_return = _breakout_surge(group, window_end, min_marcap=min_marcap, min_amount=min_amount)
            if breakout_return is None:
                continue
        last_row = group.iloc[-1]
        row = {
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'Score': score,
        }
        if show_breakout:
            row['BreakoutReturn'] = breakout_return
        rows.append(row)

    columns = ['Code', 'Name', 'Close', 'Marcap', 'Score']
    if show_breakout:
        columns.append('BreakoutReturn')
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    # 모양이 기준 패턴과 얼마나 비슷한지(Score)로 최종 정렬한다. sideways_breakout도
    # 마찬가지다 — "얼마나 많이 올랐는지"보다 "얼마나 전형적인 횡보-후-급등 모양인지"가
    # 사용자가 찾으려는 기준에 더 가깝다는 게 실제 예시 종목으로 검증됨(상승률 정렬은
    # 시장 전체의 극단적 상승 종목들이 상위를 차지해버려 원하는 종목들이 순위 밖으로
    # 밀려났었음).
    return (
        result.sort_values('Score', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def find_halted_stocks(price_df, top_n=100):
    """조회 종료일 기준 거래정지 중인 종목을 찾는다.

    marcap 데이터는 거래정지일에도 종가/시가총액은 정지 직전 값 그대로, 거래량만
    0으로 기록된다. 이 함수는 그 상태(마지막 날 Volume==0)를 그대로 이용한다.

    :param price_df: marcap_data(start, end, include_halted=True)로 불러온
        DataFrame — include_halted=False(기본값)로 불러오면 거래정지일 행 자체가
        빠져있어 이 함수가 아무것도 못 찾는다.
    :param top_n: 반환할 종목 수
    :return: DataFrame [Code, Name, Close, Marcap, HaltStartDate, HaltDays]
        (HaltStartDate 내림차순, 즉 최근에 정지된 종목이 먼저 옴).
        HaltStartDate는 조회 시작일 이전부터 정지 중이었을 경우 조회 시작일로
        표시된다(그 이전 데이터는 조회 범위 밖이라 알 수 없음).
    """
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        last_row = group.iloc[-1]
        if last_row['Volume'] != 0:
            continue  # 마지막 날 거래됐으면 지금은 정지 상태가 아님
        halted = (group['Volume'] == 0).values
        streak = 0
        for v in halted[::-1]:
            if not v:
                break
            streak += 1
        halt_start_date = group.index[-streak]
        rows.append({
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'HaltStartDate': halt_start_date,
            'HaltDays': streak,
        })

    columns = ['Code', 'Name', 'Close', 'Marcap', 'HaltStartDate', 'HaltDays']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return (
        result.sort_values('HaltStartDate', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


LIMIT_UP_MIN, LIMIT_UP_MAX = 29.0, 30.5  # 상한가(당일 종가 기준 등락률). 이 범위 밖은
# 데이터 이상치(상장일/액면분할 등으로 등락률이 수백~수만 %로 찍히는 경우)로 본다.


def find_today_momentum_stocks(price_df, top_n=50):
    """조회 종료일에 실제로 상한가를 기록한 종목 중, 최근 흐름이 ④(횡보 후 급등)
    또는 ⑥(급등 후 눌림목) 모양과 비슷한 것만 걸러 보여준다.

    "아직 조용한 종목이 내일 터질지"를 예측하는 게 아니라 — 그건 실제 검증에서
    신호를 찾지 못했다 — "오늘 이미 상한가 간 종목 중 내일도 이어질 가능성이 좀 더
    높은 것"을 거르는 용도다. 그래서 조회 종료일 자체가 실제 상한가가 있었던
    날짜여야 결과가 나온다(그런 날이 아니면 빈 결과).

    :param price_df: marcap_data(start, end)로 불러온 DataFrame
    :return: DataFrame [Code, Name, Close, Marcap, Score4, Score6, MatchedPattern]
        (BestScore = max(Score4, Score6) 내림차순)
    """
    columns = ['Code', 'Name', 'Close', 'Marcap', 'Score4', 'Score6', 'MatchedPattern']
    if price_df.empty:
        return pd.DataFrame(columns=columns)

    window_end = price_df.index.max()
    today_df = price_df[price_df.index == window_end]
    today_limitup = today_df[
        (today_df['ChangesRatio'] >= LIMIT_UP_MIN) & (today_df['ChangesRatio'] <= LIMIT_UP_MAX)
    ]
    if today_limitup.empty:
        return pd.DataFrame(columns=columns)

    lookback_start = window_end - pd.DateOffset(months=TODAY_MOMENTUM_LOOKBACK_MONTHS)
    shape4 = PATTERN_DEFINITIONS[BREAKOUT_PATTERN_KEY]['shape']
    shape6 = PATTERN_DEFINITIONS[RALLY_PULLBACK_PATTERN_KEY]['shape']

    rows = []
    for _, today_row in today_limitup.iterrows():
        code = today_row['Code']
        hist = price_df[
            (price_df['Code'] == code) & (price_df.index >= lookback_start) & (price_df.index <= window_end)
        ].sort_index()
        if len(hist) < 20:
            continue
        normalized = _resample_normalize(hist['Close'].values)
        if normalized is None:
            continue
        s4 = np.corrcoef(normalized, shape4)[0, 1]
        s6 = np.corrcoef(normalized, shape6)[0, 1]
        if np.isnan(s4):
            s4 = -1.0
        if np.isnan(s6):
            s6 = -1.0
        if s4 < TODAY_MOMENTUM_MIN_SCORE4 and s6 < TODAY_MOMENTUM_MIN_SCORE6:
            continue
        rows.append({
            'Code': code,
            'Name': today_row['Name'],
            'Close': today_row['Close'],
            'Marcap': today_row['Marcap'],
            'Score4': s4,
            'Score6': s6,
            'MatchedPattern': '④' if s4 >= s6 else '⑥',
            'BestScore': max(s4, s6),
        })

    result = pd.DataFrame(rows, columns=columns + ['BestScore'])
    if result.empty:
        return result[columns]
    return (
        result.sort_values('BestScore', ascending=False)
        .head(top_n)
        .reset_index(drop=True)[columns]
    )


def _bottom_rebound_metrics(
    group, search_window_fraction=BOTTOM_REBOUND_SEARCH_WINDOW_FRACTION,
    min_marcap=BOTTOM_REBOUND_MIN_MARCAP, min_amount=BOTTOM_REBOUND_MIN_RECENT_AMOUNT,
):
    """"바닥 찍고 연속 반등"의 저점 대비 반등률(%)을 계산한다. 조건 미달이면 None.

    최근 search_window_fraction 구간에서 저점을 찾고, 그 저점 이전까지의 고점 대비
    얼마나 하락했었는지(장기 하락 확인)와, 저점 이후 지금까지 얼마나 반등했는지를
    함께 확인한다. 저점이 바로 오늘이면(아직 반등이 시작 안 됨) 제외한다.

    :param min_marcap: None이면 BOTTOM_REBOUND_MIN_MARCAP을 쓴다
        (find_presurge_pattern_stocks가 더 작은 종목까지 잡기 위해 낮춰서 호출).
    :param min_amount: 위와 동일한 이유의 거래대금 기준 오버라이드.
    """
    if len(group) < 20:
        return None
    if group['Marcap'].iloc[-1] < min_marcap:
        return None
    if group['Amount'].tail(20).mean() < min_amount:
        return None

    closes = group['Close'].values
    n = len(closes)
    win_start = int(n * (1 - search_window_fraction))
    search_zone = closes[win_start:]
    low_idx = win_start + int(np.argmin(search_zone))
    if low_idx >= n - 1:
        return None  # 저점이 바로 오늘 -> 아직 반등이 시작되지 않음
    low_val = closes[low_idx]
    if low_val <= 0:
        return None

    pre_low = closes[:low_idx + 1]
    period_high = pre_low.max()
    if period_high <= 0:
        return None
    pre_decline_pct = (low_val / period_high - 1) * 100
    if pre_decline_pct > -BOTTOM_REBOUND_MIN_PRE_DECLINE:
        return None  # 저점까지의 하락폭이 부족(장기 하락이 아니었음)

    current_val = closes[-1]
    rise_pct = (current_val / low_val - 1) * 100
    if rise_pct < BOTTOM_REBOUND_MIN_RISE:
        return None
    return rise_pct


def find_bottom_rebound_stocks(price_df, top_n=None, min_marcap=None, min_amount=None):
    """장기 하락 후 저점을 찍고 반등 중인 종목을 찾는다.

    :param min_marcap: None이면 BOTTOM_REBOUND_MIN_MARCAP을 쓴다.
    :param min_amount: None이면 BOTTOM_REBOUND_MIN_RECENT_AMOUNT를 쓴다.
    :return: DataFrame [Code, Name, Close, Marcap, ReboundReturn] (ReboundReturn
        = 저점 대비 현재까지 상승률(%), 내림차순)
    """
    if top_n is None:
        top_n = BOTTOM_REBOUND_TOP_N
    if min_marcap is None:
        min_marcap = BOTTOM_REBOUND_MIN_MARCAP
    if min_amount is None:
        min_amount = BOTTOM_REBOUND_MIN_RECENT_AMOUNT
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        rise_pct = _bottom_rebound_metrics(group, min_marcap=min_marcap, min_amount=min_amount)
        if rise_pct is None:
            continue
        last_row = group.iloc[-1]
        rows.append({
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'ReboundReturn': rise_pct,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'ReboundReturn']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return (
        result.sort_values('ReboundReturn', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def _recent_pullback_metrics(
    group, lookback_days=RECENT_PULLBACK_LOOKBACK_DAYS,
    min_prior_rise=RECENT_PULLBACK_MIN_PRIOR_RISE, min_pullback=RECENT_PULLBACK_MIN_PULLBACK,
    max_pullback=RECENT_PULLBACK_MAX_PULLBACK, min_marcap=SURGE_MIN_MARCAP, min_amount=SURGE_MIN_RECENT_AMOUNT,
):
    """최근 lookback_days(기본 6거래일) 안에서 "짧게 오르고 - 살짝 눌리고 - 아직
    저점보다는 높은 채로 마감"인 종목의 (PriorRise%, Pullback%)을 계산한다.
    조건 미달이면 None.

    sideways_breakout/bottom_rebound 등 기존 모양 비교는 조회 기간 전체
    (1~수개월)를 20개 점으로 리샘플링해서 보기 때문에 이런 짧은 며칠짜리
    등락은 뭉개져서 안 잡힌다 — 그래서 최근 며칠만 별도로 본다.
    """
    if len(group) < lookback_days + 5:
        return None
    if group['Marcap'].iloc[-1] < min_marcap:
        return None
    if group['Amount'].tail(20).mean() < min_amount:
        return None
    closes = group['Close'].values[-lookback_days:]
    peak_idx = int(np.argmax(closes))
    if peak_idx == len(closes) - 1:
        return None  # 고점이 바로 오늘 -> 아직 눌림목이 시작되지 않음(이미 급등 중)
    peak_val = closes[peak_idx]
    pre_peak = closes[:peak_idx + 1]
    trough = pre_peak.min()
    if trough <= 0:
        return None
    prior_rise = (peak_val / trough - 1) * 100
    if prior_rise < min_prior_rise:
        return None
    current = closes[-1]
    if current <= trough:
        return None  # 눌림목 저점보다 더 내려갔다 -> 눌림목이 아니라 추세 반전
    pullback = (peak_val - current) / peak_val * 100
    if pullback < min_pullback or pullback > max_pullback:
        return None
    return prior_rise, pullback


def find_recent_pullback_stocks(price_df, top_n=None, min_marcap=None, min_amount=None):
    """최근 며칠간 짧게 오른 뒤 살짝 눌리고 있는(=재상승 대기 중일 수 있는) 종목을 찾는다.

    :param min_marcap: None이면 SURGE_MIN_MARCAP을 쓴다(이 패턴은 애초에 ⑤ 급등
        전조 패턴형 전용으로 만들어져 기본값부터 완화된 기준을 쓴다).
    :param min_amount: None이면 SURGE_MIN_RECENT_AMOUNT를 쓴다.
    :return: DataFrame [Code, Name, Close, Marcap, PriorRise, Pullback]
        (Pullback 오름차순 — 눌림폭이 얕을수록/타이트할수록 먼저 나옴)
    """
    if top_n is None:
        top_n = RECENT_PULLBACK_TOP_N
    if min_marcap is None:
        min_marcap = SURGE_MIN_MARCAP
    if min_amount is None:
        min_amount = SURGE_MIN_RECENT_AMOUNT
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        metrics = _recent_pullback_metrics(group, min_marcap=min_marcap, min_amount=min_amount)
        if metrics is None:
            continue
        prior_rise, pullback = metrics
        last_row = group.iloc[-1]
        rows.append({
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'PriorRise': prior_rise,
            'Pullback': pullback,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'PriorRise', 'Pullback']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return (
        result.sort_values('Pullback', ascending=True)
        .head(top_n)
        .reset_index(drop=True)
    )


def _sustained_volume_metrics(group):
    """가장 최근 상한가 이후 SUSTAINED_VOLUME_CONFIRM_DAYS일째 거래량이 상한가
    당일 대비 얼마나 남아있는지(비율)를 계산한다. 조건 미달이면 None.

    최근 SUSTAINED_VOLUME_LOOKBACK_DAYS 거래일 안에 상한가가 있고, 그 이후
    SUSTAINED_VOLUME_CONFIRM_DAYS일치 데이터가 이미 존재해야(즉 오늘 막 터진
    상한가는 아직 판단 불가) 계산 가능하다.
    """
    n = len(group)
    if n < SUSTAINED_VOLUME_LOOKBACK_DAYS + SUSTAINED_VOLUME_CONFIRM_DAYS + 1:
        return None
    chg = group['ChangesRatio'].values
    vol = group['Volume'].values

    # 오늘(마지막 행) 기준 SUSTAINED_VOLUME_CONFIRM_DAYS일 전까지의 구간에서
    # 가장 최근 상한가를 찾는다(그래야 그 이후 CONFIRM_DAYS일치 데이터가 존재).
    search_end = n - 1 - SUSTAINED_VOLUME_CONFIRM_DAYS
    search_start = max(0, n - 1 - SUSTAINED_VOLUME_LOOKBACK_DAYS)
    spike_idx = None
    for i in range(search_end, search_start - 1, -1):
        if LIMIT_UP_MIN <= chg[i] <= LIMIT_UP_MAX:
            spike_idx = i
            break
    if spike_idx is None:
        return None

    spike_vol = vol[spike_idx]
    if spike_vol <= 0:
        return None
    confirm_vol = vol[spike_idx + SUSTAINED_VOLUME_CONFIRM_DAYS]
    ratio = confirm_vol / spike_vol
    if ratio < SUSTAINED_VOLUME_MIN_RATIO:
        return None
    return ratio


def find_sustained_volume_stocks(price_df, top_n=None):
    """최근 상한가를 기록했고, 그 이후 거래량이 계속 유지(감소하지 않음)되고
    있는 종목을 찾는다.

    :return: DataFrame [Code, Name, Close, Marcap, VolumeRatio] (VolumeRatio =
        상한가 CONFIRM_DAYS일 뒤 거래량 / 상한가 당일 거래량, 내림차순)
    """
    if top_n is None:
        top_n = SUSTAINED_VOLUME_TOP_N
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        ratio = _sustained_volume_metrics(group)
        if ratio is None:
            continue
        last_row = group.iloc[-1]
        rows.append({
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'VolumeRatio': ratio,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'VolumeRatio']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return (
        result.sort_values('VolumeRatio', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def _dept_risk_label(dept):
    """Dept 값(예: '관리종목(소속부없음)')에 KRX 공식 위험 지정 키워드가 있으면
    그 키워드를, 없으면 None을 반환한다."""
    if not isinstance(dept, str):
        return None
    for kw in RISK_DEPT_KEYWORDS:
        if kw in dept:
            return kw
    return None


def _combine_with_source_tag(frames_with_labels, price_df):
    """[(DataFrame, 라벨), ...]을 Code/Name/Close/Marcap + MatchedPattern + Risk로
    합친다. 같은 종목이 여러 하위 패턴에 동시에 걸리면 먼저 나온 것 하나만 남긴다
    (순서가 우선순위 — 더 강하게 검증된 패턴을 앞에 둔다). Risk는 price_df의 최근
    Dept 값에서 관리종목/투자주의환기종목 등 KRX 공식 위험 지정 여부를 뽑아온다
    (이 두 메뉴는 시가총액 필터를 낮춰서 그런 종목도 검색 대상에 포함하기 때문).
    """
    frames = []
    for df_part, label in frames_with_labels:
        if df_part is None or df_part.empty:
            continue
        part = df_part[['Code', 'Name', 'Close', 'Marcap']].copy()
        part['MatchedPattern'] = label
        frames.append(part)
    columns = ['Code', 'Name', 'Close', 'Marcap', 'MatchedPattern', 'Risk']
    if not frames:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset='Code', keep='first').reset_index(drop=True)
    last_dept = price_df.sort_index().groupby('Code')['Dept'].last()
    combined['Risk'] = combined['Code'].map(last_dept).map(_dept_risk_label)
    return combined[columns]


def find_presurge_pattern_stocks(price_df, top_n=100):
    """④횡보후급등형 + ⑥급등후눌림목형 + ⑧바닥찍고연속반등형 + 최근 눌림목 후
    재상승형을 합쳐서 보여준다("급등 전조 패턴형" — 아직 상한가가 확정되지 않은,
    모양만으로 추정하는 후보들).

    ④/⑧은 시가총액/거래대금 하한을 SURGE_MIN_MARCAP/SURGE_MIN_RECENT_AMOUNT로
    낮춰서 호출한다 — 기본 300억원/10억원 기준으로는 실제 급등주(2026-09-04
    E8 시총 87억, KS인더스트리 83억)가 걸러져버리는 게 확인됐기 때문. 최근 눌림목
    후 재상승형(find_recent_pullback_stocks)은 애초에 이 완화된 기준을 기본값으로
    쓴다.
    """
    r_sideways = find_matching_stocks(
        price_df, BREAKOUT_PATTERN_KEY, top_n=top_n,
        min_marcap=SURGE_MIN_MARCAP, min_amount=SURGE_MIN_RECENT_AMOUNT,
    )
    r_rally = find_matching_stocks(price_df, RALLY_PULLBACK_PATTERN_KEY, top_n=top_n)
    r_bottom = find_bottom_rebound_stocks(
        price_df, top_n=top_n, min_marcap=SURGE_MIN_MARCAP, min_amount=SURGE_MIN_RECENT_AMOUNT,
    )
    r_recent = find_recent_pullback_stocks(price_df, top_n=top_n)
    labels = PATTERN_DEFINITIONS
    return _combine_with_source_tag([
        (r_sideways, labels[BREAKOUT_PATTERN_KEY]['label']['ko']),
        (r_bottom, labels[BOTTOM_REBOUND_PATTERN_KEY]['label']['ko']),
        (r_recent, labels[RECENT_PULLBACK_PATTERN_KEY]['label']['ko']),
        (r_rally, labels[RALLY_PULLBACK_PATTERN_KEY]['label']['ko']),
    ], price_df)


def find_limitup_continuation_stocks(price_df, top_n=50):
    """⑦오늘상한가+모양필터 + ⑨상한가후거래량지속형을 합쳐서 보여준다
    ("상한가 지속형" — 이미 상한가가 확정된 종목 중 내일 이어질 가능성이 높은 후보들).

    이 둘은 원래부터 시가총액/거래대금 하한이 없다(상한가 자체가 조건이라 이미
    충분히 좁혀짐) — 대신 호출하는 쪽(app.py)에서 시총 상위 SURGE_TOP_MARCAP_N까지
    보도록 확장해서 넘겨줘야 한다.
    """
    r_today = find_today_momentum_stocks(price_df, top_n=top_n)
    r_vol = find_sustained_volume_stocks(price_df, top_n=top_n)
    labels = PATTERN_DEFINITIONS
    return _combine_with_source_tag([
        (r_vol, labels[SUSTAINED_VOLUME_PATTERN_KEY]['label']['ko']),
        (r_today, labels[TODAY_MOMENTUM_PATTERN_KEY]['label']['ko']),
    ], price_df)
