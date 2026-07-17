# -*- coding: utf-8 -*-
"""OpenDART(전자공시) API를 이용해 종목별 최근 공시 목록을 수집한다.

무료 API 키 발급: https://opendart.fss.or.kr (회원가입 -> 오픈API 이용신청)
환경변수 DART_API_KEY 에 발급받은 키를 설정해서 사용한다.
"""

import io
import os
import time
import zipfile
from xml.etree import ElementTree

import pandas as pd
import requests

DART_BASE = 'https://opendart.fss.or.kr/api'
_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'dart_corp_code.parquet')
_CACHE_MAX_AGE_SEC = 7 * 24 * 3600


DART_NO_DATA_STATUS = '013'  # 조회된 데이터가 없음 (정상적인 "공시 없음")


class DartNotConfigured(RuntimeError):
    """DART_API_KEY 환경변수가 설정되지 않았을 때 발생."""


class DartApiError(RuntimeError):
    """DART_NO_DATA_STATUS 이외의 오류 상태코드가 반환됐을 때 발생 (키 만료, rate limit 등)."""


def _api_key():
    key = os.environ.get('DART_API_KEY')
    if not key:
        raise DartNotConfigured(
            'DART_API_KEY 환경변수가 없습니다. https://opendart.fss.or.kr 에서 무료로 발급받아 설정하세요.'
        )
    return key


def load_corp_code_map(force_refresh=False):
    """DART 고유번호(corp_code) <-> KRX 종목코드(stock_code) 매핑 테이블.

    DART API는 종목코드가 아닌 자체 corp_code로 공시를 조회하기 때문에 필요하다.
    최초 1회(또는 캐시 만료 시) 전체 매핑 파일을 내려받아 로컬에 캐시한다.
    """
    if not force_refresh and os.path.exists(_CACHE_PATH):
        age = time.time() - os.path.getmtime(_CACHE_PATH)
        if age < _CACHE_MAX_AGE_SEC:
            return pd.read_parquet(_CACHE_PATH)

    resp = requests.get(f'{DART_BASE}/corpCode.xml', params={'crtfc_key': _api_key()}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read('CORPCODE.xml')

    root = ElementTree.fromstring(xml_bytes)
    rows = []
    for item in root.findall('list'):
        stock_code = (item.findtext('stock_code') or '').strip()
        if not stock_code:
            continue  # 비상장사는 종목코드가 없어 제외
        rows.append({
            'corp_code': item.findtext('corp_code'),
            'corp_name': item.findtext('corp_name'),
            'stock_code': stock_code,
        })
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    df.to_parquet(_CACHE_PATH, index=False)
    return df


def get_disclosures(stock_code, bgn_de, end_de, page_count=20):
    """특정 종목의 기간 내 공시 목록을 반환한다.

    :param stock_code: 6자리 KRX 종목코드 (예: '005930')
    :param bgn_de, end_de: 'YYYYMMDD' 형식
    :return: DataFrame [rcept_no, report_nm, rcept_dt, flr_nm]
    """
    corp_map = load_corp_code_map()
    matched = corp_map[corp_map['stock_code'] == stock_code]
    if matched.empty:
        return pd.DataFrame(columns=['rcept_no', 'report_nm', 'rcept_dt', 'flr_nm'])
    corp_code = matched.iloc[0]['corp_code']

    resp = requests.get(f'{DART_BASE}/list.json', params={
        'crtfc_key': _api_key(),
        'corp_code': corp_code,
        'bgn_de': bgn_de,
        'end_de': end_de,
        'page_count': page_count,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    status = data.get('status')
    if status == DART_NO_DATA_STATUS:
        return pd.DataFrame(columns=['rcept_no', 'report_nm', 'rcept_dt', 'flr_nm'])
    if status != '000':
        raise DartApiError(f"DART API 오류 (status={status}): {data.get('message')}")

    items = data.get('list', [])
    df = pd.DataFrame(items)
    if df.empty:
        return pd.DataFrame(columns=['rcept_no', 'report_nm', 'rcept_dt', 'flr_nm'])
    return df[['rcept_no', 'report_nm', 'rcept_dt', 'flr_nm']]
