# -*- coding: utf-8 -*-
# kospi_index_proxy.py - marcap 데이터셋으로 KOSPI 지수 대용치를 만들고 급락일을 분석하는 예제
#
# marcap 데이터셋은 종목별 시가총액 데이터만 제공하며 공식 KOSPI 지수 값은 포함하지 않는다.
# 이 스크립트는 KOSPI 시장 소속 종목들의 (가격 x 상장주식수) 합을 매일 집계해
# 시가총액 가중 지수 대용치를 만들고, 하루 등락률이 지정한 임계값 이하로 급락한 날과
# 그 다음 거래일의 시가/양봉·음봉 여부를 찾아낸다.

import sys
import os

_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_REPO_DIR))

import pandas as pd
from marcap import marcap_data


def build_kospi_index_proxy(start, end, base_value=1000):
  '''KOSPI 시장 시가총액 합계 기반 일별 OHLC 지수 대용치를 만든다.'''
  df = marcap_data(start, end)
  kospi = df[df['Market'] == 'KOSPI'].copy()

  for col in ['Open', 'High', 'Low', 'Close']:
    kospi[col + '_cap'] = kospi[col] * kospi['Stocks']

  daily = kospi.groupby('Date').agg(
    Open=('Open_cap', 'sum'),
    High=('High_cap', 'sum'),
    Low=('Low_cap', 'sum'),
    Close=('Close_cap', 'sum'),
  ).sort_index()

  base = daily['Close'].iloc[0]
  idx = daily / base * base_value
  idx['Return'] = idx['Close'].pct_change() * 100
  return idx


def find_drop_days_and_next_day(idx, drop_threshold=-7):
  '''등락률이 drop_threshold 이하로 급락한 날과 다음 거래일의 시가/캔들 정보를 반환한다.'''
  dates = idx.index.tolist()
  drops = idx[idx['Return'] <= drop_threshold]

  results = []
  for d in drops.index:
    pos = dates.index(d)
    if pos + 1 >= len(dates):
      continue
    next_date = dates[pos + 1]
    next_row = idx.loc[next_date]
    candle = '양봉' if next_row['Close'] > next_row['Open'] else ('음봉' if next_row['Close'] < next_row['Open'] else '보합')
    results.append({
      'drop_date': d,
      'drop_return': idx.loc[d, 'Return'],
      'next_date': next_date,
      'next_open': next_row['Open'],
      'next_close': next_row['Close'],
      'candle': candle,
      'next_return': next_row['Return'],
    })
  return pd.DataFrame(results)


if __name__ == '__main__':
  # 데이터셋에 존재하는 가장 최근 날짜를 기준으로 최근 4개월 구간을 잡는다.
  from marcap.marcap_utils import _data_dir
  import glob
  last_year_file = sorted(glob.glob(os.path.join(_data_dir(), 'marcap-*.parquet')))[-1]
  last_year_df = pd.read_parquet(last_year_file)
  last_date = pd.to_datetime(last_year_df['Date']).max()
  start_date = last_date - pd.DateOffset(months=4)

  idx = build_kospi_index_proxy(start_date, last_date)
  print(f'기간: {start_date.date()} ~ {last_date.date()}')
  print(idx.tail())

  events = find_drop_days_and_next_day(idx, drop_threshold=-7)
  print('\n-7% 이상 급락일 및 다음 거래일:')
  print(events)
