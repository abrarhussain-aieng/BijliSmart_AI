"""FastAPI application entry point. Serves the API and the static frontend."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api import appliances, assistant, bills, history
from app.database.database import init_db
from app.utils.validators import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="BijliSmart AI", version="1.0.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error")
    return JSONResponse({"detail": "A database error occurred. Please try again."}, status_code=500)


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse({"detail": "Something went wrong on the server."}, status_code=500)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


for router in (bills.router, history.router, appliances.router, assistant.router):
    app.include_router(router)

# Mounted last so API routes take priority. Serves index.html at "/".
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
