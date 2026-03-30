from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from settings_store import SettingsStore, WebSettings


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="YCLIENTS Parser")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
settings_store = SettingsStore(BASE_DIR / "data" / "settings.json")
logger = logging.getLogger("yc_parser")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1)
    days: int = Field(default=30, ge=1, le=180)
    working_hours: str = Field(default="")


class ScanResponse(BaseModel):
    url: str
    days: int
    total_masters: int
    working_hours: str = ""
    total_working_minutes: Optional[int] = None
    total_free_minutes: Optional[int] = None
    occupancy_percent: Optional[float] = None
    items: list[dict]


def parse_working_hours_to_minutes(raw_value: str) -> Optional[int]:
    value = raw_value.strip()
    if not value:
        return None

    match = re.fullmatch(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})", value)
    if not match:
        raise ValueError("Режим работы должен быть в формате HH:MM-HH:MM, например 09:00-21:00.")

    start_hour, start_minute, end_hour, end_minute = (int(part) for part in match.groups())
    start_total = start_hour * 60 + start_minute
    end_total = end_hour * 60 + end_minute
    if end_total <= start_total:
        raise ValueError("Окончание режима работы должно быть позже начала.")
    return end_total - start_total


def run_scan_sync(payload: ScanRequest) -> ScanResponse:
    command = [
        sys.executable,
        str(BASE_DIR / "handler.py"),
        payload.url,
        "--days",
        str(payload.days),
        "--json-only",
    ]
    logger.info("scan_sync:start url=%s days=%s", payload.url, payload.days)
    logger.info("scan_sync:command=%s", command)
    completed = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    if completed.stderr:
        logger.info("scan_sync:stderr\n%s", completed.stderr.strip())
    if completed.returncode != 0:
        stdout_tail = completed.stdout.strip()[-1000:]
        stderr_tail = completed.stderr.strip()[-2000:]
        raise RuntimeError(
            "Парсер завершился с ошибкой. "
            f"code={completed.returncode}. stderr={stderr_tail or '<empty>'}. "
            f"stdout={stdout_tail or '<empty>'}"
        )
    try:
        items = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Не удалось распарсить JSON-ответ парсера. "
            f"stdout={completed.stdout[-2000:]}"
        ) from exc
    logger.info("scan_sync:finished items=%s", len(items))
    daily_working_minutes = parse_working_hours_to_minutes(payload.working_hours)
    total_free_minutes = sum(int(item.get("total_free_minutes", 0)) for item in items)
    total_working_minutes = None
    occupancy_percent = None
    if daily_working_minutes is not None:
        total_working_minutes = daily_working_minutes * payload.days * len(items)
        if total_working_minutes > 0:
            busy_minutes = max(total_working_minutes - total_free_minutes, 0)
            occupancy_percent = round((busy_minutes / total_working_minutes) * 100, 2)
    return ScanResponse(
        url=payload.url,
        days=payload.days,
        total_masters=len(items),
        working_hours=payload.working_hours.strip(),
        total_working_minutes=total_working_minutes,
        total_free_minutes=total_free_minutes,
        occupancy_percent=occupancy_percent,
        items=items,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    settings = settings_store.load()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "defaults": settings.model_dump(),
        },
    )


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> HTMLResponse:
    settings = settings_store.load()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "defaults": settings.model_dump(),
        },
    )


@app.get("/api/settings")
def get_settings() -> dict:
    return settings_store.load().model_dump()


@app.post("/api/settings")
def update_settings(payload: WebSettings) -> dict:
    settings_store.save(payload)
    return payload.model_dump()


@app.post("/api/scan", response_model=ScanResponse)
def scan(payload: ScanRequest) -> ScanResponse:
    logger.info(
        "scan_request:start url=%s days=%s working_hours=%s",
        payload.url,
        payload.days,
        payload.working_hours,
    )
    try:
        response = run_scan_sync(payload)
        logger.info("scan_request:success total_masters=%s", response.total_masters)
        return response
    except Exception as exc:
        logger.exception("scan_request:error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
