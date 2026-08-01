# -*- coding: utf-8 -*-
"""pykrx로 종목별 업종명/PER을 조회한다.

marcap 데이터셋에는 업종(반도체/화학/바이오 등)과 PER이 없어서, KRX 정보데이터
시스템에서 직접 받아오는 pykrx로 보완한다. 전종목을 스캔하는 느린 호출이고 하루
단위로만 바뀌는 값이라 날짜별로 로컬 parquet에 캐시한다.

pykrx는 실제 KRX 서버(data.krx.co.kr)에 접속해야 동작한다. 이 조회에 실패해도
차트 패턴 검색 자체(marcap 로컬 데이터 기반)는 영향받지 않도록, 호출하는 쪽에서
예외를 잡아 업종/PER 없이도 결과를 보여줄 수 있게 설계했다.
"""

import os
import time

import pandas as pd
from pykrx import stock

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'sector_per_cache')
_CACHE_MAX_AGE_SEC = 24 * 3600


def _cache_path(trading_day):
    return os.path.join(_CACHE_DIR, f'{trading_day}.parquet')


def get_sector_and_per(date, force_refresh=False):
    """지정일 기준 전종목 업종명/PER 테이블을 반환한다.

    :param date: 조회 기준일 (datetime 또는 문자열). 휴일이면 가장 가까운
        이전 영업일로 자동 보정한다.
    :return: DataFrame, 인덱스=Code, 컬럼=[Sector, PER]
    """
    date_str = pd.to_datetime(date).strftime('%Y%m%d')
    trading_day = stock.get_nearest_business_day_in_a_week(date_str, prev=True)

    cache_file = _cache_path(trading_day)
    if not force_refresh and os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < _CACHE_MAX_AGE_SEC:
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
    os.makedirs(_CACHE_DIR, exist_ok=True)
    result.to_parquet(cache_file)
    return result
