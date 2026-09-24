# -*- coding: utf-8 -*-
"""
ETF 전종목 일간 등락률을 계산해 data/latest.json (+ data/history/YYYY-MM-DD.json)로 저장한다.
GitHub Actions에서 매 영업일 장 마감 후 자동 실행되는 것을 전제로 하며,
KRX_ID / KRX_PW 환경변수(pykrx 로그인용)가 필요하다.

로컬에서 직접 돌릴 때:
    set KRX_ID=본인아이디
    set KRX_PW=본인비밀번호
    python etf_daily/check.py            # 오늘 날짜
    python etf_daily/check.py 20260922   # 특정 날짜
"""
import json
import os
import sys
from datetime import datetime, timedelta

from pykrx import stock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
ELIGIBLE_PATH = os.path.join(THIS_DIR, "eligible_etfs.json")


def load_eligible_names():
    """제3회 ETF투자왕 대회 투자 가능 종목명 목록 (없으면 필터링 없이 전체 사용)."""
    if not os.path.exists(ELIGIBLE_PATH):
        return None
    with open(ELIGIBLE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("all_names", []))


def prev_business_day(date_str, tries=10):
    d = datetime.strptime(date_str, "%Y%m%d")
    for _ in range(tries):
        d -= timedelta(days=1)
        cand = d.strftime("%Y%m%d")
        df = stock.get_etf_ohlcv_by_ticker(cand)
        if df is not None and not df.empty:
            return cand
    raise RuntimeError("이전 영업일을 못 찾았습니다.")


def build_report(target):
    today_df = stock.get_etf_ohlcv_by_ticker(target)
    if today_df is None or today_df.empty:
        return None

    prev = prev_business_day(target)
    prev_df = stock.get_etf_ohlcv_by_ticker(prev)

    close_col = "종가"
    merged = today_df[[close_col]].join(
        prev_df[[close_col]], lsuffix="_today", rsuffix="_prev", how="inner"
    )
    merged = merged[merged[f"{close_col}_prev"] > 0]
    merged = merged.dropna(subset=[f"{close_col}_today", f"{close_col}_prev"])

    eligible = load_eligible_names()
    SANITY_LIMIT = 100.0  # ETF 하루 등락률이 이 값을 넘으면 데이터 이상으로 간주

    rows = []
    flagged = []
    for ticker, r in merged.iterrows():
        try:
            name = stock.get_etf_ticker_name(ticker)
        except Exception:
            name = ticker
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        if eligible is not None and name not in eligible:
            continue
        try:
            close_today = int(r[f"{close_col}_today"])
            close_prev = int(r[f"{close_col}_prev"])
        except (TypeError, ValueError):
            continue
        if close_prev <= 0:
            continue
        # 실제로 저장/표시되는 종가 값으로 등락률을 다시 계산해서 표시값과 항상 일치시킨다.
        pct = round((close_today - close_prev) / close_prev * 100, 2)
        if abs(pct) > SANITY_LIMIT:
            flagged.append((name, ticker, pct, close_today, close_prev))
            continue
        rows.append({
            "name": name,
            "ticker": ticker,
            "pct": pct,
            "close_today": close_today,
            "close_prev": close_prev,
        })

    rows.sort(key=lambda x: x["pct"], reverse=True)

    if flagged:
        print(f"(경고) 등락률이 ±{SANITY_LIMIT}%를 넘어 데이터 이상으로 제외된 종목 {len(flagged)}개:")
        for name, ticker, pct, close_today, close_prev in flagged[:10]:
            print(f"   {name}({ticker}): {pct}%  (당일 {close_today} / 전일 {close_prev})")

    return {
        "date": f"{target[0:4]}-{target[4:6]}-{target[6:8]}",
        "prev_date": f"{prev[0:4]}-{prev[4:6]}-{prev[6:8]}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(rows),
        "rows": rows,
    }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime("%Y%m%d")
    print(f"기준일: {target}")

    report = build_report(target)
    if report is None:
        print("해당 날짜 데이터가 없습니다 (휴장일이거나 아직 미수집 상태). 종료.")
        return

    os.makedirs(HISTORY_DIR, exist_ok=True)

    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    hist_path = os.path.join(HISTORY_DIR, f"{report['date']}.json")
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    top5 = report["rows"][:5]
    bottom5 = report["rows"][-5:]
    print(f"{report['count']}종목 처리 완료 -> {latest_path}")
    print("상위 5:", [(r["name"], r["pct"]) for r in top5])
    print("하위 5:", [(r["name"], r["pct"]) for r in bottom5])


if __name__ == "__main__":
    main()
