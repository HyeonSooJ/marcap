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
        'label': {'ko': '④ 횡보 후 급등형', 'en': '④ Sideways then Sudden Breakout'},
        'shape': _keypoints_to_shape([(0, 0.05), (0.4, 0.1), (0.75, 0.05), (0.8, 0.1), (1.0, 1.0)]),
    },
}

# sideways_breakout 패턴 전용 랭킹/표시 로직에서 쓰는 값들.
BREAKOUT_PATTERN_KEY = 'sideways_breakout'
# 실제 사용자가 예시로 든 종목들을 검증해보니(2025-09-03~2026-03-03), 급등 직전 저점이
# 항상 "마지막 20%"에 딱 걸쳐있지 않고 조금 더 이른 시점(예: 70~80% 지점)에 있는
# 경우가 많았다. 그래서 저점 탐색 구간을 마지막 20%가 아니라 마지막 60%로 넓혔다.
BREAKOUT_SEARCH_WINDOW_FRACTION = 0.6
# 이 패턴은 "상승률이 큰 종목을 최대한 폭넓게 보여주는" 용도라 다른 패턴보다 기본
# 표시 개수를 늘린다 (검증 결과: 상관계수 기준 상위 20개만으로는 실제 사용자가
# 원하는 종목 다수가 순위 밖으로 밀려남).
BREAKOUT_TOP_N = 100


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


def _breakout_surge(closes, search_window_fraction=BREAKOUT_SEARCH_WINDOW_FRACTION):
    """"횡보 후 급등"의 상승 폭(%)을 계산한다.

    기간의 마지막 search_window_fraction 구간에서 최저가(저점)를 찾고, 그
    저점 이후 최고가까지의 상승률을 반환한다. 마지막 날 종가만 보는 대신
    "저점 이후 최고가"를 보는 이유: 급등 후 며칠 사이 살짝 눌림목이 와도
    (예: 고점 찍고 조금 내려온 채로 조회 종료일을 맞아도) 급등 자체는
    놓치지 않기 위함.
    """
    closes = np.asarray(closes, dtype=float)
    closes = closes[~np.isnan(closes)]
    n = len(closes)
    if n < 10:
        return None
    win_start = int(n * (1 - search_window_fraction))
    window = closes[win_start:]
    trough_idx = win_start + int(np.argmin(window))
    trough_val = closes[trough_idx]
    if trough_val <= 0:
        return None
    peak_val = closes[trough_idx:].max()
    return (peak_val / trough_val - 1) * 100


def find_matching_stocks(price_df, pattern_key, top_n=None, min_coverage=0.6):
    """기간 내 종가 흐름이 지정한 차트 패턴과 가장 비슷한 종목을 찾는다.

    :param price_df: marcap_data(start, end)로 불러온 DataFrame (여러 종목,
        DatetimeIndex, Code/Name/Close/Market/Dept 컬럼 포함). filter_single_stocks
        적용 여부는 호출하는 쪽에서 결정한다.
    :param pattern_key: PATTERN_DEFINITIONS의 키
    :param top_n: 반환할 종목 수. None이면 패턴별 기본값(BREAKOUT_PATTERN_KEY는
        BREAKOUT_TOP_N, 그 외는 20)을 쓴다.
    :param min_coverage: 조회 기간의 영업일 대비 최소 데이터 보유 비율
        (거래정지/상장폐지 등으로 데이터가 너무 적은 종목은 제외)
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

    expected_days = price_df.index.normalize().nunique()
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
        last_row = group.iloc[-1]
        row = {
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'Score': score,
        }
        if show_breakout:
            row['BreakoutReturn'] = _breakout_surge(group['Close'].values)
        rows.append(row)

    columns = ['Code', 'Name', 'Close', 'Marcap', 'Score']
    if show_breakout:
        columns.append('BreakoutReturn')
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    sort_col = 'BreakoutReturn' if show_breakout else 'Score'
    return (
        result.sort_values(sort_col, ascending=False, na_position='last')
        .head(top_n)
        .reset_index(drop=True)
    )
