"""
FastAPI application entry point for the Patent Search API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, intake, chat
from middleware.request_logging import RequestLoggingMiddleware

app = FastAPI(
    title="Patent Search API",
    description="API for patent prospecting and search",
    version="1.0.0",
)

# Add middleware for request logging and tracking
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api/v1 prefix
app.include_router(health.router, prefix="/api/v1")
app.include_router(intake.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
