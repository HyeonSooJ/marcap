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
    PROFILE_QUESTIONS, PROFILE_DESCRIPTIONS, PROFILE_LABELS, STAGE_LABELS,
    classify_profile, build_fallback_alert,
)
from src.llm_report import generate_personalized_alert  # noqa: E402
from src.i18n import t, col_label, reason_label, pattern_label  # noqa: E402
from src.chart_pattern import (  # noqa: E402
    PATTERN_DEFINITIONS, BREAKOUT_PATTERN_KEY, HALT_PATTERN_KEY, RALLY_PULLBACK_PATTERN_KEY,
    TODAY_MOMENTUM_PATTERN_KEY, BOTTOM_REBOUND_PATTERN_KEY, resolve_date_range,
    filter_single_stocks, filter_top_marcap, find_matching_stocks, find_halted_stocks,
    find_today_momentum_stocks, find_bottom_rebound_stocks,
)
from marcap_utils import marcap_data  # noqa: E402

if 'lang' not in st.session_state:
    st.session_state['lang'] = 'ko'

st.set_page_config(page_title='MarcapRadar', page_icon='📡', layout='wide')

_, lang_col = st.columns([10, 1])
with lang_col:
    with st.popover('🌐', use_container_width=True):
        _lang_options = {'한국어': 'ko', 'English': 'en'}
        _labels = list(_lang_options.keys())
        _current_label = _labels[list(_lang_options.values()).index(st.session_state['lang'])]
        _choice = st.radio(
            'Language / 언어', _labels, index=_labels.index(_current_label),
            key='lang_radio', label_visibility='collapsed',
        )
        st.session_state['lang'] = _lang_options[_choice]

lang = st.session_state['lang']

st.title(t('title', lang))
st.caption(t('top_caption', lang))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t('tab1_name', lang), t('tab2_name', lang), t('tab3_name', lang), t('tab4_name', lang),
    t('tab5_name', lang),
])

with tab1:
    st.markdown(t('tab1_explain', lang))

    col1, col2, col3 = st.columns(3)
    _default_end = datetime.today().date()
    _default_start = _default_end - timedelta(days=90)
    date_range = col1.date_input(
        t('date_range_label', lang),
        value=(_default_start, _default_end),
        max_value=_default_end,
        help=t('date_range_help', lang),
    )
    threshold = col2.number_input(
        t('threshold_label', lang), min_value=1.0, max_value=6.0, value=3.0, step=0.5,
        help=t('threshold_help', lang),
    )
    top_n = col3.number_input(t('top_n_label', lang), min_value=5, max_value=50, value=10, step=5)

    if st.button(t('scan_button', lang), type='primary'):
        if not (isinstance(date_range, (tuple, list)) and len(date_range) == 2):
            st.warning(t('need_both_dates', lang))
        else:
            start, end = date_range
            with st.spinner(t('loading_scan', lang)):
                df = marcap_data(start, end, include_halted=True)
                if df.empty:
                    st.warning(t('no_data', lang))
                else:
                    result = detect_anomalies(df, threshold=threshold, top_n=int(top_n))
                    st.success(t('scan_success', lang, date=df.index.max().date(), n=len(result)))
                    show_cols = ['Code', 'Name', 'Close', 'ChangesRatio', 'Volume', 'Rank', 'Dept',
                                 'AnomalyScore', 'AnomalyReason']
                    display_result = result[show_cols].copy()
                    display_result['AnomalyReason'] = display_result['AnomalyReason'].map(
                        lambda v: reason_label(v, lang),
                    )
                    # marcap은 일별(장 마감 기준) 데이터라 시:분:초 정보가 없다. DatetimeIndex를
                    # 그대로 보여주면 의미 없는 "00:00:00"이 붙어 나오므로 날짜만 표시한다.
                    display_result.index = display_result.index.strftime('%Y-%m-%d')
                    display_result.index.name = t('date_col', lang)
                    display_result = display_result.rename(
                        columns={c: col_label(c, lang) for c in show_cols},
                    )
                    st.dataframe(display_result, use_container_width=True)

