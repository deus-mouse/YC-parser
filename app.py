from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from parser import MasterAvailability, YClientsParser
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


class ScanResponse(BaseModel):
    url: str
    days: int
    total_masters: int
    items: list[dict]


def serialize_master(master: MasterAvailability) -> dict:
    return {
        "name": master.name,
        "shortest_service_name": master.shortest_service_name,
        "shortest_service_duration_min": master.shortest_service_duration_min,
        "total_slots": master.total_slots,
        "total_free_minutes": master.total_free_minutes,
        "days_with_slots": master.days_with_slots,
        "scanned_days": [
            {
                "date": day.date,
                "slots": day.slots,
                "free_minutes": day.free_minutes,
            }
            for day in master.scanned_days
        ],
    }


def run_scan_sync(payload: ScanRequest) -> ScanResponse:
    logger.info("scan_sync:start url=%s days=%s", payload.url, payload.days)
    with YClientsParser(
        masters_url=payload.url,
        days_ahead=payload.days,
        headless=True,
    ) as parser:
        logger.info("scan_sync:parser_started")
        results = parser.parse()
        logger.info("scan_sync:parse_finished masters=%s", len(results))

    items = [serialize_master(item) for item in results]
    logger.info("scan_sync:serialized items=%s", len(items))
    return ScanResponse(
        url=payload.url,
        days=payload.days,
        total_masters=len(items),
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
async def scan(payload: ScanRequest) -> ScanResponse:
    logger.info("scan_request:start url=%s days=%s", payload.url, payload.days)
    try:
        response = await asyncio.to_thread(run_scan_sync, payload)
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
