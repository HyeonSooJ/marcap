# -*- coding: utf-8 -*-
"""차트 모양 조건검색 - 한 파일짜리 독립 실행 버전.

marcap 저장소(https://github.com/HyeonSooJ/marcap)의 radar/app.py 5번째 탭
("차트 모양 조건검색")만 따로 뗀 단일 파일입니다. 다른 라디오 탭(이상신호,
데일리 리포트 등)은 없고, 대신 marcap 저장소 안에 있는 상태로 실행해야
합니다 (같은 저장소의 data/*.parquet 파일을 읽기 때문).

실행 방법:
    1. marcap 저장소를 클론 (git clone https://github.com/HyeonSooJ/marcap.git)
    2. 이 파일을 marcap 저장소 최상위 폴더(marcap_utils.py와 같은 위치) 또는
       marcap/radar/ 폴더 밑에 저장 (이미 그 위치입니다)
    3. pip install pandas numpy pyarrow streamlit pykrx
    4. streamlit run screener_standalone.py   (marcap/radar 폴더 안에서 실행)
       또는 streamlit run radar/screener_standalone.py (marcap 폴더 안에서 실행)
"""

import glob
import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 1. marcap 데이터 로딩 (marcap_utils.py 이식)
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir():
    candidates = [
        os.path.join(_THIS_DIR, 'data'),
        os.path.join(_THIS_DIR, '..', 'data'),
        os.path.join(os.getcwd(), 'data'),
        os.path.join(os.getcwd(), 'marcap', 'data'),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and glob.glob(os.path.join(candidate, 'marcap-*.parquet')):
            return candidate
    raise FileNotFoundError(
        'marcap 데이터 디렉토리를 찾을 수 없습니다. 다음 경로를 확인했습니다: ' + ', '.join(candidates)
    )


def marcap_data(start, end=None, code=None, include_halted=False):
    """지정한 기간의 marcap 데이터를 가져온다."""
    start = pd.to_datetime(start)
    end = start if end is None else pd.to_datetime(end)
    data_dir = _data_dir()
    df_list = []
    for year in range(start.year, end.year + 1):
        try:
            parquet_file = os.path.join(data_dir, 'marcap-%s.parquet' % (year))
            df = pd.read_parquet(parquet_file)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            df_list.append(df)
        except Exception as e:
            print(e)
    df_merged = pd.concat(df_list)
    df_merged = df_merged[(start <= df_merged['Date']) & (df_merged['Date'] <= end)]
    df_merged = df_merged.sort_values(['Date', 'Rank'])
    if code:
        df_merged = df_merged[code == df_merged['Code']]
    df_merged.set_index('Date', inplace=True)
    if include_halted:
        return df_merged
    return df_merged[df_merged['Volume'] > 0]


# ---------------------------------------------------------------------------
# 2. 차트 패턴 정의 + 매칭 로직 (chart_pattern.py 이식)
# ---------------------------------------------------------------------------

N_POINTS = 20


def _keypoints_to_shape(keypoints, n_points=N_POINTS):
    xs, ys = zip(*keypoints)
    x_new = np.linspace(0, 1, n_points)
    return np.interp(x_new, xs, ys)


PATTERN_DEFINITIONS = {
    'uptrend': {
        'label': '① 우상향형',
        'shape': _keypoints_to_shape([(0, 0.0), (1, 1.0)]),
    },
    'range_v_rebound': {
        'label': '② 박스권 V자 반등형',
        'shape': _keypoints_to_shape([(0, 1.0), (0.15, 0.85), (0.55, 0.0), (0.85, 0.85), (1.0, 1.0)]),
    },
    'v_rebound_breakout': {
        'label': '③ V자 반등 후 상승돌파형',
        'shape': _keypoints_to_shape([(0, 0.4), (0.2, 0.3), (0.55, 0.0), (0.75, 0.4), (1.0, 1.0)]),
    },
    'sideways_breakout': {
        'label': '횡보 후 급등형',
        'shape': _keypoints_to_shape([(0, 0.05), (0.4, 0.1), (0.75, 0.05), (0.8, 0.1), (1.0, 1.0)]),
    },
    'trading_halt': {
        'label': '④ 거래정지 종목',
        'shape': None,
    },
    'rally_pullback': {
        'label': '급등 후 눌림목형',
        'shape': _keypoints_to_shape([(0, 0.2), (0.55, 1.0), (1.0, 0.0)]),
    },
    'today_momentum': {
        'label': '오늘 상한가 + 모양 필터',
        'shape': None,
    },
    'bottom_rebound': {
        'label': '바닥 찍고 연속 반등형',
        'shape': None,
    },
    'sustained_volume': {
        'label': '상한가 후 거래량 지속형',
        'shape': None,
    },
    'recent_pullback': {
        'label': '최근 눌림목 후 재상승형',
        'shape': None,
    },
    # 아래 2개는 "종류가 너무 많다"는 요청으로, 위 6개(sideways_breakout/
    # rally_pullback/bottom_rebound/today_momentum/sustained_volume/recent_pullback
    # 중 성격이 비슷한 것끼리) 묶어 메뉴에는 이 2개만 노출한다(MENU_PATTERN_KEYS).
    # 원본 6개 함수는 그대로 두고, find_presurge_pattern_stocks/
    # find_limitup_continuation_stocks가 각각을 호출해 결과를 합친다.
    'presurge_pattern': {
        'label': '⑤ 급등 전조 패턴형',
        'shape': None,
    },
    'limitup_continuation': {
        'label': '⑥ 상한가 지속형',
        'shape': None,
    },
}

MENU_PATTERN_KEYS = [
    'uptrend', 'range_v_rebound', 'v_rebound_breakout', 'trading_halt',
    'presurge_pattern', 'limitup_continuation',
]
PRESURGE_PATTERN_KEY = 'presurge_pattern'
LIMITUP_CONTINUATION_KEY = 'limitup_continuation'

# ⑤⑥ 두 메뉴는 "급등주 찾기"가 목적이라 다른 메뉴(①~④)보다 넓은 종목군을 봐야
# 한다. 실제 사례(2026-09-04 급등: TPC로보틱스/E8/KS인더스트리/원익홀딩스)를
# 검증해보니 E8(시총 87억)·KS인더스트리(시총 83억)는 시총 순위 2000위 밖이라
# 애초에 검색 대상에도 못 들어가고 있었다. 관리종목/투자주의환기종목 등 KRX
# 공식 위험 지정 종목도 급등주에 자주 등장해서(E8=관리종목, KS인더스트리=
# 투자주의환기종목) 제외하지 않고 대신 결과 표에 위험 표시를 단다.
SURGE_TOP_MARCAP_N = 3000
SURGE_MIN_MARCAP = 5_000_000_000
SURGE_MIN_RECENT_AMOUNT = 100_000_000
RISK_DEPT_KEYWORDS = ['관리종목', '투자주의환기종목', '투자경고종목', '투자위험종목', '거래정지']

RECENT_PULLBACK_PATTERN_KEY = 'recent_pullback'
RECENT_PULLBACK_LOOKBACK_DAYS = 6
RECENT_PULLBACK_MIN_PRIOR_RISE = 13.0
RECENT_PULLBACK_MIN_PULLBACK = 3.0
RECENT_PULLBACK_MAX_PULLBACK = 40.0
RECENT_PULLBACK_TOP_N = 100

HALT_PATTERN_KEY = 'trading_halt'
RALLY_PULLBACK_PATTERN_KEY = 'rally_pullback'
TODAY_MOMENTUM_PATTERN_KEY = 'today_momentum'
TODAY_MOMENTUM_LOOKBACK_MONTHS = 2
TODAY_MOMENTUM_MIN_SCORE4 = 0.6
TODAY_MOMENTUM_MIN_SCORE6 = 0.5
BOTTOM_REBOUND_PATTERN_KEY = 'bottom_rebound'
BOTTOM_REBOUND_TOP_N = 100
BOTTOM_REBOUND_SEARCH_WINDOW_FRACTION = 0.4
BOTTOM_REBOUND_MIN_PRE_DECLINE = 30.0
BOTTOM_REBOUND_MIN_RISE = 15.0
BOTTOM_REBOUND_MIN_MARCAP = 30_000_000_000
BOTTOM_REBOUND_MIN_RECENT_AMOUNT = 1_000_000_000
SUSTAINED_VOLUME_PATTERN_KEY = 'sustained_volume'
SUSTAINED_VOLUME_TOP_N = 50
SUSTAINED_VOLUME_LOOKBACK_DAYS = 10
SUSTAINED_VOLUME_CONFIRM_DAYS = 3
SUSTAINED_VOLUME_MIN_RATIO = 1.5
BREAKOUT_PATTERN_KEY = 'sideways_breakout'
BREAKOUT_RECENT_MONTHS = 1
BREAKOUT_TOP_N = 100
BREAKOUT_MIN_MARCAP = 30_000_000_000         # 시가총액 300억원 미만 제외
BREAKOUT_MIN_RECENT_AMOUNT = 1_000_000_000   # 최근 1개월 평균 거래대금 10억원 미만 제외
TOP_MARCAP_N = 2000
LIMIT_UP_MIN, LIMIT_UP_MAX = 29.0, 30.5


def resolve_date_range(end_date, months):
    """선택한 종료일 + 개월 수로 조회 시작일을 계산한다 (달력 개월 기준)."""
    end_date = pd.to_datetime(end_date)
    start_date = end_date - pd.DateOffset(months=months)
    return start_date, end_date


def filter_single_stocks(df):
    """국내 보통주 단일종목만 남긴다 (우선주/스팩/리츠/코넥스 제외)."""
    mask = (
        df['Market'].isin(['KOSPI', 'KOSDAQ', 'KOSDAQ GLOBAL'])
        & df['Code'].str.endswith('0')
        & ~df['Dept'].str.contains('SPAC', na=False)
        & ~df['Name'].str.contains('스팩|리츠', na=False)
    )
    return df[mask]


def filter_top_marcap(df, top_n=TOP_MARCAP_N):
    """조회 기간 마지막 거래일 기준 시가총액 상위 top_n 종목만 남긴다."""
    if df.empty:
        return df
    last_date = df.index.max()
    snapshot = df[df.index == last_date]
    top_codes = set(snapshot.loc[snapshot['Rank'] <= top_n, 'Code'])
    return df[df['Code'].isin(top_codes)]


def _resample_normalize(values, n_points=N_POINTS):
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
    """"횡보 후 급등"의 상승 폭(%). 최근 1개월 내 고점 + 최소 시총/거래대금 조건."""
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


def find_matching_stocks(price_df, pattern_key, top_n=None, min_coverage=0.6, min_marcap=None, min_amount=None):
    """기간 내 종가 흐름이 지정한 차트 패턴과 가장 비슷한 종목을 찾는다."""
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
            breakout_return = _breakout_surge(group, window_end, min_marcap=min_marcap, min_amount=min_amount)
            if breakout_return is None:
                continue
        last_row = group.iloc[-1]
        row = {
            'Code': code, 'Name': last_row['Name'], 'Close': last_row['Close'],
            'Marcap': last_row['Marcap'], 'Score': score,
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
    return result.sort_values('Score', ascending=False).head(top_n).reset_index(drop=True)


def find_halted_stocks(price_df, top_n=100):
    """조회 종료일 기준 거래정지 중인 종목을 찾는다."""
    rows = []
    for code, group in price_df.groupby('Code', sort=False):
        group = group.sort_index()
        last_row = group.iloc[-1]
        if last_row['Volume'] != 0:
            continue
        halted = (group['Volume'] == 0).values
        streak = 0
        for v in halted[::-1]:
            if not v:
                break
            streak += 1
        halt_start_date = group.index[-streak]
        rows.append({
            'Code': code, 'Name': last_row['Name'], 'Close': last_row['Close'],
            'Marcap': last_row['Marcap'], 'HaltStartDate': halt_start_date, 'HaltDays': streak,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'HaltStartDate', 'HaltDays']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return result.sort_values('HaltStartDate', ascending=False).head(top_n).reset_index(drop=True)


def find_today_momentum_stocks(price_df, top_n=50):
    """조회 종료일에 실제로 상한가를 기록한 종목 중, 최근 흐름이 ④ 또는 ⑥ 모양과
    비슷한 것만 걸러 보여준다 ("오늘 이미 상한가 간 종목 중 내일도 이어질 가능성이
    좀 더 높은 것"을 거르는 용도. "조용한 종목이 내일 터질지" 예측이 아님)."""
    columns = ['Code', 'Name', 'Close', 'Marcap', 'Score4', 'Score6', 'MatchedPattern']
    if price_df.empty:
        return pd.DataFrame(columns=columns)
    window_end = price_df.index.max()
    today_df = price_df[price_df.index == window_end]
    today_limitup = today_df[(today_df['ChangesRatio'] >= LIMIT_UP_MIN) & (today_df['ChangesRatio'] <= LIMIT_UP_MAX)]
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
            'Code': code, 'Name': today_row['Name'], 'Close': today_row['Close'],
            'Marcap': today_row['Marcap'], 'Score4': s4, 'Score6': s6,
            'MatchedPattern': '④' if s4 >= s6 else '⑥', 'BestScore': max(s4, s6),
        })

    result = pd.DataFrame(rows, columns=columns + ['BestScore'])
    if result.empty:
        return result[columns]
    return result.sort_values('BestScore', ascending=False).head(top_n).reset_index(drop=True)[columns]


def _bottom_rebound_metrics(
    group, search_window_fraction=BOTTOM_REBOUND_SEARCH_WINDOW_FRACTION,
    min_marcap=BOTTOM_REBOUND_MIN_MARCAP, min_amount=BOTTOM_REBOUND_MIN_RECENT_AMOUNT,
):
    """"바닥 찍고 연속 반등"의 저점 대비 반등률(%). 조건 미달이면 None."""
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
        return None
    low_val = closes[low_idx]
    if low_val <= 0:
        return None
    pre_low = closes[:low_idx + 1]
    period_high = pre_low.max()
    if period_high <= 0:
        return None
    pre_decline_pct = (low_val / period_high - 1) * 100
    if pre_decline_pct > -BOTTOM_REBOUND_MIN_PRE_DECLINE:
        return None
    current_val = closes[-1]
    rise_pct = (current_val / low_val - 1) * 100
    if rise_pct < BOTTOM_REBOUND_MIN_RISE:
        return None
    return rise_pct


def find_bottom_rebound_stocks(price_df, top_n=None, min_marcap=None, min_amount=None):
    """장기 하락 후 저점을 찍고 반등 중인 종목을 찾는다."""
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
            'Code': code, 'Name': last_row['Name'], 'Close': last_row['Close'],
            'Marcap': last_row['Marcap'], 'ReboundReturn': rise_pct,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'ReboundReturn']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return result.sort_values('ReboundReturn', ascending=False).head(top_n).reset_index(drop=True)


