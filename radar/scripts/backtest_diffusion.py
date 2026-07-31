# -*- coding: utf-8 -*-
"""SIR 확산 진단(diffusion_model)의 예측력을 marcap 과거 데이터로 백테스트한다.

검증 방법
---------
"밈스탁 버블 정점"에는 anomaly_detector의 관리종목 지정 이벤트 같은 공식 라벨이
없다. 그래서 여기서는 이상신호가 뜬 날마다 diffusion_model의 확산 단계(Stage)를
진단하고, 그 날짜 이후 N영업일 순방향 수익률을 단계별로 비교하는 방식으로 검증한다.
모델에 실제 신호가 있다면 "초기 확산기"로 진단된 날 이후 수익률이 "정점 지나
하락기"로 진단된 날 이후 수익률보다 평균적으로 높아야 한다.

API 호출 비용: 종목별 검색량은 날짜 하나하나가 아니라 전체 백테스트 구간을
한 번에 조회하므로, 데이터랩 API 호출 횟수는 "이상신호가 뜬 날 수"가 아니라
"이상신호가 뜬 고유 종목 수"에 비례한다.

사용법:
    python radar/scripts/backtest_diffusion.py --start 2023-01-01 --end 2024-12-31 --top-n 5
"""

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src import anomaly_detector, diffusion_model  # noqa: E402
from src.search_trend_collector import get_search_trend  # noqa: E402
from marcap_utils import marcap_data  # noqa: E402

FORWARD_DAYS = (5, 10, 20)
EVENT_COLS = ['Code', 'Name', 'Close', 'AnomalyScore', 'AnomalyReason']


def collect_flagged_events(df, threshold, top_n):
    """전 기간에 대해 날짜별 이상탐지 상위 top_n 종목을 모은다 (롤링 피처는 1회만 계산)."""
    feat = anomaly_detector.score_anomaly(df)
    events = []
    for date, day in feat.groupby(feat.index):
        day = day[day['AnomalyScore'] >= threshold].sort_values('AnomalyScore', ascending=False).head(top_n)
        for _, row in day[EVENT_COLS].iterrows():
            events.append({'Date': date, **row.to_dict()})
    return pd.DataFrame(events)


def attach_diffusion_stage(df, events, start, end):
    """고유 종목별로 검색량을 1회 조회해 diffusion_model 단계를 이벤트에 붙인다."""
    unique_stocks = events[['Code', 'Name']].drop_duplicates()
    print(f'  -> 이상신호 종목 {len(unique_stocks)}개, 데이터랩 검색량 조회 중...')

    stage_frames = {}
    total = len(unique_stocks)
    for i, (_, r) in enumerate(unique_stocks.iterrows(), 1):
        code, name = r['Code'], r['Name']
        print(f'    ({i}/{total}) {name} 조회 중...', flush=True)
        search_df = None
        for attempt in range(2):  # 드문 일시적 커넥션 리셋에 대비해 1회 재시도
            try:
                search_df = get_search_trend(name, start, end)
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                # 재시도까지 실패한 개별 종목은 marcap만으로 진단하고 넘어간다
                # (pipeline.py가 기존 dart/news 조회 실패를 다루는 방식과 동일).
                print(f'    [경고] {name} 검색량 조회 실패, marcap만으로 진단: {e}')
        stock_df = df[df['Code'] == code]
        attn_df, _ = diffusion_model.diagnose(code, stock_df, search_df)
        stage_frames[code] = attn_df[['Rt', 'Stage']]
        time.sleep(0.05)  # 과호출 방지

    rt_values, stage_values = [], []
    for _, ev in events.iterrows():
        frame = stage_frames.get(ev['Code'])
        if frame is None or ev['Date'] not in frame.index:
            rt_values.append(np.nan)
            stage_values.append(np.nan)
            continue
        row = frame.loc[ev['Date']]
        rt_values.append(row['Rt'])
        stage_values.append(row['Stage'])

    events = events.copy()
    events['Rt'] = rt_values
    events['Stage'] = stage_values
    return events.dropna(subset=['Stage'])


def compute_forward_returns(df, events, forward_days=FORWARD_DAYS):
    """이벤트 발생일 이후 N영업일 순방향 수익률을 계산해 붙인다."""
    price_frames = {
        code: df[df['Code'] == code]['Close'].sort_index()
        for code in events['Code'].unique()
    }
    events = events.copy()
    for n in forward_days:
        col_values = []
        for _, ev in events.iterrows():
            prices = price_frames[ev['Code']]
            if ev['Date'] not in prices.index:
                col_values.append(np.nan)
                continue
            pos = prices.index.get_loc(ev['Date'])
            if pos + n >= len(prices):
                col_values.append(np.nan)
                continue
            col_values.append(prices.iloc[pos + n] / prices.iloc[pos] - 1)
        events[f'FwdReturn{n}d'] = col_values
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2023-01-01')
    parser.add_argument('--end', default='2024-12-31')
    parser.add_argument('--threshold', type=float, default=3.0)
    parser.add_argument('--top-n', type=int, default=5, help='날짜별 이상신호 상위 몇 종목까지 진단할지')
    args = parser.parse_args()

    print(f'[1/4] marcap 데이터 로딩 중... ({args.start} ~ {args.end})')
    df = marcap_data(args.start, args.end, include_halted=True)
    print(f'  -> {len(df):,} rows, {df["Code"].nunique():,} codes')

    print('[2/4] 이상탐지로 이벤트(날짜, 종목) 후보 수집 중...')
    events = collect_flagged_events(df, args.threshold, args.top_n)
    print(f'  -> {len(events):,}건 (고유 종목 {events["Code"].nunique() if not events.empty else 0}개)')
    if events.empty:
        print('이상신호 이벤트가 없어 백테스트를 종료합니다.')
        return

    print('[3/4] SIR 확산 단계 진단 중...')
    events = attach_diffusion_stage(df, events, args.start, args.end)
    events = compute_forward_returns(df, events)

    print('[4/4] 단계별 순방향 수익률 요약')
    print('-' * 70)
    fwd_cols = [f'FwdReturn{n}d' for n in FORWARD_DAYS]
    summary = events.groupby('Stage')[fwd_cols].agg(['mean', 'median', 'count'])
    print(summary.to_string(float_format=lambda x: f'{x:.4f}'))
    print('-' * 70)
    print('해석: "초기 확산기"의 순방향 수익률 평균이 "정점 지나 하락기"보다 높으면')
    print('모델이 실제로 확산 국면을 구분해내고 있다는 증거.')

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'backtest_diffusion_result.csv',
    )
    events.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'상세 결과 저장: {out_path}')


if __name__ == '__main__':
    main()
