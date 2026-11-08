"""종목 마스터 (종목명 검색용).

이 저장소(marcap)의 data/marcap-YYYY.parquet 중 가장 최근 거래일 데이터를 읽어
종목코드·종목명·시장·시가총액 순위를 메모리에 올립니다.
parquet 을 읽을 수 없으면 소수의 대표 종목만 사용합니다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

REPO_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_FALLBACK = [
    ("005930", "삼성전자", "KOSPI", 70000),
    ("000660", "SK하이닉스", "KOSPI", 180000),
    ("373220", "LG에너지솔루션", "KOSPI", 350000),
    ("207940", "삼성바이오로직스", "KOSPI", 900000),
    ("005380", "현대차", "KOSPI", 220000),
    ("035420", "NAVER", "KOSPI", 190000),
    ("035720", "카카오", "KOSPI", 40000),
    ("068270", "셀트리온", "KOSPI", 180000),
    ("247540", "에코프로비엠", "KOSDAQ", 120000),
    ("086520", "에코프로", "KOSDAQ", 70000),
]


@dataclass
class Stock:
    code: str
    name: str
    market: str
    rank: int
    close: int = 0  # 마지막 데이터 기준 종가 (DEMO 모드 기준가로 사용)
    prev_close: int = 0
    volume: int = 0


class StockMaster:
    def __init__(self) -> None:
        self.stocks: dict[str, Stock] = {}
        self.as_of: str = ""
        self._load()

    def _load(self) -> None:
        files = sorted(REPO_DATA_DIR.glob("marcap-*.parquet"))
        if files:
            try:
                import pandas as pd

                df = pd.read_parquet(files[-1], columns=[
                    "Code", "Name", "Market", "Rank", "Close", "Changes", "Volume", "Date"])
                last = df["Date"].max()
                df = df[df["Date"] == last].sort_values("Rank")
                for r in df.itertuples(index=False):
                    close = int(r.Close or 0)
                    self.stocks[r.Code] = Stock(
                        code=r.Code, name=r.Name, market=r.Market, rank=int(r.Rank),
                        close=close, prev_close=close - int(r.Changes or 0), volume=int(r.Volume or 0))
                self.as_of = str(last)[:10]
                log.info("종목 마스터 로드: %s (%d 종목, %s)", files[-1].name, len(self.stocks), self.as_of)
                return
            except Exception as e:  # pyarrow 미설치 등
                log.warning("parquet 로드 실패, 기본 종목만 사용합니다: %s", e)
        for i, (code, name, market, close) in enumerate(_FALLBACK, 1):
            self.stocks[code] = Stock(code, name, market, i, close, close, 0)

    def get(self, code: str) -> Stock | None:
        return self.stocks.get(code)

    def name(self, code: str) -> str:
        s = self.stocks.get(code)
        return s.name if s else code

    def search(self, q: str, limit: int = 20) -> list[dict]:
        q = q.strip().lower()
        if not q:
            return []
        exact, prefix, contains = [], [], []
        for s in self.stocks.values():  # 시가총액 순으로 정렬되어 있음
            name = s.name.lower()
            code = s.code.lower()
            if code == q or name == q:
                exact.append(s)
            elif code.startswith(q) or name.startswith(q):
                prefix.append(s)
            elif q in name:
                contains.append(s)
        out = (exact + prefix + contains)[:limit]
        return [{"code": s.code, "name": s.name, "market": s.market} for s in out]


stock_master = StockMaster()