def _recent_pullback_metrics(
    group, lookback_days=RECENT_PULLBACK_LOOKBACK_DAYS,
    min_prior_rise=RECENT_PULLBACK_MIN_PRIOR_RISE, min_pullback=RECENT_PULLBACK_MIN_PULLBACK,
    max_pullback=RECENT_PULLBACK_MAX_PULLBACK, min_marcap=SURGE_MIN_MARCAP, min_amount=SURGE_MIN_RECENT_AMOUNT,
):
    """최근 lookback_days(기본 6거래일) 안에서 "짧게 오르고 - 살짝 눌리고 - 아직
    저점보다는 높은 채로 마감"인 종목의 (PriorRise%, Pullback%)을 계산한다.
    조건 미달이면 None. 전체 기간 모양 비교로는 안 잡히는 짧은 며칠짜리 등락을
    따로 본다(2026-09-04 실제 급등주 TPC로보틱스/E8 사례로 확인)."""
    if len(group) < lookback_days + 5:
        return None
    if group['Marcap'].iloc[-1] < min_marcap:
        return None
    if group['Amount'].tail(20).mean() < min_amount:
        return None
    closes = group['Close'].values[-lookback_days:]
    peak_idx = int(np.argmax(closes))
    if peak_idx == len(closes) - 1:
        return None
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
        return None
    pullback = (peak_val - current) / peak_val * 100
    if pullback < min_pullback or pullback > max_pullback:
        return None
    return prior_rise, pullback


