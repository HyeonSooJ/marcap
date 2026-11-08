"""DEMO 모드 클라이언트.

API 키가 설정되지 않았을 때 화면·주문 흐름을 확인할 수 있도록
marcap 데이터의 최근 종가를 기준으로 가격을 무작위로 움직이고, 주문은 메모리에서 체결합니다.
실제 증권사로 어떤 요청도 보내지 않습니다.
"""
from __future__ import annotations

import itertools
import random
import time
from datetime import datetime, timedelta

from .kis_client import KisError, now_kst, tick_size
from .stocks import stock_master

START_CASH = 10_000_000


def _round_tick(p: float) -> int:
    t = tick_size(int(p))
    return max(t, int(round(p / t)) * t)


class _Sim:
    def __init__(self, code: str):
        s = stock_master.get(code)
        if not s:
            raise KisError("존재하지 않는 종목코드입니다.", status=404)
        self.code = code
        self.prev_close = s.close or 10000
        self.price = self.prev_close
        self.open = self.high = self.low = self.price
        self.volume = 0
        self.last = time.monotonic()
        self.upper = _round_tick(self.prev_close * 1.3)
        self.lower = _round_tick(self.prev_close * 0.7)

    def step(self) -> None:
        now = time.monotonic()
        n = min(int((now - self.last) / 1.0), 30)  # 1초마다 한 틱
        if n <= 0:
            return
        self.last = now
        for _ in range(n):
            t = tick_size(self.price)
            self.price = min(self.upper, max(self.lower, self.price + random.choice([-2, -1, -1, 0, 0, 1, 1, 2]) * t))
            self.high, self.low = max(self.high, self.price), min(self.low, self.price)
            self.volume += random.randint(50, 3000)


