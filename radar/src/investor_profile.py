# -*- coding: utf-8 -*-
"""짧은 온보딩 설문으로 투자 성향을 3가지 유형으로 태깅한다 (개인화 레이어, "A-lite").

diffusion_model의 확산 단계 진단(시장/종목 수준 신호)과 결합해 "이 사용자에게 지금 이
종목이 특히 위험한 이유"를 설명하는 데 쓴다. 전체 매매이력을 분석하는 무거운
반사실 시뮬레이터 대신, 5문항 규칙 기반 분류로 범위를 의도적으로 좁혔다
(PROJECT_CONTEXT.md의 "A-lite" 축소안 참고).

내부 유형 키(PROFILE_AVERAGING_DOWN 등)는 언어와 무관한 식별자로 고정하고,
화면에 보여줄 문구만 lang('ko'/'en')에 따라 PROFILE_LABELS/PROFILE_DESCRIPTIONS/
PROFILE_QUESTIONS에서 골라 쓴다.
"""

PROFILE_AVERAGING_DOWN = '물타기형'
PROFILE_MOMENTUM_CHASER = '추격매수형'
PROFILE_BUY_AND_HOLD = '장기보유형'

PROFILE_LABELS = {
    PROFILE_AVERAGING_DOWN: {'ko': '물타기형', 'en': 'Loss-Averager'},
    PROFILE_MOMENTUM_CHASER: {'ko': '추격매수형', 'en': 'Momentum Chaser'},
    PROFILE_BUY_AND_HOLD: {'ko': '장기보유형', 'en': 'Long-Term Holder'},
}

PROFILE_DESCRIPTIONS = {
    PROFILE_AVERAGING_DOWN: {
        'ko': (
            '보유 종목이 하락하면 평균단가를 낮추려 추가 매수하는 경향이 있습니다. '
            '하락 국면이 이미 시작된 종목(정점을 지나 하락기)에 진입하면 손실이 '
            '눈덩이처럼 불어날 위험이 특히 큽니다.'
        ),
        'en': (
            "Tends to buy more when a holding drops, to lower the average cost. "
            "Entering a stock that's already past its peak and declining carries "
            "an especially high risk of snowballing losses."
        ),
    },
    PROFILE_MOMENTUM_CHASER: {
        'ko': (
            '화제성/급등에 이끌려 뒤늦게 진입하는 경향이 있습니다. 이미 관심이 '
            '포화 상태이거나 확산 후기에 접어든 종목을 고점 근처에서 매수하게 될 '
            '위험이 특히 큽니다.'
        ),
        'en': (
            'Tends to jump in late, drawn by hype or a sudden surge. Especially at '
            'risk of buying near the top when attention is already saturated or in '
            'its late diffusion phase.'
        ),
    },
    PROFILE_BUY_AND_HOLD: {
        'ko': (
            '단기 변동에 비교적 영향을 덜 받고 장기 보유하는 경향이 있습니다. '
            '다만 확산 초기가 아니라 이미 정점을 지난 시점에 매수를 시작하면, '
            '장기 손실 국면에 그대로 노출될 위험이 있습니다.'
        ),
        'en': (
            'Relatively unaffected by short-term swings and holds for the long run. '
            "Still, starting a position after the peak rather than in the early "
            'growth phase risks staying exposed through a prolonged downturn.'
        ),
    },
}

