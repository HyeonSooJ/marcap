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
DIVISIONS = ["국내주식형", "연금형", "글로벌형", "자율투자형"]
TOP_N = 30

# pykrx의 get_etf_ohlcv_by_ticker()(전종목 일괄조회)가 통째로 빠뜨리는 종목들.
# 개별조회(get_etf_ohlcv_by_date)로는 정상 조회되는 걸 확인했음 (2026-09-27 확인).
# 아래 3개는 상장폐지가 확정돼 있어 애초에 조회가 불가능하므로 목록에서 제외함:
#   - "TIME 미국배당다우존스액티브" (0036D0)
#   - "RISE 국채선물5년추종" (397420, 2026-08-19 상장폐지)
#   - "PLUS 글로벌AI인프라" (489010, 2026-08-26 상장폐지)
SUPPLEMENTAL_TICKERS = {
    "0198D0": "1Q SK하이닉스선물단일종목레버리지",
    "0198B0": "1Q 삼성전자선물단일종목레버리지",
    "0194T0": "ACE SK하이닉스단일종목레버리지",
    "0194M0": "ACE 삼성전자단일종목레버리지",
    "0194R0": "KIWOOM SK하이닉스선물단일종목레버리지",
    "0194N0": "KIWOOM 삼성전자선물단일종목레버리지",
    "0193T0": "KODEX SK하이닉스단일종목레버리지",
    "0193W0": "KODEX 삼성전자단일종목레버리지",
    "0193K0": "PLUS 삼성전자단일종목레버리지",
    "0193L0": "PLUS 삼성전자선물단일종목인버스2X",
    "0192L0": "RISE SK하이닉스단일종목레버리지",
    "0192M0": "RISE 삼성전자단일종목레버리지",
    "0197W0": "SOL SK하이닉스단일종목레버리지",
    "0197X0": "SOL SK하이닉스선물단일종목인버스2X",
    "0195S0": "TIGER SK하이닉스단일종목레버리지",
    "0195R0": "TIGER 삼성전자단일종목레버리지",
}


def single_ohlc(ticker, date_str):
    """일괄조회에서 빠진 종목 하나를 개별조회해서 시가/종가를 뽑아낸다."""
    try:
        df = stock.get_etf_ohlcv_by_date(date_str, date_str, ticker)
    except Exception as e:
        print(f"   [보정 실패] {ticker} {date_str}: 조회 중 예외 발생 - {type(e).__name__}: {e}")
        return None, None
    if df is None or df.empty:
        print(f"   [보정 실패] {ticker} {date_str}: 조회 결과 비어있음")
        return None, None
    try:
        return int(df["시가"].iloc[0]), int(df["종가"].iloc[0])
    except (TypeError, ValueError, KeyError) as e:
        print(f"   [보정 실패] {ticker} {date_str}: 시가/종가 파싱 실패 - {type(e).__name__}: {e} / columns={list(df.columns)}")
        return None, None


