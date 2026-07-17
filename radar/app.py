# -*- coding: utf-8 -*-
"""마캡레이더 데모 대시보드 (Streamlit).

실행: streamlit run radar/app.py
"""

import glob
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.anomaly_detector import detect_anomalies  # noqa: E402
from marcap_utils import marcap_data  # noqa: E402

st.set_page_config(page_title='마캡레이더', page_icon='📡', layout='wide')

st.title('📡 마캡레이더 — 상장기업 이상변동 조기경보')
st.caption('marcap 일별 시가총액/주가/거래량 데이터를 통계적으로 스캔해 이상신호를 잡아내고, '
           '실제 관리종목·투자주의환기종목 지정 이력과 대조해 조기경보 성능을 검증합니다.')

tab1, tab2, tab3 = st.tabs(['오늘의 이상신호', '데일리 리포트', '백테스트 결과'])

with tab1:
    col1, col2, col3 = st.columns(3)
    lookback = col1.number_input('롤링 윈도우(일)', min_value=30, max_value=365, value=90, step=10)
    threshold = col2.number_input('이상신호 임계값(z-score)', min_value=1.0, max_value=6.0, value=3.0, step=0.5)
    top_n = col3.number_input('표시 종목 수', min_value=5, max_value=50, value=10, step=5)

    if st.button('스캔 실행', type='primary'):
        with st.spinner('marcap 데이터 로딩 및 이상탐지 실행 중...'):
            end = datetime.today()
            start = end - timedelta(days=int(lookback))
            df = marcap_data(start, end, include_halted=True)
            if df.empty:
                st.warning('불러올 데이터가 없습니다.')
            else:
                result = detect_anomalies(df, threshold=threshold, top_n=int(top_n))
                st.success(f'{df.index.max().date()} 기준 {len(result)}개 종목 플래그')
                st.dataframe(
                    result[['Code', 'Name', 'Close', 'ChangesRatio', 'Volume', 'Rank', 'Dept',
                            'AnomalyScore', 'AnomalyReason']],
                    use_container_width=True,
                )

with tab2:
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'reports')
    files = sorted(glob.glob(os.path.join(report_dir, '*.md')), reverse=True)
    if not files:
        st.info('아직 생성된 리포트가 없습니다. `python radar/src/pipeline.py` 를 먼저 실행하세요.')
    else:
        selected = st.selectbox('날짜 선택', [os.path.basename(f).replace('.md', '') for f in files])
        with open(os.path.join(report_dir, f'{selected}.md'), encoding='utf-8') as f:
            st.markdown(f.read())

with tab3:
    bt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'backtest_result.csv')
    if not os.path.exists(bt_path):
        st.info('백테스트 결과가 없습니다. `python radar/scripts/backtest.py` 를 먼저 실행하세요.')
    else:
        bt = pd.read_csv(bt_path)
        n_events = len(bt)
        coverage = bt['Detected'].mean() * 100 if n_events else 0
        avg_lead = bt.loc[bt['Detected'] == True, 'LeadDaysApprox'].mean() if n_events else 0  # noqa: E712

        c1, c2, c3 = st.columns(3)
        c1.metric('위험지정 이벤트 수', f'{n_events}건')
        c2.metric('조기탐지 커버리지', f'{coverage:.1f}%')
        c3.metric('평균 리드타임', f'{avg_lead:.1f} 영업일')

        st.dataframe(bt, use_container_width=True)
