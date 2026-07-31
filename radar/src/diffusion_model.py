# -*- coding: utf-8 -*-
"""marcap 거래대금/시총 데이터와 네이버 데이터랩 검색량을 결합해 종목별 "시장 관심"을
감염병 확산모델(SIR)의 실효재생산수(Rt) 개념으로 진단한다.

핵심 아이디어
-------------
종목에 대한 시장 관심을 감염병의 "감염(Infected)" 규모로 보고, 관심도의 순간
증가율로부터 역학에서 쓰는 실효재생산수 Rt(감염자 1명이 만들어내는 평균 2차
감염자 수)를 근사 추정한다. 지수증가 모델 I(t) ≈ I(0)*exp(r·t)에서 성장률 r을
롤링 구간 로그선형회귀로 추정하고, 세대기간(generation_time)을 가정해
Rt = exp(r · generation_time) 로 환산한다(역학의 renewal-equation 근사와 같은
발상). Rt와 관심도의 최근 고점 대비 위치를 함께 보고 4단계로 분류한다:
평시 / 초기 확산기(Rt≥임계) / 포화기(Rt≈1, 고점 근접) / 정점 지나 하락기(Rt≤임계).

한계 (반드시 결과와 함께 표기)
------------------------------
실제 역학모델처럼 S(감수성)·R(회복) 인구를 직접 관측하는 게 아니라, I(관심도)의
성장률만으로 Rt를 "역산"하는 근사치다. generation_time은 실증적으로 추정한 값이
아니라 모델링 가정(기본 3영업일)이며, threshold(1.15/0.85)도 튜닝 가능한 값이다.

관심도(Attention)를 롤링 min-max로 정규화하기 때문에 "상대적 성장/둔화"에는
민감하지만 "절대적으로 이례적인 수준인가"는 구분하지 못한다. 실제로 평범한
대형주(삼성전자, 2024~2026)로 검증한 결과 하루의 73%가 확산 신호로 오탐될 만큼
민감했다. 그래서 diagnose_stage()/diagnose()를 아무 종목에나 매일 돌리지 말고,
diagnose_flagged_stocks()로 anomaly_detector의 통계적 이상탐지를 먼저 통과한
(절대적으로 이례적인) 종목에만 적용해야 한다.

거래대금 회전율은 그 자체로 방향(매수 vs 매도)을 모른다 — 초기 버전은 순방향
수익률 백테스트(2023년 이차전지 랠리+붕괴 구간)에서 "초기 확산기"로 진단된
종목들의 이후 수익률이 오히려 마이너스로 나오는 문제가 있었는데, 원인은 폭락일의
패닉 매도 거래량까지 "관심 급증"으로 세고 있었기 때문이었다. 그래서 compute_
attention_index()는 하락일(ChangesRatio<0)의 거래대금은 관심 지수에서 0으로
처리해 매수세 유입만 "확산"으로 카운트한다.
"""

import numpy as np
import pandas as pd

from . import anomaly_detector
from .search_trend_collector import get_search_trend

DEFAULT_GROWTH_WINDOW = 5      # 성장률 r(t) 추정에 쓰는 롤링 구간(영업일)
DEFAULT_GENERATION_DAYS = 3    # 세대기간 가정(영업일) — 실증값 아닌 모델링 가정
DEFAULT_PEAK_WINDOW = 20       # "최근 고점" 판단에 쓰는 롤링 구간(영업일)
DEFAULT_GROWTH_THRESHOLD = 1.15
DEFAULT_DECLINE_THRESHOLD = 0.85
DEFAULT_NEAR_PEAK_RATIO = 0.9

STAGE_BASELINE = '평시'
STAGE_GROWTH = '초기 확산기'
STAGE_SATURATION = '포화기'
STAGE_DECLINE = '정점 지나 하락기'


