from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .routes import router


app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator",

    description=(
        "AI-powered 7-day workout planning "
        "with Gemini, FastAPI, Jinja2 and SQLite."
    ),

    version="1.0.0",
)


# Static files
app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)


# Application routes
app.include_router(
    router
)


@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "fitbuddy",
    }