# (질문, [(보기 텍스트, {유형: 가중치}), ...]) - 언어별로 문구만 다르고 가중치 구조는 동일
PROFILE_QUESTIONS = {
    'ko': [
        (
            '관심 없던 종목이 갑자기 급등하며 화제가 되면?',
            [
                ('놓칠까봐 바로 따라 산다', {PROFILE_MOMENTUM_CHASER: 2}),
                ('왜 오르는지 확인하고 신중히 판단한다', {PROFILE_BUY_AND_HOLD: 1}),
                ('오히려 불안해서 안 산다', {PROFILE_BUY_AND_HOLD: 1}),
            ],
        ),
        (
            '보유 종목이 매수 후 -15% 하락했다면?',
            [
                ('평균단가를 낮추려 추가 매수한다', {PROFILE_AVERAGING_DOWN: 2}),
                ('손실을 확정하더라도 빠르게 매도한다', {PROFILE_MOMENTUM_CHASER: 1}),
                ('원래 계획대로 계속 보유한다', {PROFILE_BUY_AND_HOLD: 2}),
            ],
        ),
        (
            '투자 결정에 가장 큰 영향을 주는 정보는?',
            [
                ('실시간 커뮤니티/뉴스 반응', {PROFILE_MOMENTUM_CHASER: 2}),
                ('기업 펀더멘털과 장기 전망', {PROFILE_BUY_AND_HOLD: 2}),
                ('내 평균단가와 현재가의 차이', {PROFILE_AVERAGING_DOWN: 2}),
            ],
        ),
        (
            '하루에 보유 종목 주가를 몇 번 확인하나요?',
            [
                ('수시로, 실시간으로 확인한다', {PROFILE_MOMENTUM_CHASER: 1}),
                ('하루 한두 번 확인한다', {PROFILE_AVERAGING_DOWN: 1}),
                ('거의 안 본다 (주 1회 이하)', {PROFILE_BUY_AND_HOLD: 1}),
            ],
        ),
        (
            '투자할 때 염두에 두는 기간은?',
            [
                ('단기 시세차익 (며칠~몇 주)', {PROFILE_MOMENTUM_CHASER: 2}),
                ('손실을 만회할 때까지 (몇 개월~1년)', {PROFILE_AVERAGING_DOWN: 1}),
                ('장기 계획 보유 (1년 이상)', {PROFILE_BUY_AND_HOLD: 2}),
            ],
        ),
    ],
    'en': [
        (
            "When a stock you weren't watching suddenly surges and starts trending, you...",
            [
                ('buy immediately, afraid of missing out', {PROFILE_MOMENTUM_CHASER: 2}),
                ('check why it is rising and decide carefully', {PROFILE_BUY_AND_HOLD: 1}),
                ('feel uneasy about it and avoid buying', {PROFILE_BUY_AND_HOLD: 1}),
            ],
        ),
        (
            'If a stock you hold drops -15% after you bought it, you...',
            [
                ('buy more to lower your average cost', {PROFILE_AVERAGING_DOWN: 2}),
                ('sell quickly even if it locks in the loss', {PROFILE_MOMENTUM_CHASER: 1}),
                ('keep holding as originally planned', {PROFILE_BUY_AND_HOLD: 2}),
            ],
        ),
        (
            'What influences your investment decisions the most?',
            [
                ('real-time community chatter / news reactions', {PROFILE_MOMENTUM_CHASER: 2}),
                ('company fundamentals and long-term outlook', {PROFILE_BUY_AND_HOLD: 2}),
                ('the gap between my average cost and the current price', {PROFILE_AVERAGING_DOWN: 2}),
            ],
        ),
        (
            'How often do you check your holdings’ prices in a day?',
            [
                ('constantly, in real time', {PROFILE_MOMENTUM_CHASER: 1}),
                ('once or twice a day', {PROFILE_AVERAGING_DOWN: 1}),
                ('rarely (once a week or less)', {PROFILE_BUY_AND_HOLD: 1}),
            ],
        ),
        (
            'What time horizon do you usually invest for?',
            [
                ('short-term gains (days to weeks)', {PROFILE_MOMENTUM_CHASER: 2}),
                ('until losses are recovered (months to a year)', {PROFILE_AVERAGING_DOWN: 1}),
                ('long-term holding (1+ years)', {PROFILE_BUY_AND_HOLD: 2}),
            ],
        ),
    ],
}


