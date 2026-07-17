# -*- coding: utf-8 -*-
"""marcap 일별 데이터 기반 통계적 이상변동 탐지.

거래량, 등락률, 시가총액 변화율, 시총순위 변동을 종목별 롤링 z-score로 계산해
이상신호를 스코어링한다. 또한 marcap 데이터의 Dept 컬럼(관리종목/투자주의환기종목
지정 이력)을 이용해 "공식 위험 지정보다 며칠 앞서 탐지할 수 있는가"를 검증하는
백테스트 함수를 제공한다.
"""

import numpy as np
import pandas as pd

RISK_DEPTS = {'관리종목(소속부없음)', '투자주의환기종목(소속부없음)'}

Z_COLUMNS = ['VolumeZ', 'ChangesRatioZ', 'MarcapReturnZ', 'RankChangeZ']


def _zscore(series, window=60, min_periods=20):
    roll_mean = series.rolling(window, min_periods=min_periods).mean()
    roll_std = series.rolling(window, min_periods=min_periods).std()
    return (series - roll_mean) / roll_std.replace(0, np.nan)


def compute_features(df):
    """종목(Code)별로 정렬 후 롤링 z-score 피처를 계산해 붙인다.

    groupby().transform()으로 종목별 롤링 계산을 벡터화한다(종목 수만큼 Python
    루프를 도는 대신 pandas가 내부적으로 그룹별 계산을 수행).

    :param df: marcap_data()로 불러온 DataFrame (DatetimeIndex, Code/Volume/
        ChangesRatio/Marcap/Rank 컬럼 포함)
    :return: 피처가 추가된 DataFrame
    """
    df = df.sort_index().copy()
    grouped = df.groupby('Code', sort=False)
    df['VolumeZ'] = grouped['Volume'].transform(_zscore)
    df['ChangesRatioZ'] = grouped['ChangesRatio'].transform(lambda s: _zscore(s.abs()))
    df['MarcapReturn'] = grouped['Marcap'].pct_change()
    df['MarcapReturnZ'] = df.groupby('Code', sort=False)['MarcapReturn'].transform(_zscore)
    df['RankChange'] = grouped['Rank'].diff().abs()
    df['RankChangeZ'] = df.groupby('Code', sort=False)['RankChange'].transform(_zscore)
    return df


def score_anomaly(df):
    """종합 이상점수(AnomalyScore)와 주요 원인(AnomalyReason)을 계산한다."""
    feat = compute_features(df)
    scores = feat[Z_COLUMNS]
    feat['AnomalyScore'] = scores.max(axis=1)
    feat['AnomalyReason'] = pd.NA
    valid = feat['AnomalyScore'].notna()
    feat.loc[valid, 'AnomalyReason'] = scores.loc[valid].idxmax(axis=1)
    return feat


def detect_anomalies(df, date=None, threshold=3.0, top_n=10):
    """특정 날짜의 이상신호 상위 top_n 종목을 반환한다.

    :param date: 조회 날짜. None이면 데이터 내 최신 날짜 사용
    :param threshold: 이상신호로 판단할 z-score 임계값
    :param top_n: 반환할 최대 종목 수
    """
    feat = score_anomaly(df)
    date = feat.index.max() if date is None else pd.to_datetime(date)
    day = feat.loc[feat.index == date]
    day = day[day['AnomalyScore'] >= threshold]
    day = day.sort_values('AnomalyScore', ascending=False).head(top_n)
    cols = ['Code', 'Name', 'Close', 'ChangesRatio', 'Volume', 'Marcap', 'Rank',
            'Dept', 'AnomalyScore', 'AnomalyReason'] + Z_COLUMNS
    return day[cols]


def label_dept_events(df):
    """Dept가 위험구분(관리종목/투자주의환기종목)으로 신규 진입한 이벤트 목록.

    :return: columns=[Code, Name, EventDate, Dept]
    """
    events = []
    for code, g in df.groupby('Code', sort=False):
        g = g.sort_index()
        is_risk = g['Dept'].isin(RISK_DEPTS)
        newly_risk = is_risk & (~is_risk.shift(1, fill_value=False))
        idx = np.where(newly_risk.to_numpy())[0]
        for i in idx:
            events.append({
                'Code': code,
                'Name': g['Name'].iloc[i],
                'EventDate': g.index[i],
                'Dept': g['Dept'].iloc[i],
            })
    return pd.DataFrame(events, columns=['Code', 'Name', 'EventDate', 'Dept'])


def backtest_early_warning(df, lookback_days=20, threshold=3.0):
    """위험 지정 이벤트 대비 조기탐지 리드타임을 백테스트한다.

    각 이벤트에 대해 지정일 이전 lookback_days 영업일 구간에서 AnomalyScore가
    threshold를 최초로 넘긴 시점을 찾아, 공식 지정일 대비 며칠 앞서
    탐지했는지(영업일 기준) 집계한다.

    :return: (이벤트별 결과 DataFrame, 요약 dict)
    """
    feat = score_anomaly(df)
    events = label_dept_events(df)

    results = []
    for _, ev in events.iterrows():
        code, event_date = ev['Code'], ev['EventDate']
        hist = feat[(feat['Code'] == code) & (feat.index < event_date)].sort_index().tail(lookback_days)
        flagged = hist[hist['AnomalyScore'] >= threshold]
        if len(flagged) > 0:
            first_flag_date = flagged.index.min()
            lead_days = len(hist.loc[first_flag_date:])
            results.append({
                'Code': code, 'Name': ev['Name'], 'EventDate': event_date,
                'Detected': True, 'FirstFlagDate': first_flag_date,
                'LeadDaysApprox': lead_days,
            })
        else:
            results.append({
                'Code': code, 'Name': ev['Name'], 'EventDate': event_date,
                'Detected': False, 'FirstFlagDate': pd.NaT, 'LeadDaysApprox': np.nan,
            })

    result_df = pd.DataFrame(results)
    n_events = len(result_df)
    coverage = float(result_df['Detected'].mean()) if n_events else 0.0
    detected = result_df.loc[result_df['Detected'], 'LeadDaysApprox']
    avg_lead = float(detected.mean()) if len(detected) else 0.0
    summary = {
        'n_events': n_events,
        'coverage': coverage,
        'avg_lead_days': avg_lead,
        'threshold': threshold,
        'lookback_days': lookback_days,
    }
    return result_df, summary
