# -*- coding: utf-8 -*-
"""데일리 리스크 레이더 파이프라인.

1) marcap 최근 데이터를 불러와 이상신호 상위 종목을 탐지
2) (키가 설정된 경우) 해당 종목의 최근 DART 공시 / 뉴스를 수집
3) (키가 설정된 경우) LLM으로 원인 해설 리포트를 생성
4) 결과를 output/reports/YYYY-MM-DD.md 로 저장

DART_API_KEY / NAVER_CLIENT_ID / NAVER_CLIENT_SECRET / ANTHROPIC_API_KEY 중
설정되지 않은 항목은 건너뛰고, 이상탐지 결과만으로도 리포트가 생성되도록
degrade gracefully 한다.
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.anomaly_detector import detect_anomalies  # noqa: E402
from src import dart_collector, news_collector, llm_report  # noqa: E402
from marcap_utils import marcap_data  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'reports')


def _dept_display(dept):
    """marcap Dept 값을 표시용 문자열로 변환한다.

    연도별 parquet 파일마다 무분류 값이 실제 NaN(float)이거나 문자열 'nan'으로
    섞여 있어, 두 경우 모두 '-'로 정규화한다.
    """
    if dept is None or (isinstance(dept, float) and pd.isna(dept)):
        return '-'
    text = str(dept).strip()
    return '-' if text.lower() in ('', 'nan', 'none') else text


def _has_dart():
    return bool(os.environ.get('DART_API_KEY'))


def _has_naver():
    return bool(os.environ.get('NAVER_CLIENT_ID') and os.environ.get('NAVER_CLIENT_SECRET'))


def _has_llm():
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


def run(date=None, lookback_days=90, threshold=3.0, top_n=10):
    target_date = datetime.today() if date is None else datetime.fromisoformat(str(date))
    start = target_date - timedelta(days=lookback_days)

    print(f'[1/3] marcap 데이터 로딩 ({start.date()} ~ {target_date.date()})')
    df = marcap_data(start, target_date, include_halted=True)
    if df.empty:
        print('데이터가 없습니다. (휴장일이거나 아직 업데이트되지 않았을 수 있습니다)')
        return None
    report_date = df.index.max().date()

    print('[2/3] 이상탐지 실행')
    anomalies = detect_anomalies(df, date=None, threshold=threshold, top_n=top_n)
    print(f'  -> {len(anomalies)}개 종목 플래그')

    print('[3/3] 종목별 컨텍스트 수집 + 리포트 생성')
    sections = []
    for _, row in anomalies.iterrows():
        code, name = row['Code'], row['Name']
        section = [f"## {name} ({code})", '']
        section.append(
            f"- 이상점수: **{row['AnomalyScore']:.2f}** (주요 원인 지표: `{row['AnomalyReason']}`)\n"
            f"- 종가: {row['Close']} / 등락률: {row['ChangesRatio']}% / 거래량: {row['Volume']:,.0f}\n"
            f"- 시가총액순위: {row['Rank']} / 소속부: {_dept_display(row['Dept'])}"
        )

        disclosures, news_items = None, None
        if _has_dart():
            try:
                bgn = (target_date - timedelta(days=30)).strftime('%Y%m%d')
                end = target_date.strftime('%Y%m%d')
                disclosures = dart_collector.get_disclosures(code, bgn, end)
            except Exception as e:
                print(f'  [경고] DART 조회 실패 ({name}): {e}')

        if _has_naver():
            try:
                news_items = news_collector.get_recent_news(name, display=5)
            except Exception as e:
                print(f'  [경고] 뉴스 조회 실패 ({name}): {e}')

        if _has_llm():
            try:
                row_dict = row.to_dict()
                row_dict['Date'] = report_date.isoformat()
                report_text = llm_report.generate_report(row_dict, disclosures, news_items)
                section.append('')
                section.append(report_text)
            except Exception as e:
                print(f'  [경고] LLM 리포트 생성 실패 ({name}): {e}')
        else:
            section.append('')
            section.append('_(ANTHROPIC_API_KEY 미설정 — 원인 해설 리포트 생략, 이상탐지 수치만 표시)_')

        sections.append('\n'.join(section))

    header = f"# 마캡레이더 데일리 리스크 브리핑 — {report_date}\n"
    body = '\n\n---\n\n'.join(sections) if sections else '_오늘 임계값을 초과한 이상신호 종목이 없습니다._'
    full_report = f'{header}\n{body}\n'

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f'{report_date}.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(full_report)
    print(f'리포트 저장: {out_path}')
    return out_path


if __name__ == '__main__':
    run()