def classify_profile(answer_indices, lang='ko'):
    """설문 응답으로부터 투자 성향 유형을 분류한다.

    :param answer_indices: PROFILE_QUESTIONS[lang]과 같은 길이의 리스트. 각 원소는
        해당 질문에서 고른 보기의 인덱스(0-based).
    :param lang: 'ko' 또는 'en' (질문 개수 검증에만 쓰임, 가중치 구조는 언어 무관)
    :return: (분류된 유형 문자열(내부 키), {유형: 점수} 전체 스코어 dict)
    """
    questions = PROFILE_QUESTIONS[lang]
    if len(answer_indices) != len(questions):
        raise ValueError(
            f'응답 개수({len(answer_indices)})가 질문 개수({len(questions)})와 다릅니다.'
        )

    scores = {PROFILE_AVERAGING_DOWN: 0, PROFILE_MOMENTUM_CHASER: 0, PROFILE_BUY_AND_HOLD: 0}
    for (_, options), choice_idx in zip(questions, answer_indices):
        _, weights = options[choice_idx]
        for profile, weight in weights.items():
            scores[profile] += weight

    # 동점이면 "물타기형 > 추격매수형 > 장기보유형" 순으로 보수적으로 우선한다
    # (물타기/추격매수가 리스크 관점에서 더 눈여겨봐야 할 성향이라 애매하면 그쪽으로 태깅).
    priority = [PROFILE_AVERAGING_DOWN, PROFILE_MOMENTUM_CHASER, PROFILE_BUY_AND_HOLD]
    best = max(priority, key=lambda p: (scores[p], -priority.index(p)))
    return best, scores


STAGE_LABELS = {
    '초기 확산기': {'ko': '초기 확산기', 'en': 'Early Growth'},
    '포화기': {'ko': '포화기', 'en': 'Saturation'},
    '정점 지나 하락기': {'ko': '정점 지나 하락기', 'en': 'Post-Peak Decline'},
    '평시': {'ko': '평시', 'en': 'Baseline'},
}

STAGE_FALLBACK_NOTES = {
    '초기 확산기': {
        'ko': '시장 관심이 막 늘어나기 시작한 단계로 진단됩니다.',
        'en': 'Market attention appears to be just starting to build (early growth stage).',
    },
    '포화기': {
        'ko': '관심이 최근 고점 근처에 머무르고 있어, 상승 동력이 둔화될 수 있는 단계로 진단됩니다.',
        'en': 'Attention is hovering near its recent peak, so upward momentum may be slowing (saturation stage).',
    },
    '정점 지나 하락기': {
        'ko': '관심이 정점을 지나 줄어들고 있는 단계로 진단됩니다.',
        'en': 'Attention appears to have passed its peak and is now declining (post-peak decline stage).',
    },
    '평시': {
        'ko': '뚜렷한 확산/하락 신호 없이 평시 수준으로 진단됩니다.',
        'en': 'No clear diffusion or decline signal; attention is at baseline levels.',
    },
}


def build_fallback_alert(diffusion_summary, profile_key, lang='ko'):
    """ANTHROPIC_API_KEY가 없을 때 쓰는 규칙 기반 대체 경고 문구.

    llm_report.generate_personalized_alert와 동일한 입력을 받아, LLM 없이도
    데모/오프라인 환경에서 개인화 메시지 형태를 보여줄 수 있게 한다 (기존
    pipeline.py의 "키 없으면 단계적으로 기능이 줄어드는" 패턴과 동일한 취지).
    """
    name = diffusion_summary.get('Name', '해당 종목' if lang == 'ko' else 'this stock')
    stage = diffusion_summary.get('Stage')
    stage_note = STAGE_FALLBACK_NOTES.get(stage, {}).get(
        lang, f"'{stage}'" if lang == 'ko' else f'"{stage}"',
    )
    profile_label = PROFILE_LABELS.get(profile_key, {}).get(lang, profile_key)
    profile_note = PROFILE_DESCRIPTIONS.get(profile_key, {}).get(lang, '')

    if lang == 'en':
        return (
            f'[Rule-based notice — ANTHROPIC_API_KEY not set] {name}: {stage_note} '
            f"Your investor profile was classified as '{profile_label}'. {profile_note} "
            'This diagnosis is a reference indicator only and does not recommend buying or '
            'selling any specific stock. Investment decisions and their outcomes are your own responsibility.'
        )
    return (
        f'[규칙 기반 안내 — ANTHROPIC_API_KEY 미설정] {name}은(는) 현재 {stage_note} '
        f"입력하신 투자 성향은 '{profile_label}'입니다. {profile_note} "
        '이 진단은 참고용 보조 지표이며 특정 종목의 매수/매도를 권유하지 않습니다. '
        '투자 판단과 그 결과는 본인 책임입니다.'
    )