with tab2:
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'reports')
    files = sorted(glob.glob(os.path.join(report_dir, '*.md')), reverse=True)
    if not files:
        st.info(t('tab2_no_report', lang))
    else:
        if lang == 'en':
            st.caption(t('tab2_lang_note', lang))
        selected = st.selectbox(t('tab2_select_date', lang), [os.path.basename(f).replace('.md', '') for f in files])
        with open(os.path.join(report_dir, f'{selected}.md'), encoding='utf-8') as f:
            st.markdown(f.read())

with tab3:
    bt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'backtest_result.csv')
    if not os.path.exists(bt_path):
        st.info(t('tab3_no_backtest', lang))
    else:
        bt = pd.read_csv(bt_path)
        n_events = len(bt)
        coverage = bt['Detected'].mean() * 100 if n_events else 0
        avg_lead = bt.loc[bt['Detected'] == True, 'LeadDaysApprox'].mean() if n_events else 0  # noqa: E712

        c1, c2, c3 = st.columns(3)
        c1.metric(t('tab3_metric_events', lang), f"{n_events}{t('tab3_unit_events', lang)}")
        c2.metric(t('tab3_metric_coverage', lang), f'{coverage:.1f}%')
        c3.metric(t('tab3_metric_lead', lang), f"{avg_lead:.1f} {t('tab3_unit_lead', lang)}")

        st.dataframe(
            bt.rename(columns={c: col_label(c, lang) for c in bt.columns}),
            use_container_width=True,
        )

with tab4:
    st.subheader(t('tab4_subheader', lang))
    st.caption(t('tab4_caption', lang))
    st.markdown(t('tab4_explain', lang))

    col1, col2 = st.columns(2)
    _diff_default_end = datetime.today().date()
    _diff_default_start = _diff_default_end - timedelta(days=120)
    diff_date_range = col1.date_input(
        t('date_range_label', lang),
        value=(_diff_default_start, _diff_default_end),
        max_value=_diff_default_end,
        key='diff_date_range',
        help=t('diff_date_range_help', lang),
    )
    diff_threshold = col2.number_input(
        t('threshold_label', lang), min_value=1.0, max_value=6.0, value=3.0, step=0.5, key='diff_threshold',
        help=t('diff_threshold_help', lang),
    )

    if st.button(t('diff_scan_button', lang)):
        if not (isinstance(diff_date_range, (tuple, list)) and len(diff_date_range) == 2):
            st.warning(t('need_both_dates', lang))
            st.stop()
        start, end = diff_date_range
        with st.spinner(t('diff_loading', lang)):
            df = marcap_data(start, end, include_halted=True)
            if df.empty:
                st.warning(t('no_data', lang))
                st.session_state['diffusion_result'] = None
            else:
                st.session_state['diffusion_result'] = diagnose_flagged_stocks(
                    df, threshold=diff_threshold, top_n=10,
                )

    diag = st.session_state.get('diffusion_result')
    if diag is None:
        st.info(t('diff_waiting', lang))
    elif diag.empty:
        st.info(t('diff_none_flagged', lang))
    else:
        show_cols = ['Code', 'Name', 'Close', 'ChangesRatio', 'AnomalyScore', 'AnomalyReason',
                     'Attention', 'Rt', 'Stage']
        display_diag = diag[show_cols].copy()
        display_diag['AnomalyReason'] = display_diag['AnomalyReason'].map(lambda v: reason_label(v, lang))
        if lang == 'en':
            display_diag['Stage'] = display_diag['Stage'].map(
                lambda s: STAGE_LABELS.get(s, {}).get('en', s) if pd.notna(s) else s,
            )
        display_diag = display_diag.rename(columns={c: col_label(c, lang) for c in show_cols})
        st.dataframe(display_diag, use_container_width=True)

        valid = diag.dropna(subset=['Stage']).reset_index(drop=True)
        if valid.empty:
            st.info(t('diff_none_diagnosable', lang))
        else:
            st.divider()
            st.markdown(t('alert_section_header', lang))

            pick_labels = [
                f"{r['Name']} ({r['Code']}) — {STAGE_LABELS.get(r['Stage'], {}).get(lang, r['Stage'])}"
                for _, r in valid.iterrows()
            ]
            picked_idx = st.selectbox(t('pick_stock_label', lang), range(len(pick_labels)),
                                       format_func=lambda i: pick_labels[i])
            picked_row = valid.iloc[picked_idx]

            st.markdown(t('survey_header', lang))
            answers = []
            for i, (question, options) in enumerate(PROFILE_QUESTIONS[lang]):
                choice_labels = [opt[0] for opt in options]
                choice = st.radio(question, choice_labels, key=f'profile_q{i}')
                answers.append(choice_labels.index(choice))

            if st.button(t('generate_alert_button', lang), type='primary'):
                profile_key, scores = classify_profile(answers, lang=lang)
                profile_label = PROFILE_LABELS[profile_key][lang]
                display_scores = {PROFILE_LABELS[k][lang]: v for k, v in scores.items()}
                st.info(t('your_profile', lang, profile=profile_label, scores=display_scores))

                diffusion_summary = picked_row.to_dict()
                profile_description = PROFILE_DESCRIPTIONS[profile_key][lang]

                if os.environ.get('ANTHROPIC_API_KEY'):
                    try:
                        alert_text = generate_personalized_alert(
                            diffusion_summary, profile_key, profile_description, lang=lang,
                        )
                    except Exception as e:
                        st.warning(t('llm_call_failed', lang, error=e))
                        alert_text = build_fallback_alert(diffusion_summary, profile_key, lang=lang)
                else:
                    alert_text = build_fallback_alert(diffusion_summary, profile_key, lang=lang)

                st.markdown(f'> {alert_text}')

