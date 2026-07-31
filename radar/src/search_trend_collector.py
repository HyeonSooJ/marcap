# -*- coding: utf-8 -*-
"""네이버 데이터랩 검색어트렌드 API로 종목명 검색량 추이를 수집한다.

무료 API 키 발급: https://developers.naver.com/apps (애플리케이션 등록 -> 사용 API에
"데이터랩(검색어트렌드)" 추가. 뉴스 검색과 동일한 애플리케이션에 권한만 추가하면 됨)
환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 은 news_collector.py와 공유한다.

무료 쿼터가 하루 1,000회로 낮아서(백테스트처럼 같은 종목/구간을 반복 조회하는
용도에는 금방 소진됨), 조회 결과를 로컬에 캐싱한다. 과거 날짜 구간은 다시 조회해도
값이 바뀌지 않으므로 캐시 만료 없이 그대로 재사용한다.
"""

import hashlib
import os
import re

import pandas as pd
import requests

from .news_collector import NaverNotConfigured, _headers  # noqa: E402  (동일 앱 자격증명 재사용)

DATALAB_SEARCH_URL = 'https://openapi.naver.com/v1/datalab/search'
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'search_trend_cache')


class DatalabApiError(RuntimeError):
    """데이터랩 API가 오류를 반환했을 때 발생 (스코프 미설정, 쿼터 초과, 잘못된 파라미터 등)."""


def _cache_path(keyword, start_date, end_date, time_unit, extra_keywords):
    key = f'{keyword}|{start_date}|{end_date}|{time_unit}|{sorted(extra_keywords or [])}'
    digest = hashlib.md5(key.encode('utf-8')).hexdigest()[:12]
    safe_keyword = re.sub(r'[^0-9A-Za-z가-힣]', '', keyword)[:20] or 'keyword'
    return os.path.join(_CACHE_DIR, f'{safe_keyword}_{digest}.parquet')


def get_search_trend(keyword, start_date, end_date, time_unit='date', extra_keywords=None, use_cache=True):
    """종목명(keyword) 검색량 추이(상대지수, 구간 내 최대값=100)를 반환한다.

    :param keyword: 검색 키워드이자 결과 그룹명 (예: 종목명 '에코프로')
    :param start_date, end_date: 'YYYY-MM-DD' 형식
    :param time_unit: 'date' | 'week' | 'month'
    :param extra_keywords: keyword와 같은 그룹으로 묶을 동의어/별칭 리스트 (optional)
    :param use_cache: False로 주면 캐시를 쓰지 않고 항상 API를 호출한다
    :return: DataFrame, DatetimeIndex, 컬럼=['ratio'] (0~100 상대 검색량 지수)
    """
    cache_path = _cache_path(keyword, start_date, end_date, time_unit, extra_keywords)
    if use_cache and os.path.exists(cache_path):
        return pd.read_parquet(cache_path)

    keywords = [keyword] + list(extra_keywords or [])
    body = {
        'startDate': start_date,
        'endDate': end_date,
        'timeUnit': time_unit,
        'keywordGroups': [{'groupName': keyword, 'keywords': keywords}],
    }
    resp = requests.post(
        DATALAB_SEARCH_URL,
        headers={**_headers(), 'Content-Type': 'application/json'},
        json=body,
        timeout=15,
    )
    if resp.status_code != 200:
        raise DatalabApiError(f'데이터랩 API 오류 (status={resp.status_code}): {resp.text}')

    results = resp.json().get('results', [])
    if not results:
        result = pd.DataFrame(columns=['ratio']).astype({'ratio': float})
    else:
        data = results[0].get('data', [])
        df = pd.DataFrame(data)
        if df.empty:
            result = pd.DataFrame(columns=['ratio']).astype({'ratio': float})
        else:
            df['period'] = pd.to_datetime(df['period'])
            result = df.set_index('period')[['ratio']]

    if use_cache:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        result.to_parquet(cache_path)
    return result
