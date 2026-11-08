"""한국투자증권 Open API (KIS Developers) REST 클라이언트.

참고: https://github.com/koreainvestment/open-trading-api (kis_auth.py 의 토큰 발급/헤더 구성 방식)
사용 API (업로드된 API 문서 기준)
  - 접근토큰발급(P)          POST /oauth2/tokenP
  - 주식현재가 시세          GET  /uapi/domestic-stock/v1/quotations/inquire-price             FHKST01010100
  - 주식현재가 호가/예상체결   GET  /uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn FHKST01010200
  - 국내주식기간별시세        GET  /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice FHKST03010100
  - 거래량순위(실전 전용)     GET  /uapi/domestic-stock/v1/quotations/volume-rank               FHPST01710000
  - 주식주문(현금)           POST /uapi/domestic-stock/v1/trading/order-cash         (매도)TTTC0011U (매수)TTTC0012U
  - 주식주문(정정취소)        POST /uapi/domestic-stock/v1/trading/order-rvsecncl     TTTC0013U
  - 주식일별주문체결조회      GET  /uapi/domestic-stock/v1/trading/inquire-daily-ccld TTTC0081R
  - 주식잔고조회             GET  /uapi/domestic-stock/v1/trading/inquire-balance    TTTC8434R
  - 매수가능조회             GET  /uapi/domestic-stock/v1/trading/inquire-psbl-order TTTC8908R
모의투자(vps) 는 TR_ID 앞자리 T → V 로 바꿔서 호출합니다.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

from .config import Settings
from .stocks import stock_master

log = logging.getLogger(__name__)


class KisError(Exception):
    def __init__(self, message: str, code: str = "", status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def to_int(v: Any) -> int:
    try:
        return int(float(str(v).strip() or 0))
    except (TypeError, ValueError):
        return 0


def to_float(v: Any) -> float:
    try:
        return float(str(v).strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def tick_size(price: int) -> int:
    """KRX 호가가격단위 (2023.01 개편 기준, 코스피·코스닥 공통)."""
    if price < 2000:
        return 1
    if price < 5000:
        return 5
    if price < 20000:
        return 10
    if price < 50000:
        return 50
    if price < 200000:
        return 100
    if price < 500000:
        return 500
    return 1000


SIGN_MAP = {"1": 1, "2": 1, "3": 0, "4": -1, "5": -1}  # 1 상한 2 상승 3 보합 4 하한 5 하락


class KisClient:
    """실전(prod)/모의(vps) 계좌용 실제 API 클라이언트."""

    def __init__(self, settings: Settings):
        self.s = settings
        self._token: str = ""
        self._token_exp: datetime = datetime.min
        self._token_lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._last_call = 0.0
        # 모의투자는 초당 2건, 실전은 초당 20건 제한 → 여유있게 간격 유지
        self._min_interval = 0.55 if settings.env == "vps" else 0.06
        self._http = httpx.AsyncClient(base_url=settings.domain, timeout=10.0)

    async def close(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ 인증
    @property
    def _token_file(self):
        return self.s.token_dir / f"token_{self.s.env}_{self.s.app_key[:8]}.json"

    def _load_cached_token(self) -> None:
        try:
            data = json.loads(self._token_file.read_text(encoding="utf-8"))
            exp = datetime.fromisoformat(data["expires"])
            if exp > datetime.now() + timedelta(minutes=5):
                self._token, self._token_exp = data["token"], exp
        except Exception:
            pass

    async def _get_token(self) -> str:
        async with self._token_lock:
            if not self._token:
                self._load_cached_token()
            if self._token and self._token_exp > datetime.now() + timedelta(minutes=5):
                return self._token
            # 접근토큰은 유효기간 24시간이며 1분당 1회만 발급 가능 → 파일로 캐시해서 재사용
            r = await self._http.post("/oauth2/tokenP", json={
                "grant_type": "client_credentials",
                "appkey": self.s.app_key,
                "appsecret": self.s.app_secret,
            })
            data = r.json()
            if r.status_code != 200 or "access_token" not in data:
                raise KisError(f"접근토큰 발급 실패: {data.get('error_description') or data}", status=502)
            self._token = data["access_token"]
            exp_str = data.get("access_token_token_expired")
            try:
                self._token_exp = datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                self._token_exp = datetime.now() + timedelta(seconds=int(data.get("expires_in", 86400)))
            try:
                self.s.token_dir.mkdir(parents=True, exist_ok=True)
                self._token_file.write_text(json.dumps(
                    {"token": self._token, "expires": self._token_exp.isoformat()}), encoding="utf-8")
                self._token_file.chmod(0o600)
            except OSError as e:
                log.warning("토큰 캐시 저장 실패: %s", e)
            return self._token

    def _tr(self, real_tr_id: str) -> str:
        """실전 TR_ID → 모의투자 TR_ID 변환 (T/C 로 시작하는 주문·계좌 TR 만 V 로 변경)."""
        if self.s.env == "vps" and real_tr_id[0] in "TC":
            return "V" + real_tr_id[1:]
        return real_tr_id

    async def _request(self, method: str, path: str, tr_id: str, *, params: dict | None = None,
                       body: dict | None = None, tr_cont: str = "",
                       _retry: bool = False) -> tuple[dict, dict]:
        token = await self._get_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.s.app_key,
            "appsecret": self.s.app_secret,
            "tr_id": tr_id,
            "tr_cont": tr_cont,
            "custtype": self.s.custtype,
        }
        async with self._rate_lock:
            wait = self._min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        try:
            r = await self._http.request(method, path, headers=headers, params=params, json=body)
        except httpx.HTTPError as e:
            raise KisError(f"KIS 서버 통신 오류: {e}", status=502) from e
        try:
            data = r.json()
        except ValueError:
            raise KisError(f"KIS 응답 파싱 실패 (HTTP {r.status_code})", status=502)
        if data.get("rt_cd") != "0":
            if data.get("msg_cd") in ("EGW00121", "EGW00123") and not _retry:  # 유효하지 않은/만료된 토큰
                self._token = ""
                self._token_file.unlink(missing_ok=True)
                return await self._request(method, path, tr_id, params=params, body=body,
                                           tr_cont=tr_cont, _retry=True)
            raise KisError(data.get("msg1") or str(data), code=data.get("msg_cd", ""))
        return data, dict(r.headers)

    # ------------------------------------------------------------------ 시세
    async def quote(self, code: str) -> dict:
        data, _ = await self._request(
            "GET", "/uapi/domestic-stock/v1/quotations/inquire-price", "FHKST01010100",
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
        o = data["output"]
        price = to_int(o.get("stck_prpr"))
        sign = SIGN_MAP.get(o.get("prdy_vrss_sign", "3"), 0)
        return {
            "code": code,
            "name": stock_master.name(code),
            "market": o.get("rprs_mrkt_kor_name", ""),
            "sector": o.get("bstp_kor_isnm", ""),
            "price": price,
            "change": abs(to_int(o.get("prdy_vrss"))),
            "change_rate": abs(to_float(o.get("prdy_ctrt"))) * (-1 if sign < 0 else 1),
            "sign": sign,
            "open": to_int(o.get("stck_oprc")),
            "high": to_int(o.get("stck_hgpr")),
            "low": to_int(o.get("stck_lwpr")),
            "upper": to_int(o.get("stck_mxpr")),
            "lower": to_int(o.get("stck_llam")),
            "base": to_int(o.get("stck_sdpr")),
            "volume": to_int(o.get("acml_vol")),
            "amount": to_int(o.get("acml_tr_pbmn")),
            "per": to_float(o.get("per")),
            "pbr": to_float(o.get("pbr")),
            "eps": to_float(o.get("eps")),
            "w52_high": to_int(o.get("w52_hgpr")),
            "w52_low": to_int(o.get("w52_lwpr")),
            "frgn_rate": to_float(o.get("hts_frgn_ehrt")),
            "market_cap": to_int(o.get("hts_avls")) * 100_000_000,  # 억원 단위
            "tick": to_int(o.get("aspr_unit")) or tick_size(price),
            "status_code": o.get("iscd_stat_cls_code", ""),
            "time": datetime.now().strftime("%H:%M:%S"),
        }

    async def orderbook(self, code: str) -> dict:
        data, _ = await self._request(
            "GET", "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn", "FHKST01010200",
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
        o1, o2 = data.get("output1", {}), data.get("output2", {})
        asks = [{"price": to_int(o1.get(f"askp{i}")), "qty": to_int(o1.get(f"askp_rsqn{i}"))} for i in range(1, 11)]
        bids = [{"price": to_int(o1.get(f"bidp{i}")), "qty": to_int(o1.get(f"bidp_rsqn{i}"))} for i in range(1, 11)]
        return {
            "code": code,
            "asks": asks,  # asks[0] = 최우선 매도호가
            "bids": bids,  # bids[0] = 최우선 매수호가
            "total_ask": to_int(o1.get("total_askp_rsqn")),
            "total_bid": to_int(o1.get("total_bidp_rsqn")),
            "price": to_int(o2.get("stck_prpr")),
            "base": to_int(o2.get("stck_sdpr")),
            "expected_price": to_int(o2.get("antc_cnpr")),
            "time": o1.get("aspr_acpt_hour", ""),
        }

    async def chart(self, code: str, period: str = "D") -> list[dict]:
        end = datetime.now()
        span = {"D": 150, "W": 7 * 100, "M": 31 * 100, "Y": 366 * 30}[period]
        data, _ = await self._request(
            "GET", "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": (end - timedelta(days=span)).strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "0",
            })
        rows = []
        for o in data.get("output2", []) or []:
            if not o or not o.get("stck_bsop_date"):
                continue
            rows.append({
                "date": o["stck_bsop_date"],
                "open": to_int(o.get("stck_oprc")),
                "high": to_int(o.get("stck_hgpr")),
                "low": to_int(o.get("stck_lwpr")),
                "close": to_int(o.get("stck_clpr")),
                "volume": to_int(o.get("acml_vol")),
            })
        rows.sort(key=lambda x: x["date"])
        return rows

    async def volume_rank(self) -> list[dict]:
        if self.s.env == "vps":
            raise KisError("거래량순위 API 는 모의투자를 지원하지 않습니다.", status=501)
        data, _ = await self._request(
            "GET", "/uapi/domestic-stock/v1/quotations/volume-rank", "FHPST01710000",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "0000000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": "",
            })
        out = []
        for o in data.get("output", []) or data.get("Output", []):
            out.append({
                "rank": to_int(o.get("data_rank")),
                "code": o.get("mksc_shrn_iscd", ""),
                "name": o.get("hts_kor_isnm", ""),
                "price": to_int(o.get("stck_prpr")),
                "change_rate": to_float(o.get("prdy_ctrt")),
                "sign": SIGN_MAP.get(o.get("prdy_vrss_sign", "3"), 0),
                "volume": to_int(o.get("acml_vol")),
            })
        return out

    # ------------------------------------------------------------------ 계좌
    def _acct(self) -> dict:
        return {"CANO": self.s.cano, "ACNT_PRDT_CD": self.s.acnt_prdt_cd}

    async def balance(self) -> dict:
        holdings: list[dict] = []
        summary: dict = {}
        fk = nk = ""
        tr_cont = ""
        for _ in range(5):  # 연속조회 (최대 5페이지)
            data, headers = await self._request(
                "GET", "/uapi/domestic-stock/v1/trading/inquire-balance", self._tr("TTTC8434R"),
                params={**self._acct(),
                        "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
                        "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00",
                        "CTX_AREA_FK100": fk, "CTX_AREA_NK100": nk},
                tr_cont=tr_cont)
            for o in data.get("output1", []):
                qty = to_int(o.get("hldg_qty"))
                if qty <= 0:
                    continue
                holdings.append({
                    "code": o.get("pdno", ""),
                    "name": o.get("prdt_name", ""),
                    "qty": qty,
                    "sellable_qty": to_int(o.get("ord_psbl_qty")),
                    "avg_price": to_float(o.get("pchs_avg_pric")),
                    "price": to_int(o.get("prpr")),
                    "buy_amount": to_int(o.get("pchs_amt")),
                    "eval_amount": to_int(o.get("evlu_amt")),
                    "pnl": to_int(o.get("evlu_pfls_amt")),
                    "pnl_rate": to_float(o.get("evlu_pfls_rt")),
                })
            o2 = (data.get("output2") or [{}])[0]
            summary = {
                "deposit": to_int(o2.get("dnca_tot_amt")),
                "d2_deposit": to_int(o2.get("prvs_rcdl_excc_amt")),
                "stock_eval": to_int(o2.get("scts_evlu_amt")),
                "total_eval": to_int(o2.get("tot_evlu_amt")),
                "buy_amount": to_int(o2.get("pchs_amt_smtl_amt")),
                "pnl": to_int(o2.get("evlu_pfls_smtl_amt")),
                "net_asset": to_int(o2.get("nass_amt")),
            }
            if headers.get("tr_cont") not in ("M", "F"):
                break
            fk, nk, tr_cont = data.get("ctx_area_fk100", ""), data.get("ctx_area_nk100", ""), "N"
        buy = summary.get("buy_amount") or 0
        summary["pnl_rate"] = round(summary.get("pnl", 0) / buy * 100, 2) if buy else 0.0
        return {"summary": summary, "holdings": holdings}

    async def buyable(self, code: str, price: int, ord_dvsn: str) -> dict:
        data, _ = await self._request(
            "GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-order", self._tr("TTTC8908R"),
            params={**self._acct(), "PDNO": code, "ORD_UNPR": str(price if ord_dvsn == "00" else 0),
                    "ORD_DVSN": ord_dvsn, "CMA_EVLU_AMT_ICLD_YN": "N", "OVRS_ICLD_YN": "N"})
        o = data.get("output", {})
        return {
            "cash": to_int(o.get("ord_psbl_cash")),
            "max_qty": to_int(o.get("nrcvb_buy_qty")),  # 미수 없는 매수 수량
            "max_amount": to_int(o.get("nrcvb_buy_amt")),
            "calc_price": to_int(o.get("psbl_qty_calc_unpr")),
        }

    async def order(self, side: str, code: str, qty: int, price: int, ord_dvsn: str) -> dict:
        tr_id = self._tr("TTTC0012U" if side == "buy" else "TTTC0011U")
        body = {**self._acct(), "PDNO": code, "ORD_DVSN": ord_dvsn, "ORD_QTY": str(qty),
                "ORD_UNPR": str(price if ord_dvsn == "00" else 0), "EXCG_ID_DVSN_CD": "KRX"}
        if side == "sell":
            body["SLL_TYPE"] = "01"
        data, _ = await self._request("POST", "/uapi/domestic-stock/v1/trading/order-cash", tr_id, body=body)
        o = data.get("output", {})
        return {"order_no": o.get("ODNO", ""), "org_no": o.get("KRX_FWDG_ORD_ORGNO", ""),
                "time": o.get("ORD_TMD", ""), "message": data.get("msg1", "")}

    async def orders(self) -> list[dict]:
        today = datetime.now().strftime("%Y%m%d")
        out: list[dict] = []
        fk = nk = ""
        tr_cont = ""
        for _ in range(5):
            data, headers = await self._request(
                "GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld", self._tr("TTTC0081R"),
                params={**self._acct(),
                        "INQR_STRT_DT": today, "INQR_END_DT": today, "SLL_BUY_DVSN_CD": "00",
                        "PDNO": "", "ORD_GNO_BRNO": "", "ODNO": "", "CCLD_DVSN": "00",
                        "INQR_DVSN": "00", "INQR_DVSN_1": "", "INQR_DVSN_3": "00",
                        "EXCG_ID_DVSN_CD": "KRX" if self.s.env == "vps" else "ALL",
                        "CTX_AREA_FK100": fk, "CTX_AREA_NK100": nk},
                tr_cont=tr_cont)
            for o in data.get("output1", []):
                if not o.get("odno"):
                    continue
                qty = to_int(o.get("ord_qty"))
                filled = to_int(o.get("tot_ccld_qty"))
                remain = to_int(o.get("rmn_qty"))
                cancelled = o.get("cncl_yn") == "Y"
                out.append({
                    "order_no": o.get("odno", ""),
                    "org_order_no": o.get("orgn_odno", ""),
                    "org_no": o.get("ord_gno_brno", ""),
                    "time": o.get("ord_tmd", ""),
                    "code": o.get("pdno", ""),
                    "name": o.get("prdt_name", ""),
                    "side": "sell" if o.get("sll_buy_dvsn_cd") == "01" else "buy",
                    "type": o.get("ord_dvsn_name", ""),
                    "qty": qty,
                    "price": to_int(o.get("ord_unpr")),
                    "filled_qty": filled,
                    "avg_price": to_int(o.get("avg_prvs")),
                    "remain_qty": remain,
                    "cancelled": cancelled,
                    "cancellable": remain > 0 and not cancelled and to_int(o.get("rjct_qty")) == 0,
                })
            if headers.get("tr_cont") not in ("M", "F"):
                break
            fk, nk, tr_cont = data.get("ctx_area_fk100", ""), data.get("ctx_area_nk100", ""), "N"
        return out

    async def revise_cancel(self, org_no: str, order_no: str, action: str, price: int = 0) -> dict:
        """action: cancel(취소) | amend(정정, 잔량 전부를 새 지정가로)."""
        body = {**self._acct(),
                "KRX_FWDG_ORD_ORGNO": org_no, "ORGN_ODNO": order_no, "ORD_DVSN": "00",
                "RVSE_CNCL_DVSN_CD": "02" if action == "cancel" else "01",
                "ORD_QTY": "0", "ORD_UNPR": str(price if action == "amend" else 0),
                "QTY_ALL_ORD_YN": "Y", "EXCG_ID_DVSN_CD": "KRX"}
        data, _ = await self._request(
            "POST", "/uapi/domestic-stock/v1/trading/order-rvsecncl", self._tr("TTTC0013U"), body=body)
        o = data.get("output", {})
        return {"order_no": o.get("odno") or o.get("ODNO", ""), "message": data.get("msg1", "")}
