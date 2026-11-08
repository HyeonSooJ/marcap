"""간단한 비밀번호 로그인.

APP_PASSWORD 환경변수가 설정되어 있으면 모든 화면과 /api 요청에 로그인이 필요합니다.
인터넷에 공개(클라우드 배포)할 때는 반드시 설정하세요. REQUIRE_PASSWORD=1 이면
비밀번호 없이 서버가 시작되지 않습니다.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

COOKIE = "kt_session"
SESSION_SECONDS = 3 * 24 * 3600
PUBLIC_PATHS = {"/login", "/api/login", "/static/css/style.css", "/static/js/login.js", "/healthz"}

PASSWORD = os.getenv("APP_PASSWORD", "")
SECRET = (os.getenv("SESSION_SECRET") or secrets.token_hex(32)).encode()

if os.getenv("REQUIRE_PASSWORD") == "1" and len(PASSWORD) < 8:
    raise RuntimeError("APP_PASSWORD 를 8자 이상으로 설정해야 합니다 (REQUIRE_PASSWORD=1).")

_fail_count = 0
_locked_until = 0.0


def enabled() -> bool:
    return bool(PASSWORD)


def _sign(exp: int) -> str:
    # 비밀번호가 바뀌면 기존 세션도 무효화되도록 비밀번호 해시를 서명에 포함
    msg = f"{exp}:{hashlib.sha256(PASSWORD.encode()).hexdigest()}".encode()
    return hmac.new(SECRET, msg, hashlib.sha256).hexdigest()


def make_cookie() -> str:
    exp = int(time.time()) + SESSION_SECONDS
    return f"{exp}.{_sign(exp)}"


def is_valid(cookie: str | None) -> bool:
    if not cookie or "." not in cookie:
        return False
    exp_s, sig = cookie.split(".", 1)
    if not exp_s.isdigit() or int(exp_s) < time.time():
        return False
    return hmac.compare_digest(sig, _sign(int(exp_s)))


def check_password(pw: str) -> tuple[bool, str]:
    """연속 5회 실패하면 60초 동안 로그인 시도를 막습니다 (무차별 대입 방지)."""
    global _fail_count, _locked_until
    now = time.time()
    if now < _locked_until:
        return False, f"로그인 시도가 너무 많습니다. {int(_locked_until - now)}초 후 다시 시도하세요."
    if hmac.compare_digest(pw.encode(), PASSWORD.encode()):
        _fail_count = 0
        return True, ""
    _fail_count += 1
    if _fail_count >= 5:
        _fail_count = 0
        _locked_until = now + 60
    return False, "비밀번호가 올바르지 않습니다."


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


async def middleware(request: Request, call_next):
    if not enabled() or request.url.path in PUBLIC_PATHS or is_valid(request.cookies.get(COOKIE)):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "로그인이 필요합니다."}, status_code=401)
    return RedirectResponse("/login", status_code=303)