with tab5:
    st.subheader(t('tab5_subheader', lang))
    st.markdown(t('tab5_explain', lang))

    col1, col2, col3 = st.columns(3)
    end_date = col1.date_input(
        t('tab5_end_date_label', lang), value=datetime.today().date(),
        max_value=datetime.today().date(), key='pattern_end_date',
    )
    months = col2.selectbox(t('tab5_months_label', lang), list(range(1, 13)), index=2, key='pattern_months')
    pattern_key = col3.selectbox(
        t('tab5_pattern_label', lang), list(PATTERN_DEFINITIONS.keys()),
        format_func=lambda k: pattern_label(k, lang), key='pattern_key',
    )

    if st.button(t('tab5_confirm_button', lang), type='primary'):
        is_today_momentum = pattern_key == TODAY_MOMENTUM_PATTERN_KEY
        # ⑦번은 실제 검증(최근 2개월 고정 기준)과 동일한 조건으로 계산해야 검증된
        # 적중률(16.7%->20~30%)이 의미가 있어서, ②개월수 선택과 무관하게 항상
        # 최근 2개월로 계산한다.
        start, end = resolve_date_range(end_date, 2) if is_today_momentum else resolve_date_range(end_date, months)
        with st.spinner(t('tab5_loading', lang)):
            is_halt = pattern_key == HALT_PATTERN_KEY
            # 거래정지일은 marcap_data 기본값(include_halted=False)에서는 아예 빠지므로,
            # "⑤ 거래정지 종목"을 찾을 때만 그 행들을 포함해서 불러온다.
            df = marcap_data(start, end, include_halted=is_halt)
            if df.empty:
                st.warning(t('tab5_no_data', lang))
                st.session_state['pattern_result'] = None
            else:
                df = filter_single_stocks(df)
                df = filter_top_marcap(df)
                if is_halt:
                    matched = find_halted_stocks(df)
                elif is_today_momentum:
                    matched = find_today_momentum_stocks(df)
                elif pattern_key == BOTTOM_REBOUND_PATTERN_KEY:
                    matched = find_bottom_rebound_stocks(df)
                else:
                    matched = find_matching_stocks(df, pattern_key)
                if matched.empty:
                    st.session_state['pattern_result'] = matched
                else:
                    try:
                        from src.sector_data import get_sector_and_per
                        sector_per = get_sector_and_per(end)
                        matched = matched.join(sector_per, on='Code')
                    except Exception as e:
                        st.warning(t('tab5_sector_fail', lang, error=e))
                        matched['Sector'] = pd.NA
                        matched['PER'] = pd.NA
                    st.session_state['pattern_result'] = matched
                    st.session_state['pattern_range'] = (start, end)
                    st.session_state['pattern_result_key'] = pattern_key
                    matched_codes = set(matched['Code'])
                    st.session_state['pattern_chart_df'] = (
                        df[df['Code'].isin(matched_codes)][['Code', 'Name', 'Close']].copy()
                    )

    matched = st.session_state.get('pattern_result')
    if matched is None:
        pass
    elif matched.empty:
        if st.session_state.get('pattern_result_key') == TODAY_MOMENTUM_PATTERN_KEY:
            st.info(t('tab5_today_momentum_empty', lang))
        else:
            st.info(t('tab5_no_match', lang))
    else:
        start, end = st.session_state['pattern_range']
        st.caption(t('tab5_result_caption', lang, start=start.date(), end=end.date(), n=len(matched)))
        result_key = st.session_state.get('pattern_result_key')
        show_cols = ['Name', 'Close', 'Sector', 'Marcap', 'PER']
        if result_key == BREAKOUT_PATTERN_KEY:
            show_cols.append('BreakoutReturn')
            st.caption(t('tab5_breakout_note', lang))
            st.warning(t('tab5_breakout_disclaimer', lang))
        elif result_key == HALT_PATTERN_KEY:
            show_cols += ['HaltStartDate', 'HaltDays']
            st.caption(t('tab5_halt_note', lang))
        elif result_key == RALLY_PULLBACK_PATTERN_KEY:
            st.warning(t('tab5_rally_pullback_disclaimer', lang))
        elif result_key == TODAY_MOMENTUM_PATTERN_KEY:
            show_cols += ['MatchedPattern', 'Score4', 'Score6']
            st.caption(t('tab5_today_momentum_note', lang))
            st.warning(t('tab5_today_momentum_disclaimer', lang))
        elif result_key == BOTTOM_REBOUND_PATTERN_KEY:
            show_cols.append('ReboundReturn')
            st.caption(t('tab5_bottom_rebound_note', lang))
            st.warning(t('tab5_bottom_rebound_disclaimer', lang))
        col_map = {c: col_label(c, lang) for c in show_cols}
        col_map['Close'] = t('tab5_price_col', lang)
        display_matched = matched[show_cols].copy()
        display_matched['Close'] = display_matched['Close'].apply(
            lambda v: f'{v:,.0f}' if pd.notna(v) else v,
        )
        display_matched['Marcap'] = display_matched['Marcap'].apply(
            lambda v: f'{v / 1e8:,.0f}억' if pd.notna(v) else v,
        )
        if 'BreakoutReturn' in display_matched.columns:
            display_matched['BreakoutReturn'] = display_matched['BreakoutReturn'].round(1)
        if 'ReboundReturn' in display_matched.columns:
            display_matched['ReboundReturn'] = display_matched['ReboundReturn'].round(1)
        if 'HaltStartDate' in display_matched.columns:
            display_matched['HaltStartDate'] = display_matched['HaltStartDate'].dt.strftime('%Y-%m-%d')
        for c in ('Score4', 'Score6'):
            if c in display_matched.columns:
                display_matched[c] = display_matched[c].round(2)
        display_matched = display_matched.rename(columns=col_map)

        chart_col = t('tab5_chart_col', lang)
        display_matched[chart_col] = (
            'https://finance.naver.com/item/main.naver?code=' + matched['Code']
        )
        st.dataframe(
            display_matched, use_container_width=True, hide_index=True,
            column_config={
                chart_col: st.column_config.LinkColumn(
                    chart_col, display_text=t('tab5_chart_link_text', lang),
                ),
            },
        )

        st.divider()
        st.markdown(t('tab5_chart_viewer_header', lang))
        chart_df = st.session_state.get('pattern_chart_df')
        if chart_df is not None and not chart_df.empty:
            pick_options = matched[['Code', 'Name']].drop_duplicates().reset_index(drop=True)
            pick_labels = [f"{r['Name']} ({r['Code']})" for _, r in pick_options.iterrows()]
            picked_label = st.selectbox(
                t('tab5_chart_pick_label', lang), pick_labels, key='pattern_chart_pick',
            )
            picked_code = pick_options.iloc[pick_labels.index(picked_label)]['Code']
            series = chart_df[chart_df['Code'] == picked_code].sort_index()['Close']
            st.line_chart(series)
            st.caption(t('tab5_chart_viewer_caption', lang, start=start.date(), end=end.date()))
