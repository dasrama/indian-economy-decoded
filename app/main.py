from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.api.router import api_router
from app.config.config import settings
from app.config.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode")
    settings.ensure_directories()
    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend API for RBI India Economic Indicators Dashboard. "
        "Provides automated ingestion, storage, time series retrieval, "
        "revision preservation, and chart-ready metrics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root access directly to interactive Swagger API documentation."""
    return RedirectResponse(url="/docs")

