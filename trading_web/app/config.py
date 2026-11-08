"""환경설정 로더.

설정은 환경변수 또는 trading_web/.env 파일에서 읽습니다.
APP_KEY/APP_SECRET/ACCOUNT 가 하나라도 비어 있으면 DEMO(가상 시뮬레이션) 모드로 동작합니다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DOMAINS = {
    "prod": "https://openapi.koreainvestment.com:9443",  # 실전투자
    "vps": "https://openapivts.koreainvestment.com:29443",  # 모의투자
}


def _load_dotenv(path: Path) -> None:
    """의존성 없이 KEY=VALUE 형식의 .env 파일을 읽어 os.environ 에 채웁니다 (기존 값 우선)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    env: str  # "prod" | "vps" | "demo"
    app_key: str
    app_secret: str
    cano: str  # 종합계좌번호 앞 8자리
    acnt_prdt_cd: str  # 계좌상품코드 뒤 2자리
    custtype: str
    token_dir: Path

    @property
    def is_demo(self) -> bool:
        return self.env == "demo"

    @property
    def domain(self) -> str:
        return DOMAINS[self.env]

    @property
    def masked_account(self) -> str:
        if not self.cano:
            return "DEMO-00"
        return f"{self.cano[:4]}****-{self.acnt_prdt_cd}"


def load_settings() -> Settings:
    _load_dotenv(BASE_DIR / ".env")

    env = os.getenv("KIS_ENV", "vps").strip().lower()
    app_key = os.getenv("KIS_APP_KEY", "").strip()
    app_secret = os.getenv("KIS_APP_SECRET", "").strip()
    account = os.getenv("KIS_ACCOUNT", "").strip().replace(" ", "")

    cano, prdt = "", ""
    if account:
        digits = account.replace("-", "")
        cano, prdt = digits[:8], (digits[8:10] or "01")

    if env not in ("prod", "vps", "demo"):
        raise ValueError("KIS_ENV 는 prod / vps / demo 중 하나여야 합니다.")
    if env != "demo" and not (app_key and app_secret and cano):
        env = "demo"

    return Settings(
        env=env,
        app_key=app_key,
        app_secret=app_secret,
        cano=cano,
        acnt_prdt_cd=prdt,
        custtype=os.getenv("KIS_CUSTTYPE", "P"),
        token_dir=Path(os.getenv("KIS_TOKEN_DIR", str(BASE_DIR / ".tokens"))),
    )
