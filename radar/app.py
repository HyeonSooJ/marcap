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
from src.diffusion_model import diagnose_flagged_stocks  # noqa: E402
from src.investor_profile import (  # noqa: E402
    PROFILE_QUESTIONS, PROFILE_DESCRIPTIONS, classify_profile, build_fallback_alert,
)
from src.llm_report import generate_personalized_alert  # noqa: E402
from marcap_utils import marcap_data  # noqa: E402

st.set_page_config(page_title='마캡레이더', page_icon='📡', layout='wide')

st.title('📡 마캡레이더 — 상장기업 이상변동 조기경보')
st.caption('marcap 일별 시가총액/주가/거래량 데이터를 통계적으로 스캔해 이상신호를 잡아내고, '
           '실제 관리종목·투자주의환기종목 지정 이력과 대조해 조기경보 성능을 검증합니다.')

tab1, tab2, tab3, tab4 = st.tabs(['오늘의 이상신호', '데일리 리포트', '백테스트 결과', '밈스탁 확산 진단 + 맞춤 경고'])

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

with tab4:
    st.subheader('밈스탁 버블 확산 진단 + 맞춤 경고')
    st.caption(
        '1차로 이상탐지를 통과한 종목에 한해, 감염병 확산모델(SIR)의 실효재생산수(Rt) 개념을 '
        '시장 관심(거래대금 회전율 + 검색량) 확산에 적용해 지금 어느 단계인지 진단합니다. '
        '재무·신용 지표가 아니라 "정보 확산의 속도"로 보는 보조 지표이며, 투자 성향 설문과 '
        '결합해 개인화된 주의 메시지를 만듭니다. 특정 종목의 매수·매도를 추천하지 않습니다.'
    )

    col1, col2 = st.columns(2)
    diff_lookback = col1.number_input(
        '조회 기간(일)', min_value=30, max_value=365, value=120, step=10, key='diff_lookback',
    )
    diff_threshold = col2.number_input(
        '1차 이상신호 임계값(z-score)', min_value=1.0, max_value=6.0, value=3.0, step=0.5, key='diff_threshold',
    )

    if st.button('확산 진단 스캔 실행'):
        with st.spinner('marcap 데이터 로딩 + 이상탐지 + 확산 진단 실행 중 '
                         '(검색량 API 호출 포함, 다소 시간이 걸릴 수 있습니다)...'):
            end = datetime.today()
            start = end - timedelta(days=int(diff_lookback))
            df = marcap_data(start, end, include_halted=True)
            if df.empty:
                st.warning('불러올 데이터가 없습니다.')
                st.session_state['diffusion_result'] = None
            else:
                st.session_state['diffusion_result'] = diagnose_flagged_stocks(
                    df, threshold=diff_threshold, top_n=10,
                )

    diag = st.session_state.get('diffusion_result')
    if diag is None:
        st.info('스캔을 실행하면 결과가 여기 표시됩니다.')
    elif diag.empty:
        st.info('이상신호로 플래그된 종목이 없습니다.')
    else:
        show_cols = ['Code', 'Name', 'Close', 'ChangesRatio', 'AnomalyScore', 'AnomalyReason',
                     'Attention', 'Rt', 'Stage']
        st.dataframe(diag[show_cols], use_container_width=True)

        valid = diag.dropna(subset=['Stage']).reset_index(drop=True)
        if valid.empty:
            st.info('확산 단계를 진단할 수 있는 종목이 없습니다 (검색량 데이터 부족 등으로 Rt 산출 불가).')
        else:
            st.divider()
            st.markdown('#### 맞춤 경고 메시지 생성')

            pick_labels = [f"{r['Name']} ({r['Code']}) — {r['Stage']}" for _, r in valid.iterrows()]
            picked_idx = st.selectbox('종목 선택', range(len(pick_labels)), format_func=lambda i: pick_labels[i])
            picked_row = valid.iloc[picked_idx]

            st.markdown('**투자 성향 설문 (5문항)**')
            answers = []
            for i, (question, options) in enumerate(PROFILE_QUESTIONS):
                choice_labels = [opt[0] for opt in options]
                choice = st.radio(question, choice_labels, key=f'profile_q{i}')
                answers.append(choice_labels.index(choice))

            if st.button('맞춤 경고 생성', type='primary'):
                profile_key, scores = classify_profile(answers)
                st.info(f'당신의 투자 성향: **{profile_key}** (점수: {scores})')

                diffusion_summary = picked_row.to_dict()
                profile_description = PROFILE_DESCRIPTIONS[profile_key]

                if os.environ.get('ANTHROPIC_API_KEY'):
                    try:
                        alert_text = generate_personalized_alert(
                            diffusion_summary, profile_key, profile_description,
                        )
                    except Exception as e:
                        st.warning(f'LLM 호출 실패, 규칙 기반 메시지로 대체합니다: {e}')
                        alert_text = build_fallback_alert(diffusion_summary, profile_key)
                else:
                    alert_text = build_fallback_alert(diffusion_summary, profile_key)

                st.markdown(f'> {alert_text}')