def find_recent_pullback_stocks(price_df, top_n=None, min_marcap=None, min_amount=None):
    """최근 며칠간 짧게 오른 뒤 살짝 눌리고 있는(=재상승 대기 중일 수 있는) 종목을 찾는다."""
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
            'Code': code, 'Name': last_row['Name'], 'Close': last_row['Close'],
            'Marcap': last_row['Marcap'], 'PriorRise': prior_rise, 'Pullback': pullback,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'PriorRise', 'Pullback']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return result.sort_values('Pullback', ascending=True).head(top_n).reset_index(drop=True)


def _sustained_volume_metrics(group):
    """가장 최근 상한가 후 CONFIRM_DAYS일째 거래량이 상한가 당일 대비 얼마나
    남아있는지(비율). 조건 미달이면 None."""
    n = len(group)
    if n < SUSTAINED_VOLUME_LOOKBACK_DAYS + SUSTAINED_VOLUME_CONFIRM_DAYS + 1:
        return None
    chg = group['ChangesRatio'].values
    vol = group['Volume'].values
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
    ratio = vol[spike_idx + SUSTAINED_VOLUME_CONFIRM_DAYS] / spike_vol
    if ratio < SUSTAINED_VOLUME_MIN_RATIO:
        return None
    return ratio


def find_sustained_volume_stocks(price_df, top_n=None):
    """최근 상한가를 기록했고 그 이후 거래량이 계속 유지되는 종목을 찾는다."""
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
            'Code': code, 'Name': last_row['Name'], 'Close': last_row['Close'],
            'Marcap': last_row['Marcap'], 'VolumeRatio': ratio,
        })
    columns = ['Code', 'Name', 'Close', 'Marcap', 'VolumeRatio']
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return result.sort_values('VolumeRatio', ascending=False).head(top_n).reset_index(drop=True)


