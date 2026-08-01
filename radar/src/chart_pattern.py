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


def find_matching_stocks(price_df, pattern_key, top_n=20, min_coverage=0.6):
    """기간 내 종가 흐름이 지정한 차트 패턴과 가장 비슷한 종목을 찾는다.

    :param price_df: marcap_data(start, end)로 불러온 DataFrame (여러 종목,
        DatetimeIndex, Code/Name/Close/Market/Dept 컬럼 포함). filter_single_stocks
        적용 여부는 호출하는 쪽에서 결정한다.
    :param pattern_key: PATTERN_DEFINITIONS의 키
    :param top_n: 반환할 종목 수
    :param min_coverage: 조회 기간의 영업일 대비 최소 데이터 보유 비율
        (거래정지/상장폐지 등으로 데이터가 너무 적은 종목은 제외)
    :return: DataFrame [Code, Name, Close, Marcap, Score] (Score 내림차순, 즉
        패턴과 가장 비슷한 종목이 먼저 옴)
    """
    if pattern_key not in PATTERN_DEFINITIONS:
        raise ValueError(f'알 수 없는 패턴: {pattern_key}')
    reference = PATTERN_DEFINITIONS[pattern_key]['shape']

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
        rows.append({
            'Code': code,
            'Name': last_row['Name'],
            'Close': last_row['Close'],
            'Marcap': last_row['Marcap'],
            'Score': score,
        })

    result = pd.DataFrame(rows, columns=['Code', 'Name', 'Close', 'Marcap', 'Score'])
    if result.empty:
        return result
    return result.sort_values('Score', ascending=False).head(top_n).reset_index(drop=True)
