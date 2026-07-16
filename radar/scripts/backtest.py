# -*- coding: utf-8 -*-
"""이상탐지 모델의 조기경보 성능을 marcap 과거 데이터로 백테스트한다.

사용법:
    python radar/scripts/backtest.py --start 2022-01-01 --end 2026-07-01
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.anomaly_detector import backtest_early_warning  # noqa: E402
from marcap_utils import marcap_data  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2022-01-01')
    parser.add_argument('--end', default='2026-07-01')
    parser.add_argument('--lookback-days', type=int, default=20)
    parser.add_argument('--threshold', type=float, default=3.0)
    args = parser.parse_args()

    print(f'[1/3] marcap 데이터 로딩 중... ({args.start} ~ {args.end})')
    df = marcap_data(args.start, args.end)
    print(f'  -> {len(df):,} rows, {df["Code"].nunique():,} codes')

    print('[2/3] 이상탐지 + 백테스트 실행 중... (몇 분 걸릴 수 있습니다)')
    result_df, summary = backtest_early_warning(
        df, lookback_days=args.lookback_days, threshold=args.threshold,
    )

    print('[3/3] 결과')
    print('-' * 50)
    print(f'검증 기간          : {args.start} ~ {args.end}')
    print(f'위험지정 이벤트 수  : {summary["n_events"]}')
    print(f'조기탐지 커버리지   : {summary["coverage"] * 100:.1f}%')
    print(f'평균 리드타임(영업일): {summary["avg_lead_days"]:.1f}일')
    print('-' * 50)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'backtest_result.csv')
    result_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'상세 결과 저장: {out_path}')


if __name__ == '__main__':
    main()
