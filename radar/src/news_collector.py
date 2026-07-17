# -*- coding: utf-8 -*-
"""네이버 검색 오픈API로 종목 관련 최근 뉴스를 수집한다.

무료 API 키 발급: https://developers.naver.com/apps (애플리케이션 등록 -> 검색 API 선택)
환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 에 발급받은 값을 설정해서 사용한다.
"""

import os

import requests

NAVER_NEWS_URL = 'https://openapi.naver.com/v1/search/news.json'


class NaverNotConfigured(RuntimeError):
    """NAVER_CLIENT_ID/SECRET 환경변수가 설정되지 않았을 때 발생."""


def _headers():
    client_id = os.environ.get('NAVER_CLIENT_ID')
    client_secret = os.environ.get('NAVER_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise NaverNotConfigured(
            'NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다. '
            'https://developers.naver.com/apps 에서 무료로 발급받아 설정하세요.'
        )
    return {'X-Naver-Client-Id': client_id, 'X-Naver-Client-Secret': client_secret}


def _strip_tags(text):
    # 네이버 뉴스 검색 API는 검색어 강조에 <b>/</b>만 사용한다(HTML 전반이 아님).
    # 일반 정규식(<[^>]+>)은 본문에 등장하는 부등호(<, >)까지 태그로 오인해
    # 그 사이 텍스트를 통째로 삭제할 수 있어, 알려진 태그만 명시적으로 제거한다.
    text = (text or '').replace('<b>', '').replace('</b>', '')
    return text.replace('&quot;', '"').replace('&amp;', '&')


def get_recent_news(query, display=5, sort='date'):
    """종목명(query) 관련 최근 뉴스 목록을 반환한다.

    :return: list[dict] (title, description, link, pub_date)
    """
    resp = requests.get(
        NAVER_NEWS_URL,
        headers=_headers(),
        params={'query': query, 'display': display, 'sort': sort},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get('items', [])
    return [
        {
            'title': _strip_tags(it.get('title')),
            'description': _strip_tags(it.get('description')),
            'link': it.get('link'),
            'pub_date': it.get('pubDate'),
        }
        for it in items
    ]
