"""주식 매매 웹사이트 - FastAPI 서버.

실행:  cd trading_web && uvicorn app.main:app --reload
브라우저: http://127.0.0.1:8000
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .config import BASE_DIR, load_settings
from .demo_client import DemoClient
from .kis_client import KisClient, KisError, tick_size
from .stocks import stock_master

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("trading_web")

settings = load_settings()  # .env 를 먼저 읽은 뒤 auth 를 import (APP_PASSWORD 사용)
from . import auth  # noqa: E402

client: KisClient | DemoClient
_bg_tasks: set = set()  # 백그라운드 작업 참조 유지 (GC 방지)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global client
    client = DemoClient() if settings.is_demo else KisClient(settings)
    log.info("모드: %s / 계좌: %s", settings.env, settings.masked_account)
    if isinstance(client, KisClient):
        _bg_tasks.add(asyncio.create_task(client.warmup()))
    yield
    await client.close()


app = FastAPI(title="KIS 주식 매매", lifespan=lifespan,
              docs_url=None if auth.enabled() else "/docs", redoc_url=None,
              openapi_url=None if auth.enabled() else "/openapi.json")
app.middleware("http")(auth.middleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

CODE = Path(..., pattern=r"^[0-9A-Z]{6}$", description="6자리 종목코드")


@app.exception_handler(KisError)
async def kis_error_handler(_: Request, exc: KisError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(BASE_DIR / "static" / "login.html")


class LoginReq(BaseModel):
    password: str = Field(max_length=200)


@app.post("/api/login")
async def login(req: LoginReq, request: Request):
    if not auth.enabled():
        return {"ok": True}
    ok, msg = auth.check_password(req.password)
    if not ok:
        log.warning("로그인 실패")
        raise HTTPException(401, msg)
    res = JSONResponse({"ok": True})
    res.set_cookie(auth.COOKIE, auth.make_cookie(), max_age=auth.SESSION_SECONDS, httponly=True,
                   secure=auth.is_https(request), samesite="strict")
    return res


@app.post("/api/logout")
async def logout():
    res = JSONResponse({"ok": True})
    res.delete_cookie(auth.COOKIE)
    return res


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"ok": True}


@app.get("/api/status")
async def status():
    labels = {"prod": "실전투자", "vps": "모의투자", "demo": "DEMO (가상)"}
    return {"env": settings.env, "env_label": labels[settings.env],
            "account": settings.masked_account, "stock_master_date": stock_master.as_of,
            "auth": auth.enabled(),
            "credit": settings.env == "prod",  # 신용주문은 실전 계좌 전용
            "nxt": settings.env == "prod",  # NXT·SOR 주문은 실전 계좌 전용
            "poll_ms": 1000 if settings.env == "prod" else 3000}


# ---------------------------------------------------------------------- 시세
@app.get("/api/stocks/search")
async def search(q: str = Query(..., min_length=1, max_length=30)):
    return stock_master.search(q)


MARKET = Query("J", pattern="^(J|NX|UN)$", description="J=KRX, NX=NXT, UN=통합")


@app.get("/api/quote/{code}")
async def quote(code: str = CODE, market: str = MARKET):
    return await client.quote(code, market)


@app.get("/api/orderbook/{code}")
async def orderbook(code: str = CODE, market: str = MARKET):
    return await client.orderbook(code, market)


@app.get("/api/chart/{code}")
async def chart(code: str = CODE, period: Literal["D", "W", "M", "Y"] = "D", market: str = MARKET):
    return await client.chart(code, period, market)


@app.get("/api/ranking/volume")
async def volume_rank():
    return await client.volume_rank()


# ---------------------------------------------------------------------- 계좌/주문
@app.get("/api/balance")
async def balance():
    return await client.balance()


@app.get("/api/buyable/{code}")
async def buyable(code: str = CODE, price: int = Query(0, ge=0),
                  ord_dvsn: Literal["00", "01", "03"] = "00",
                  credit: Literal["", "21", "23"] = ""):
    return await client.buyable(code, price, ord_dvsn, credit)


class OrderReq(BaseModel):
    side: Literal["buy", "sell"]
    code: str = Field(pattern=r"^[0-9A-Z]{6}$")
    qty: int = Field(gt=0, le=10_000_000)
    price: int = Field(0, ge=0)
    ord_dvsn: Literal["00", "01", "03"] = Field("00", description="00 지정가, 01 시장가, 03 최유리지정가")
    credit: Literal["", "21", "23", "25", "27"] = Field(
        "", description="'' 현금, 21 자기융자신규, 23 유통융자신규 (매수) / 25 자기융자상환, 27 유통융자상환 (매도)")
    excg: Literal["KRX", "NXT", "SOR"] = Field("KRX", description="KRX, NXT(넥스트레이드), SOR(최선집행)")
    loan_dt: str = Field("", pattern=r"^(\d{8})?$", description="신용 상환 매도 시 대출일자 YYYYMMDD")

    @model_validator(mode="after")
    def check_price(self):
        if self.ord_dvsn == "00":
            if self.price <= 0:
                raise ValueError("지정가 주문은 가격을 입력해야 합니다.")
            if self.price % tick_size(self.price):
                raise ValueError(f"호가단위({tick_size(self.price):,}원)에 맞지 않는 가격입니다.")
        else:
            self.price = 0
        if self.excg == "NXT" and self.ord_dvsn == "01":
            raise ValueError("NXT 는 시장가 주문이 없습니다. 지정가 또는 최유리를 사용하세요.")
        if self.credit:
            if self.side == "buy" and self.credit not in ("21", "23"):
                raise ValueError("신용매수는 자기융자(21)/유통융자(23)만 가능합니다.")
            if self.side == "sell" and (self.credit not in ("25", "27") or not self.loan_dt):
                raise ValueError("신용상환 매도는 상환할 잔고(대출일자)를 선택해야 합니다.")
        return self


@app.post("/api/order")
async def order(req: OrderReq):
    log.info("주문 요청: %s %s %d주 @%s (%s) 신용=%s 거래소=%s", req.side, req.code, req.qty,
             req.price or "시장가", req.ord_dvsn, req.credit or "-", req.excg)
    return await client.order(req.side, req.code, req.qty, req.price, req.ord_dvsn,
                              req.credit, req.loan_dt, req.excg)


@app.get("/api/orders")
async def orders():
    return await client.orders()


class ReviseReq(BaseModel):
    org_no: str = Field(max_length=10)
    order_no: str = Field(min_length=1, max_length=10)
    action: Literal["cancel", "amend"]
    excg: Literal["KRX", "NXT", "SOR"] = "KRX"
    price: int = Field(0, ge=0)


@app.post("/api/order/revise")
async def revise(req: ReviseReq):
    if req.action == "amend" and (req.price <= 0 or req.price % tick_size(req.price)):
        raise HTTPException(422, "정정 가격이 올바르지 않습니다 (호가단위 확인).")
    log.info("정정/취소 요청: %s 주문번호 %s 가격 %s", req.action, req.order_no, req.price)
    return await client.revise_cancel(req.org_no, req.order_no, req.action, req.price, req.excg)