def _minmax_rolling(series, window=60, min_periods=20):
    roll_min = series.rolling(window, min_periods=min_periods).min()
    roll_max = series.rolling(window, min_periods=min_periods).max()
    span = (roll_max - roll_min).replace(0, np.nan)
    return ((series - roll_min) / span).clip(0, 1)


def compute_attention_index(marcap_df, search_trend_df=None, turnover_weight=0.5, search_weight=0.5):
    """단일 종목의 marcap 시계열(+ 선택적 검색량 시계열)을 결합해 일별 관심도 지수 I(t)를 만든다.

    :param marcap_df: marcap_data(code=...)로 불러온 단일 종목 DataFrame (DatetimeIndex,
        Amount/Marcap 컬럼 포함)
    :param search_trend_df: search_trend_collector.get_search_trend() 결과 (선택). 주어지면
        거래대금 회전율과 절반씩 섞고, 없으면 거래대금 회전율만 사용한다.
    :return: DataFrame, 컬럼=['Attention'] (0~1 정규화), marcap_df와 동일 DatetimeIndex
    """
    df = marcap_df.sort_index()
    # 거래대금/시가총액 = 회전율. 절대 거래대금보다 종목 규모(대형주 vs 소형주) 편향이 적다.
    turnover = (df['Amount'] / df['Marcap']).replace([np.inf, -np.inf], np.nan)
    # 하락일(패닉 매도)의 거래대금은 "확산(관심 유입)"으로 세지 않는다 — 회전율 자체는
    # 방향을 모르기 때문에, 이 처리 없이는 폭락으로 인한 거래량 급증도 매수세 급증과
    # 똑같이 "초기 확산기"로 오판한다(2023년 이차전지 붕괴 구간 백테스트에서 실제로
    # 확인된 문제 — 상세는 모듈 상단 "한계" 참고).
    buy_side_turnover = turnover.where(df['ChangesRatio'] >= 0, 0.0)
    turnover_norm = _minmax_rolling(buy_side_turnover).fillna(0)

    if search_trend_df is not None and not search_trend_df.empty:
        search_norm = (search_trend_df['ratio'].reindex(df.index).ffill() / 100.0).fillna(0)
        attention = turnover_weight * turnover_norm + search_weight * search_norm
    else:
        attention = turnover_norm

    return pd.DataFrame({'Attention': attention})


def estimate_growth_rate(attention, window=DEFAULT_GROWTH_WINDOW):
    """관심도 로그값의 롤링 선형회귀 기울기로 순간 성장률 r(t)를 추정한다."""
    log_attn = np.log(attention.clip(lower=1e-4))
    x = np.arange(window)

    def _slope(y):
        if np.isnan(y).any():
            return np.nan
        return np.polyfit(x, y, 1)[0]

    return log_attn.rolling(window).apply(_slope, raw=True)


def estimate_rt(attention, window=DEFAULT_GROWTH_WINDOW, generation_days=DEFAULT_GENERATION_DAYS):
    """성장률 r(t)를 역학의 실효재생산수 Rt = exp(r · generation_time)로 환산한다."""
    r = estimate_growth_rate(attention, window=window)
    return np.exp(r * generation_days)


def diagnose_stage(attention, rt, peak_window=DEFAULT_PEAK_WINDOW,
                    growth_threshold=DEFAULT_GROWTH_THRESHOLD,
                    decline_threshold=DEFAULT_DECLINE_THRESHOLD,
                    near_peak_ratio=DEFAULT_NEAR_PEAK_RATIO):
    """Rt와 최근 고점 대비 위치를 결합해 확산 단계를 4단계로 분류한다.

    우선순위: 결측 > 하락(Rt<=decline) > 확산(Rt>=growth) > 포화(고점 근접) > 평시.
    :return: pd.Series(문자열 라벨, object dtype), attention과 동일 인덱스
    """
    rolling_peak = attention.rolling(peak_window, min_periods=1).max()
    near_peak = attention >= rolling_peak * near_peak_ratio

    # 낮은 우선순위 -> 높은 우선순위 순으로 덮어쓴다: 평시 -> 포화 -> 확산 -> 하락 -> 결측
    stage = pd.Series(STAGE_BASELINE, index=attention.index, dtype=object)
    stage[near_peak.fillna(False)] = STAGE_SATURATION
    stage[rt >= growth_threshold] = STAGE_GROWTH
    stage[rt <= decline_threshold] = STAGE_DECLINE
    stage[rt.isna()] = np.nan
    stage.name = 'Stage'
    return stage