def load_division_lists():
    """부문별 종목명 목록(dict[부문] = set(종목명))을 반환. 파일이 없으면 None(필터링 안 함)."""
    if not os.path.exists(ELIGIBLE_PATH):
        return None
    with open(ELIGIBLE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    divisions = data.get("divisions")
    if not divisions:
        return None
    return {d: set(names) for d, names in divisions.items()}


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

    open_col = "시가"
    close_col = "종가"
    merged = today_df[[open_col, close_col]].join(
        prev_df[[close_col]], lsuffix="_today", rsuffix="_prev", how="inner"
    )
    merged = merged[merged[f"{close_col}_prev"] > 0]
    merged = merged.dropna(subset=[open_col, f"{close_col}_today", f"{close_col}_prev"])

    div_lists = load_division_lists()
    all_eligible = set().union(*div_lists.values()) if div_lists else None
    SANITY_LIMIT = 100.0  # ETF 하루 등락률이 이 값을 넘으면 데이터 이상으로 간주

    rows = []
    flagged = []
    for ticker, r in merged.iterrows():
        try:
            name = stock.get_etf_ticker_name(ticker)
        except Exception:
            name = ticker
        # 일부 신상품 티커는 get_etf_ticker_name()이 문자열이 아니라 중복된
        # pandas Series를 반환하는 경우가 있어(pykrx 내부 명단 중복), 그런
        # 경우는 여기서 걸러지고 아래 SUPPLEMENTAL_TICKERS 보정 단계에서
        # 하드코딩된 이름으로 개별 재조회된다.
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        if all_eligible is not None and name not in all_eligible:
            continue
        try:
            open_today = int(r[open_col])
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
        intraday_pct = round((close_today - open_today) / open_today * 100, 2) if open_today > 0 else None
        divisions = [d for d in DIVISIONS if div_lists and name in div_lists.get(d, ())] if div_lists else []
        rows.append({
            "name": name,
            "ticker": ticker,
            "pct": pct,
            "intraday_pct": intraday_pct,
            "open_today": open_today,
            "close_today": close_today,
            "close_prev": close_prev,
            "divisions": divisions,
        })

    # 일괄조회(get_etf_ohlcv_by_ticker)에서 통째로 빠지는 신상품군을 개별조회로 보정한다.
    # (merged.index가 아니라 실제로 rows에 반영된 티커 기준: 시세는 있어도 이름 불일치 등으로
    #  메인 루프에서 걸러졌을 수 있으므로 그런 경우도 여기서 다시 보정 시도한다.)
    existing_tickers = {r["ticker"] for r in rows}
    supplemental_added = 0
    print(f"보정 대상 신상품 {len(SUPPLEMENTAL_TICKERS)}개 처리 시작...")
    for ticker, name in SUPPLEMENTAL_TICKERS.items():
        if ticker in existing_tickers:
            print(f"   [보정 불필요] {ticker} {name}: 이미 일괄조회 결과에 포함됨")
            continue
        if all_eligible is not None and name not in all_eligible:
            print(f"   [보정 제외] {ticker} {name}: 대회 명단에 없음")
            continue
        open_today, close_today = single_ohlc(ticker, target)
        _, close_prev = single_ohlc(ticker, prev)
        if close_today is None or close_prev is None or close_prev <= 0:
            continue
        pct = round((close_today - close_prev) / close_prev * 100, 2)
        if abs(pct) > SANITY_LIMIT:
            flagged.append((name, ticker, pct, close_today, close_prev))
            continue
        intraday_pct = round((close_today - open_today) / open_today * 100, 2) if open_today and open_today > 0 else None
        divisions = [d for d in DIVISIONS if div_lists and name in div_lists.get(d, ())] if div_lists else []
        rows.append({
            "name": name,
            "ticker": ticker,
            "pct": pct,
            "intraday_pct": intraday_pct,
            "open_today": open_today,
            "close_today": close_today,
            "close_prev": close_prev,
            "divisions": divisions,
        })
        supplemental_added += 1
    print(f"보정으로 추가된 종목: {supplemental_added}개")

    rows.sort(key=lambda x: x["pct"], reverse=True)

    if flagged:
        print(f"(경고) 등락률이 ±{SANITY_LIMIT}%를 넘어 데이터 이상으로 제외된 종목 {len(flagged)}개:")
        for name, ticker, pct, close_today, close_prev in flagged[:10]:
            print(f"   {name}({ticker}): {pct}%  (당일 {close_today} / 전일 {close_prev})")

    def top_n(entries, reverse):
        s = sorted(entries, key=lambda x: x["pct"], reverse=reverse)[:TOP_N]
        return [{"name": e["name"], "ticker": e["ticker"], "pct": e["pct"], "intraday_pct": e["intraday_pct"]} for e in s]

    by_division = {
        "전체": {"up": top_n(rows, True), "down": top_n(rows, False)},
    }
    for d in DIVISIONS:
        d_rows = [r for r in rows if d in r["divisions"]]
        by_division[d] = {"up": top_n(d_rows, True), "down": top_n(d_rows, False)}

    return {
        "date": f"{target[0:4]}-{target[4:6]}-{target[6:8]}",
        "prev_date": f"{prev[0:4]}-{prev[4:6]}-{prev[6:8]}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(rows),
        "rows": rows,
        "by_division": by_division,
    }


def latest_available_date(tries=10):
    """KRX ETF 시세는 당일 장 마감 이후에도 한동안 미게시 상태일 수 있어서,
    데이터가 실제로 있는 가장 최근 날짜를 오늘부터 거슬러 올라가며 찾는다."""
    d = datetime.today()
    for _ in range(tries):
        ds = d.strftime("%Y%m%d")
        df = stock.get_etf_ohlcv_by_ticker(ds)
        if df is not None and not df.empty:
            return ds
        d -= timedelta(days=1)
    raise RuntimeError("최근 거래일 데이터를 못 찾았습니다.")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else latest_available_date()
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