class DemoClient:
    def __init__(self) -> None:
        self.sims: dict[str, _Sim] = {}
        self.cash = START_CASH
        self.holdings: dict[str, dict] = {}  # code -> {qty, avg}
        self._orders: list[dict] = []
        self._seq = itertools.count(1)

    async def close(self) -> None:
        pass

    def _sim(self, code: str) -> _Sim:
        if code not in self.sims:
            self.sims[code] = _Sim(code)
        sim = self.sims[code]
        sim.step()
        self._match(code, sim.price)
        return sim

    # ------------------------------------------------------------------ 시세
    async def quote(self, code: str) -> dict:
        s = self._sim(code)
        st = stock_master.get(code)
        change = s.price - s.prev_close
        return {
            "code": code, "name": st.name, "market": st.market, "sector": "",
            "price": s.price, "change": abs(change),
            "change_rate": round(change / s.prev_close * 100, 2),
            "sign": (change > 0) - (change < 0),
            "open": s.open, "high": s.high, "low": s.low,
            "upper": s.upper, "lower": s.lower, "base": s.prev_close,
            "volume": s.volume, "amount": s.volume * s.price,
            "per": 0, "pbr": 0, "eps": 0, "w52_high": 0, "w52_low": 0, "frgn_rate": 0,
            "market_cap": 0, "tick": tick_size(s.price), "status_code": "",
            "time": now_kst().strftime("%H:%M:%S"),
        }

    async def orderbook(self, code: str) -> dict:
        s = self._sim(code)
        t = tick_size(s.price)
        rnd = random.Random(f"{code}{int(time.time())}")
        asks = [{"price": s.price + t * (i + 1), "qty": rnd.randint(100, 20000)} for i in range(10)]
        bids = [{"price": s.price - t * i, "qty": rnd.randint(100, 20000)} for i in range(10)]
        return {"code": code, "asks": asks, "bids": bids,
                "total_ask": sum(a["qty"] for a in asks), "total_bid": sum(b["qty"] for b in bids),
                "price": s.price, "base": s.prev_close, "expected_price": 0,
                "time": now_kst().strftime("%H%M%S")}

    async def chart(self, code: str, period: str = "D") -> list[dict]:
        s = self._sim(code)
        rnd = random.Random(code + period)
        step = {"D": 1, "W": 7, "M": 30, "Y": 365}[period]
        n = {"D": 100, "W": 100, "M": 100, "Y": 20}[period]
        closes = [float(s.prev_close)]
        for _ in range(n - 1):
            closes.append(closes[-1] / (1 + rnd.gauss(0.0005 * step, 0.02 * step ** 0.5)))
        closes.reverse()
        rows, day = [], now_kst() - timedelta(days=step * n)
        prev = closes[0]
        for c in closes:
            day += timedelta(days=step)
            o = prev
            hi, lo = max(o, c) * (1 + abs(rnd.gauss(0, 0.008))), min(o, c) * (1 - abs(rnd.gauss(0, 0.008)))
            rows.append({"date": day.strftime("%Y%m%d"), "open": _round_tick(o), "high": _round_tick(hi),
                         "low": _round_tick(lo), "close": _round_tick(c), "volume": rnd.randint(10**5, 10**7)})
            prev = c
        rows[-1].update(close=s.price, high=max(rows[-1]["high"], s.high), low=min(rows[-1]["low"], s.low))
        return rows

    async def volume_rank(self) -> list[dict]:
        top = sorted(stock_master.stocks.values(), key=lambda x: -x.volume)[:30]
        out = []
        for i, st in enumerate(top, 1):
            price = self.sims[st.code].price if st.code in self.sims else st.close
            base = st.close or 1
            rate = round((price - base) / base * 100, 2) if st.code in self.sims else \
                round((st.close - st.prev_close) / (st.prev_close or 1) * 100, 2)
            out.append({"rank": i, "code": st.code, "name": st.name, "price": price,
                        "change_rate": rate, "sign": (rate > 0) - (rate < 0), "volume": st.volume})
        return out

    # ------------------------------------------------------------------ 계좌
    def _locked_cash(self) -> int:
        return sum(o["price"] * o["remain_qty"] for o in self._orders
                   if o["side"] == "buy" and o["remain_qty"] > 0 and not o["cancelled"])

    def _locked_qty(self, code: str) -> int:
        return sum(o["remain_qty"] for o in self._orders
                   if o["code"] == code and o["side"] == "sell" and o["remain_qty"] > 0 and not o["cancelled"])

    async def balance(self) -> dict:
        holdings, buy_total, eval_total = [], 0, 0
        for code, h in self.holdings.items():
            price = self._sim(code).price
            buy_amt, eval_amt = int(h["avg"] * h["qty"]), price * h["qty"]
            buy_total += buy_amt
            eval_total += eval_amt
            holdings.append({
                "code": code, "name": stock_master.name(code), "qty": h["qty"],
                "sellable_qty": h["qty"] - self._locked_qty(code),
                "avg_price": round(h["avg"], 2), "price": price, "buy_amount": buy_amt,
                "eval_amount": eval_amt, "pnl": eval_amt - buy_amt,
                "pnl_rate": round((eval_amt - buy_amt) / buy_amt * 100, 2) if buy_amt else 0,
            })
        pnl = eval_total - buy_total
        return {"summary": {
            "deposit": self.cash, "d2_deposit": self.cash, "stock_eval": eval_total,
            "total_eval": self.cash + eval_total, "buy_amount": buy_total, "pnl": pnl,
            "net_asset": self.cash + eval_total,
            "pnl_rate": round(pnl / buy_total * 100, 2) if buy_total else 0.0,
        }, "holdings": holdings}

    async def buyable(self, code: str, price: int, ord_dvsn: str) -> dict:
        s = self._sim(code)
        p = price if ord_dvsn == "00" and price > 0 else s.upper  # 시장가는 상한가 기준으로 계산
        cash = self.cash - self._locked_cash()
        qty = max(cash // p, 0)
        return {"cash": cash, "max_qty": qty, "max_amount": qty * p, "calc_price": p}

    async def order(self, side: str, code: str, qty: int, price: int, ord_dvsn: str) -> dict:
        s = self._sim(code)
        if ord_dvsn == "00":
            if not (s.lower <= price <= s.upper):
                raise KisError(f"주문가격이 가격제한폭({s.lower:,}~{s.upper:,})을 벗어났습니다.")
            if price % tick_size(price):
                raise KisError(f"호가단위({tick_size(price):,}원)에 맞지 않는 가격입니다.")
        if side == "buy":
            need = (price if ord_dvsn == "00" else s.upper) * qty
            if need > self.cash - self._locked_cash():
                raise KisError("주문가능금액을 초과했습니다.")
        else:
            have = self.holdings.get(code, {}).get("qty", 0) - self._locked_qty(code)
            if qty > have:
                raise KisError(f"매도가능수량({have:,}주)을 초과했습니다.")
        no = f"{next(self._seq):010d}"
        self._orders.append({
            "order_no": no, "org_order_no": "", "org_no": "00950",
            "time": now_kst().strftime("%H%M%S"), "code": code, "name": stock_master.name(code),
            "side": side, "type": "지정가" if ord_dvsn == "00" else "시장가", "market": ord_dvsn == "01",
            "qty": qty, "price": price if ord_dvsn == "00" else 0, "filled_qty": 0, "avg_price": 0,
            "remain_qty": qty, "cancelled": False, "cancellable": True,
        })
        self._match(code, s.price)
        return {"order_no": no, "org_no": "00950", "time": now_kst().strftime("%H%M%S"),
                "message": "[DEMO] 주문 전송 완료 되었습니다."}

    def _match(self, code: str, price: int) -> None:
        for o in self._orders:
            if o["code"] != code or o["remain_qty"] <= 0 or o["cancelled"]:
                continue
            fill_ok = o["market"] or (price <= o["price"] if o["side"] == "buy" else price >= o["price"])
            if not fill_ok:
                continue
            q = o["remain_qty"]
            # 지정가 매수는 주문가 이하, 매도는 주문가 이상에서 체결되므로 현재가로 체결
            fill_price = price
            o["avg_price"] = int((o["avg_price"] * o["filled_qty"] + fill_price * q) / (o["filled_qty"] + q))
            o["filled_qty"] += q
            o["remain_qty"] = 0
            o["cancellable"] = False
            h = self.holdings.setdefault(code, {"qty": 0, "avg": 0.0})
            if o["side"] == "buy":
                self.cash -= fill_price * q
                h["avg"] = (h["avg"] * h["qty"] + fill_price * q) / (h["qty"] + q)
                h["qty"] += q
            else:
                self.cash += fill_price * q
                h["qty"] -= q
                if h["qty"] <= 0:
                    del self.holdings[code]

    async def orders(self) -> list[dict]:
        for code in {o["code"] for o in self._orders}:
            self._sim(code)
        return [{k: v for k, v in o.items() if k != "market"} for o in reversed(self._orders)]

    async def revise_cancel(self, org_no: str, order_no: str, action: str, price: int = 0) -> dict:
        o = next((x for x in self._orders if x["order_no"] == order_no), None)
        if not o or not o["cancellable"]:
            raise KisError("정정/취소 가능한 주문이 아닙니다.")
        if action == "cancel":
            o["cancelled"], o["cancellable"] = True, False
            o["remain_qty"] = 0
            return {"order_no": order_no, "message": "[DEMO] 취소 주문이 완료되었습니다."}
        s = self._sim(o["code"])
        if not (s.lower <= price <= s.upper) or price % tick_size(price):
            raise KisError("정정 가격이 올바르지 않습니다.")
        o["price"], o["market"], o["type"] = price, False, "지정가"
        self._match(o["code"], s.price)
        return {"order_no": order_no, "message": "[DEMO] 정정 주문이 완료되었습니다."}