def diagnose(code, marcap_df, search_trend_df=None, **kwargs):
    """종목 하나에 대한 전체 진단 파이프라인. 전체 시계열 + 최신일 요약을 반환한다.

    :param marcap_df: 해당 code로 필터링된 marcap DataFrame (marcap_data(code=code) 결과)
    :param search_trend_df: search_trend_collector.get_search_trend() 결과 (선택)
    :return: (전체 시계열 DataFrame, 최신일 요약 dict 또는 진단 불가 시 None)
    """
    attn_df = compute_attention_index(marcap_df, search_trend_df, **kwargs)
    attn_df['GrowthRate'] = estimate_growth_rate(attn_df['Attention'])
    attn_df['Rt'] = estimate_rt(attn_df['Attention'])
    attn_df['Stage'] = diagnose_stage(attn_df['Attention'], attn_df['Rt'])

    valid = attn_df.dropna(subset=['Rt'])
    if valid.empty:
        return attn_df, None

    latest = valid.iloc[-1]
    summary = {
        'Code': code,
        'Date': valid.index[-1],
        'Attention': float(latest['Attention']),
        'GrowthRate': float(latest['GrowthRate']),
        'Rt': float(latest['Rt']),
        'Stage': latest['Stage'],
    }
    return attn_df, summary


def diagnose_flagged_stocks(df, date=None, threshold=3.0, top_n=10):
    """anomaly_detector로 1차 스크리닝된 이상신호 종목에 대해서만 SIR 확산 단계를 진단한다.

    diagnose()를 아무 종목에나 매일 적용하면 절대적 수준 판단 없이 상대적 성장률만
    보기 때문에 평범한 종목도 자주 오탐된다(모듈 상단 "한계" 참고). anomaly_detector의
    z-score 기반 이상탐지(절대적으로 이례적인 종목만 통과)로 먼저 후보를 좁힌 뒤에만
    SIR 진단을 적용해 오탐을 줄이고, 종목당 1회씩만 나가는 데이터랩 API 호출량도
    top_n으로 제한한다.

    :param df: marcap_data(start, end, include_halted=True)로 불러온 다종목 히스토리
        (diagnose()에 필요한 lookback 구간을 포함해야 함)
    :param date: 진단 기준일 (None이면 df 내 최신일)
    :param threshold, top_n: anomaly_detector.detect_anomalies()에 그대로 전달
    :return: DataFrame — anomaly_detector 결과 컬럼 + [Attention, GrowthRate, Rt, Stage]
    """
    anomalies = anomaly_detector.detect_anomalies(df, date=date, threshold=threshold, top_n=top_n)
    if anomalies.empty:
        return anomalies.assign(Attention=[], GrowthRate=[], Rt=[], Stage=[])

    start = df.index.min().strftime('%Y-%m-%d')
    end = df.index.max().strftime('%Y-%m-%d')

    rows = []
    for _, row in anomalies.iterrows():
        code, name = row['Code'], row['Name']
        stock_df = df[df['Code'] == code]
        try:
            search_df = get_search_trend(name, start, end)
        except Exception as e:
            print(f'  [경고] 검색량 조회 실패 ({name}): {e}')
            search_df = None

        _, summary = diagnose(code, stock_df, search_df)
        merged = row.to_dict()
        for key in ('Attention', 'GrowthRate', 'Rt', 'Stage'):
            merged[key] = summary[key] if summary else None
        rows.append(merged)

    return pd.DataFrame(rows)
