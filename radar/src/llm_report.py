# -*- coding: utf-8 -*-
"""이상탐지 결과 + 공시/뉴스 컨텍스트를 LLM(Claude)에 넣어 원인 해설 리포트를 생성한다.

환경변수 ANTHROPIC_API_KEY 가 필요하다. https://console.anthropic.com 에서 발급.
비용 절감을 위해 하루 상위 N개(기본 top_n=10) 이상신호 종목에 대해서만 호출하도록
pipeline.py에서 스코프를 제한한다.
"""

import os

REPORT_MODEL = os.environ.get('RADAR_LLM_MODEL', 'claude-sonnet-5')


def _extract_text(message):
    """Claude 응답에서 텍스트 블록을 뽑아 이어붙인다.

    확장 씽킹(extended thinking)이 켜진 모델은 content[0]이 텍스트가 아니라
    ThinkingBlock일 수 있어, 인덱스로 고정하면 'ThinkingBlock' object has no
    attribute 'text' 로 깨진다. type == 'text'인 블록만 골라 이어붙인다.
    """
    parts = [block.text for block in message.content if getattr(block, 'type', None) == 'text']
    return '\n'.join(parts)

SYSTEM_PROMPT = """\
당신은 한국거래소 상장기업 리스크를 분석하는 애널리스트입니다.
주어진 통계적 이상탐지 결과와 최근 공시·뉴스 정보를 바탕으로, 왜 해당 종목의 시가총액/주가/
거래량이 이상 변동을 보였는지 가능한 원인을 간결하게 설명하세요.

규칙:
- 확인되지 않은 사실을 단정하지 말고, 근거(공시/뉴스)가 있는 부분과 추정인 부분을 구분하세요.
- 공시/뉴스에서 뚜렷한 원인을 찾지 못했다면 "확인된 공시·뉴스 근거 없음"이라고 명시하세요.
- 투자 조언이 아닌 리스크 모니터링 참고 자료임을 유의하고, 매수/매도 추천은 하지 마세요.
- 출력은 아래 4개 항목의 한국어 마크다운으로 작성하세요:
  1. **한줄 요약**
  2. **이상신호 내용** (어떤 지표가 왜 이상치인지)
  3. **추정 원인** (공시/뉴스 근거 인용, 없으면 명시)
  4. **리스크 등급** (낮음/중간/높음 중 하나 + 한 줄 근거)
"""


def _build_user_prompt(anomaly_row, disclosures, news_items):
    lines = [
        f"### 종목: {anomaly_row.get('Name')} ({anomaly_row.get('Code')})",
        f"- 날짜: {anomaly_row.get('Date', '')}",
        f"- 종가: {anomaly_row.get('Close')} / 등락률: {anomaly_row.get('ChangesRatio')}%",
        f"- 거래량: {anomaly_row.get('Volume')}",
        f"- 시가총액: {anomaly_row.get('Marcap')}",
        f"- 시가총액순위: {anomaly_row.get('Rank')}",
        f"- 소속부(Dept): {anomaly_row.get('Dept')}",
        f"- 종합 이상점수: {anomaly_row.get('AnomalyScore'):.2f} (주요 원인 지표: {anomaly_row.get('AnomalyReason')})",
        '',
        '### 최근 공시 (DART)',
    ]
    if disclosures is None or len(disclosures) == 0:
        lines.append('- 없음')
    else:
        for _, d in disclosures.iterrows():
            lines.append(f"- [{d['rcept_dt']}] {d['report_nm']} ({d['flr_nm']})")

    lines.append('')
    lines.append('### 최근 뉴스')
    if not news_items:
        lines.append('- 없음')
    else:
        for n in news_items:
            lines.append(f"- {n['title']} — {n['description']}")

    return '\n'.join(lines)


def generate_report(anomaly_row, disclosures=None, news_items=None, client=None):
    """단일 종목에 대한 LLM 원인 해설 리포트를 생성한다.

    :param anomaly_row: detect_anomalies() 결과 한 행 (dict-like)
    :param disclosures: dart_collector.get_disclosures() 결과 DataFrame (optional)
    :param news_items: news_collector.get_recent_news() 결과 list (optional)
    :param client: anthropic.Anthropic 인스턴스 (미지정 시 자동 생성)
    :return: 마크다운 문자열
    """
    if client is None:
        import anthropic
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

    user_prompt = _build_user_prompt(anomaly_row, disclosures, news_items)
    message = client.messages.create(
        model=REPORT_MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    return _extract_text(message)


PERSONALIZED_SYSTEM_PROMPT = """\
당신은 개인투자자에게 리스크를 설명해주는 금융 코치입니다.
아래 "종목의 시장 관심 확산 진단 결과"와 "사용자의 투자 성향"을 결합해서, 왜 지금
이 사용자에게 이 종목이 특히 주의가 필요할 수 있는지(또는 상대적으로 덜 위험한지)
설명하세요.

규칙:
- 특정 종목을 사라거나 팔라고 지시하지 마세요. 이건 매매 추천이 아니라 위험
  정보 제공입니다.
- 확산 단계 진단(SIR 역학모델을 시장 관심 확산에 적용한 근사 지표)은 절대적
  진실이 아니라 보조 신호임을 인지하고, "~일 수 있습니다" 같은 완곡한 표현을
  쓰세요.
- 사용자의 투자 성향 특징과 현재 확산 단계를 구체적으로 연결해서 설명하세요
  (일반론이 아니라 "당신은 X한 경향이 있는데, 지금 이 종목은 Y 단계라서..." 식으로).
- 출력은 3~4문장의 짧은 한국어 문단 하나로만 작성하세요. 제목이나 목록 없이.
"""


def _build_personalized_prompt(diffusion_summary, profile_key, profile_description):
    return (
        '### 종목 확산 진단\n'
        f"- 종목: {diffusion_summary.get('Name')} ({diffusion_summary.get('Code')})\n"
        f"- 진단일: {diffusion_summary.get('Date')}\n"
        f"- 확산 단계: {diffusion_summary.get('Stage')}\n"
        f"- 실효재생산수(Rt) 추정치: {diffusion_summary.get('Rt'):.2f}\n"
        f"- 관심도 지수(0~1): {diffusion_summary.get('Attention'):.2f}\n\n"
        f'### 사용자 투자 성향: {profile_key}\n'
        f'- 특징: {profile_description}\n'
    )


def generate_personalized_alert(diffusion_summary, profile_key, profile_description, client=None):
    """확산 진단 결과 + 투자 성향을 결합한 개인화 경고 메시지를 생성한다.

    :param diffusion_summary: diffusion_model.diagnose()가 반환하는 요약 dict
        (Code, Name, Date, Attention, GrowthRate, Rt, Stage)
    :param profile_key: investor_profile.classify_profile()이 반환한 유형 문자열
    :param profile_description: investor_profile.PROFILE_DESCRIPTIONS[profile_key]
    :param client: anthropic.Anthropic 인스턴스 (미지정 시 자동 생성)
    :return: 마크다운(짧은 문단) 문자열
    """
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    user_prompt = _build_personalized_prompt(diffusion_summary, profile_key, profile_description)
    message = client.messages.create(
        model=REPORT_MODEL,
        max_tokens=400,
        system=PERSONALIZED_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    return _extract_text(message)