def _dept_risk_label(dept):
    """Dept 값에 KRX 공식 위험 지정 키워드가 있으면 그 키워드를, 없으면 None을 반환한다."""
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
    Dept 값에서 관리종목/투자주의환기종목 등 위험 지정 여부를 뽑아온다."""
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
    """횡보 후 급등형 + 바닥 찍고 연속 반등형 + 최근 눌림목 후 재상승형 + 급등 후
    눌림목형을 합쳐서 보여준다("급등 전조 패턴형" — 아직 상한가가 확정되지 않은,
    모양만으로 추정하는 후보들). ④/⑧은 시가총액/거래대금 하한을 SURGE_MIN_MARCAP/
    SURGE_MIN_RECENT_AMOUNT로 낮춰서 호출한다."""
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
        (r_sideways, labels[BREAKOUT_PATTERN_KEY]['label']),
        (r_bottom, labels[BOTTOM_REBOUND_PATTERN_KEY]['label']),
        (r_recent, labels[RECENT_PULLBACK_PATTERN_KEY]['label']),
        (r_rally, labels[RALLY_PULLBACK_PATTERN_KEY]['label']),
    ], price_df)


def find_limitup_continuation_stocks(price_df, top_n=50):
    """오늘 상한가+모양 필터 + 상한가 후 거래량 지속형을 합쳐서 보여준다
    ("상한가 지속형" — 이미 상한가가 확정된 종목 중 내일 이어질 가능성이 높은 후보들)."""
    r_today = find_today_momentum_stocks(price_df, top_n=top_n)
    r_vol = find_sustained_volume_stocks(price_df, top_n=top_n)
    labels = PATTERN_DEFINITIONS
    return _combine_with_source_tag([
        (r_vol, labels[SUSTAINED_VOLUME_PATTERN_KEY]['label']),
        (r_today, labels[TODAY_MOMENTUM_PATTERN_KEY]['label']),
    ], price_df)


# ---------------------------------------------------------------------------
# 3. 업종/PER 조회 (sector_data.py 이식, pykrx 필요)
# ---------------------------------------------------------------------------

_SECTOR_CACHE_DIR = os.path.join(_THIS_DIR, 'output', 'sector_per_cache')
_SECTOR_CACHE_MAX_AGE_SEC = 24 * 3600


def get_sector_and_per(date, force_refresh=False):
    """지정일 기준 전종목 업종명/PER 테이블을 반환한다 (Code 인덱스, Sector/PER 컬럼)."""
    from pykrx import stock

    date_str = pd.to_datetime(date).strftime('%Y%m%d')
    trading_day = stock.get_nearest_business_day_in_a_week(date_str, prev=True)

    cache_file = os.path.join(_SECTOR_CACHE_DIR, f'{trading_day}.parquet')
    if not force_refresh and os.path.exists(cache_file):
        age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if age < _SECTOR_CACHE_MAX_AGE_SEC:
            return pd.read_parquet(cache_file)

    sector_frames = []
    for market in ('KOSPI', 'KOSDAQ'):
        sector_df = stock.get_market_sector_classifications(trading_day, market)
        if sector_df is not None and not sector_df.empty:
            sector_frames.append(sector_df[['업종명']])
    if not sector_frames:
        return pd.DataFrame(columns=['Sector', 'PER']).rename_axis('Code')
    sector = pd.concat(sector_frames)
    sector.index.name = 'Code'
    sector.columns = ['Sector']

    per = stock.get_market_fundamental(trading_day, market='ALL')[['PER']]
    per.index.name = 'Code'

    result = sector.join(per, how='left')
    os.makedirs(_SECTOR_CACHE_DIR, exist_ok=True)
    result.to_parquet(cache_file)
    return result


# ---------------------------------------------------------------------------
# 4. Streamlit 화면
# ---------------------------------------------------------------------------

st.set_page_config(page_title='주식 조건 검색 도구', page_icon='📐', layout='wide')
st.title('📐 차트 모양 조건검색')
st.markdown(
    '기준일과 조회 개월 수를 고르면 그 기간 동안의 종가 흐름을 3가지 차트 모양(①우상향 ②박스권 '
    'V자 반등 ③V자 반등 후 상승돌파)과 비교해 찾아줍니다. ④거래정지 종목은 모양 비교 대신 기준일 '
    '현재 거래정지 중인 종목을 그대로 찾아줍니다. ⑤급등 전조 패턴형과 ⑥상한가 지속형은 "급등주 '
    '찾기" 관련 세부 조건들을 성격별로 묶은 메뉴입니다 — ⑤는 아직 상한가가 확정되지 않은 종목 중 '
    '모양만으로 후보를 추정하고, ⑥은 이미 상한가를 기록한 종목 중 다음 상한가로 이어질 가능성이 '
    '상대적으로 높은 후보를 찾습니다(어떤 세부 조건에 걸렸는지는 결과 표의 "매칭된 세부 유형" '
    '칼럼에서 확인 가능). ①~④는 국내 보통주(우선주·스팩·리츠·코넥스 제외, 기준일 시가총액 상위 '
    '2,000 종목 이내)만 봅니다. ⑤⑥은 실제 급등주가 초소형주에서도 자주 나오는 게 확인돼('
    '2026-09-04 사례 검증) 시가총액 상위 3,000위까지 훨씬 넓게 보고, 관리종목·투자주의환기종목 '
    '같은 KRX 공식 위험 지정 종목도 제외하지 않는 대신 "위험 표시(KRX)" 칼럼에 ⚠️로 표시합니다. '
    '업종/PER은 KRX(pykrx)에서 별도로 조회하며, 조회에 실패하면 해당 칸이 비어있을 수 있습니다.'
)

col1, col2, col3 = st.columns(3)
end_date = col1.date_input(
    '① 기준일(종료일) 선택', value=datetime.today().date(),
    max_value=datetime.today().date(), key='pattern_end_date',
)
months = col2.selectbox('② 조회 개월 수', list(range(1, 13)), index=2, key='pattern_months')
pattern_key = col3.selectbox(
    '③ 차트 모양 선택', MENU_PATTERN_KEYS,
    format_func=lambda k: PATTERN_DEFINITIONS[k]['label'], key='pattern_key',
)

if st.button('④ 확인 — 종목 찾기', type='primary'):
    use_fixed_2m = pattern_key in (TODAY_MOMENTUM_PATTERN_KEY, LIMITUP_CONTINUATION_KEY)
    start, end = resolve_date_range(end_date, 2) if use_fixed_2m else resolve_date_range(end_date, months)
    with st.spinner('조건에 맞는 종목을 찾는 중...'):
        is_halt = pattern_key == HALT_PATTERN_KEY
        df = marcap_data(start, end, include_halted=is_halt)
        if df.empty:
            st.warning('해당 기간에 데이터가 없습니다.')
            st.session_state['pattern_result'] = None
        else:
            df = filter_single_stocks(df)
            is_surge_menu = pattern_key in (PRESURGE_PATTERN_KEY, LIMITUP_CONTINUATION_KEY)
            df = filter_top_marcap(df, top_n=SURGE_TOP_MARCAP_N) if is_surge_menu else filter_top_marcap(df)
            if is_halt:
                matched = find_halted_stocks(df)
            elif pattern_key == PRESURGE_PATTERN_KEY:
                matched = find_presurge_pattern_stocks(df)
            elif pattern_key == LIMITUP_CONTINUATION_KEY:
                matched = find_limitup_continuation_stocks(df)
            else:
                matched = find_matching_stocks(df, pattern_key)
            if matched.empty:
                st.session_state['pattern_result'] = matched
            else:
                try:
                    sector_per = get_sector_and_per(end)
                    matched = matched.join(sector_per, on='Code')
                except Exception as e:
                    st.warning(f'업종/PER 조회에 실패했습니다 (KRX 접속 불가 등): {e}')
                    matched['Sector'] = pd.NA
                    matched['PER'] = pd.NA
                st.session_state['pattern_result'] = matched
                st.session_state['pattern_range'] = (start, end)
                st.session_state['pattern_result_key'] = pattern_key
                matched_codes = set(matched['Code'])
                st.session_state['pattern_chart_df'] = (
                    df[df['Code'].isin(matched_codes)][['Code', 'Name', 'Close']].copy()
                )

matched = st.session_state.get('pattern_result')
if matched is None:
    pass
elif matched.empty:
    if st.session_state.get('pattern_result_key') == LIMITUP_CONTINUATION_KEY:
        st.info('선택하신 날짜(최근 2개월 기준) 안에 상한가를 기록한 종목이 없어서 결과가 없습니다. 다른 날짜로 다시 시도해보세요.')
    else:
        st.info('조건에 맞는 종목을 찾지 못했습니다.')
else:
    start, end = st.session_state['pattern_range']
    st.caption(f'{start.date()} ~ {end.date()} 기간, {len(matched)}개 종목 매칭')
    result_key = st.session_state.get('pattern_result_key')
    show_cols = ['Name', 'Close', 'Sector', 'Marcap', 'PER']
    if result_key == HALT_PATTERN_KEY:
        show_cols += ['HaltStartDate', 'HaltDays']
        st.caption(
            '④ 거래정지 종목은 조회 종료일 기준 거래정지 중인 종목입니다. 현재가는 정지 직전 마지막 '
            '체결가로 고정된 값이고, 정지 시작일이 조회 시작일과 같다면 실제로는 그보다 더 이전부터 '
            '정지 중이었을 수 있습니다(조회 범위 밖이라 정확한 시작일을 알 수 없음).'
        )
    elif result_key == PRESURGE_PATTERN_KEY:
        show_cols += ['MatchedPattern', 'Risk']
        st.caption(
            '⑤ 급등 전조 패턴형은 네 가지 하위 조건(횡보 후 급등형·바닥 찍고 연속 반등형·최근 '
            '눌림목 후 재상승형·급등 후 눌림목형)을 합쳐서 보여줍니다. "매칭된 세부 유형" 칼럼에서 '
            '어떤 조건에 걸렸는지 확인할 수 있고, 한 종목이 여러 조건에 동시에 해당하면 그중 하나만 '
            '표시됩니다. "최근 눌림목 후 재상승형"은 조회 기간 전체가 아니라 최근 6거래일만 보고 '
            '"짧게 오르고-살짝 눌리고-아직 저점보다는 높게 마감"인 종목을 찾습니다. 이 메뉴는 시총 '
            '상위 3000위·50억원 이상까지 넓게 보고(다른 메뉴보다 훨씬 완화됨), 관리종목·투자주의환기 '
            '종목 같은 KRX 위험 지정 종목도 "위험 표시(KRX)" 칼럼에 ⚠️로 표시한 채 포함합니다.'
        )
        st.warning(
            '⚠️ 네 조건 모두 2026년 데이터 워크포워드 백테스트로 검증했지만 결과가 엇갈립니다. '
            '**횡보 후 급등형**은 다음날 상한가 확률이 0.6%로 사실상 예측 불가능했고, 한 달 내로 '
            '넓히면 약 10%(무작위 5.2%)였습니다. **바닥 찍고 연속 반등형**은 다음날~한 달 내 상한가 '
            '확률이 23.1%로 무작위(2.7%) 대비 높았지만, 정작 매수 후 1개월 보유 수익률은 -17.0%로 '
            '무작위(-8.2%)보다 나빴습니다. **최근 눌림목 후 재상승형**은 다음날 재상한가 확률이 '
            '1.14%(무작위 0.47%, 약 2.4배), 5거래일 내로 넓히면 4.6%(무작위 1.7%, 약 2.8배)로 약한 '
            '수준이지만 꾸준한 신호가 확인됐습니다(2026년 4~9월, 105개 검증일 기준). **급등 후 '
            '눌림목형**은 1개월 보유 수익률이 -13.2%로 무작위(-15.7%)보다 근소하게 나은 수준에 '
            '그쳤습니다. 넷 다 상한가를 보장하지 않으며 특히 "매수 후 장기 보유"에는 적합하지 '
            '않으니 참고용으로만 활용하세요.'
        )
    elif result_key == LIMITUP_CONTINUATION_KEY:
        show_cols += ['MatchedPattern', 'Risk']
        st.caption(
            '⑥ 상한가 지속형은 두 가지 하위 조건(오늘 상한가+모양 필터·상한가 후 거래량 지속형)을 '
            '합쳐서 보여줍니다. 둘 다 "이미 상한가를 기록한 종목 중 다음 상한가로 이어질 가능성이 '
            '상대적으로 높은 것"을 찾는 용도라, 최근 상한가 종목이 없으면 결과가 비어있을 수 '
            '있습니다. ②개월수 선택과 무관하게 항상 최근 2개월 흐름으로 계산합니다. 이 메뉴도 ⑤와 '
            '동일하게 시총 상위 3000위까지 넓게 보며, KRX 위험 지정 종목도 "위험 표시(KRX)" 칼럼에 '
            '⚠️로 표시한 채 포함합니다.'
        )
        st.warning(
            '⚠️ "확률이 더 높다"는 뜻이지 보장이 아닙니다. **오늘 상한가+모양 필터**는 실제 상한가 '
            '647건 검증 결과 다음날도 상한가 갈 확률이 평균 16.7%였고, 최근 2개월 흐름이 특정 모양과 '
            '상관계수 0.5~0.6 이상이면 20.0~23.8%까지 올라갔습니다(여전히 대부분은 이어지지 않음). '
            '**상한가 후 거래량 지속형**은 실제 상한가 846건 검증 결과 상한가 3일 뒤 거래량이 1.5배 '
            '이상 유지되면 2~7일 내 재상한가 확률이 31.7%로 전체 평균(17.4%)의 약 1.8배였습니다. '
            '두 조건 모두 투자 조언이 아닌 참고 자료입니다.'
        )

    col_labels = {
        'Name': '종목명', 'Close': '현재가', 'Sector': '분야(업종)', 'Marcap': '시가총액(백만원)',
        'PER': 'PER', 'HaltStartDate': '거래정지 시작일', 'HaltDays': '정지 영업일수',
        'MatchedPattern': '매칭된 세부 유형', 'Risk': '위험 표시(KRX)',
    }
    display_matched = matched[show_cols].copy()
    display_matched['Close'] = display_matched['Close'].apply(lambda v: f'{v:,.0f}' if pd.notna(v) else v)
    display_matched['Marcap'] = display_matched['Marcap'].apply(
        lambda v: f'{v / 1e8:,.0f}억' if pd.notna(v) else v,
    )
    if 'HaltStartDate' in display_matched.columns:
        display_matched['HaltStartDate'] = display_matched['HaltStartDate'].dt.strftime('%Y-%m-%d')
    if 'Risk' in display_matched.columns:
        display_matched['Risk'] = display_matched['Risk'].apply(lambda v: f'⚠️ {v}' if pd.notna(v) else '')
    display_matched = display_matched.rename(columns=col_labels)

    display_matched['실시간 차트'] = 'https://finance.naver.com/item/main.naver?code=' + matched['Code']
    st.dataframe(
        display_matched, use_container_width=True, hide_index=True,
        column_config={
            '실시간 차트': st.column_config.LinkColumn('실시간 차트', display_text='📈 네이버에서 보기(실시간)'),
        },
    )

    st.divider()
    st.markdown('#### 📊 조회 기간 기준 차트')
    chart_df = st.session_state.get('pattern_chart_df')
    if chart_df is not None and not chart_df.empty:
        pick_options = matched[['Code', 'Name']].drop_duplicates().reset_index(drop=True)
        pick_labels = [f"{r['Name']} ({r['Code']})" for _, r in pick_options.iterrows()]
        picked_label = st.selectbox('종목 선택', pick_labels, key='pattern_chart_pick')
        picked_code = pick_options.iloc[pick_labels.index(picked_label)]['Code']
        series = chart_df[chart_df['Code'] == picked_code].sort_index()['Close']
        st.line_chart(series)
        st.caption(f'{start.date()} ~ {end.date()} 기간의 종가만 표시합니다 (오늘 날짜 데이터 아님).')
