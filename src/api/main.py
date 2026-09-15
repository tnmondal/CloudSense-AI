"""
CloudSense AI — High-Performance FastAPI Application Entrypoint
Exposes RESTful endpoints for FinOps cost allocation, resource efficiency,
carbon estimation, statistical anomaly detection, and ML forecasting.
"""

import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.config import settings
from src.api.routers import (
    health,
    dashboard,
    cost,
    usage,
    anomalies,
    optimizations,
    carbon,
    forecast,
    ai_context,
    chat,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cloudsense.api")

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## CloudSense AI REST API
    Enterprise Cloud Cost, Resource Usage & Carbon Intelligence Platform.
    
    ### Key Analytical Capabilities:
    * **Cost Analytics**: Multi-dimensional attribution, unit economics, and spend trends.
    * **Resource Utilization**: CPU, RAM, IOPS, Egress telemetry and load-to-cost elasticity.
    * **Carbon Accounting**: SPECpower TDP model, PUE multipliers, and Scope 2/3 GHG estimates.
    * **Statistical Anomalies**: Interpretable consensus screening (Z-Score, Modified MAD, IQR).
    * **Optimization Engine**: Quantified ROI savings for rightsizing, zombie termination, and storage tiers.
    * **Time-Series Forecasting**: Machine learning cost projections with calibrated confidence bounds.
    * **AI Analyst Grounding**: Pre-computed factual contexts for zero-hallucination GenAI reasoning.
    * **FinOps Copilot Chat**: Conversational Gemini-grounded Q&A over verified analytics, with an offline deterministic fallback.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

# Configure Cross-Origin Resource Sharing (CORS)
# NOTE: allow_credentials is intentionally False. This API has no cookie,
# session, or credential-based authentication anywhere — every endpoint is
# public, read-only demo data (plus the stateless AI Copilot chat endpoint).
# Combining a wildcard allow_origins with allow_credentials=True is an
# unsafe/spec-invalid configuration (it can cause credentialed requests to
# be permitted from any origin); since nothing in this app ever relies on
# credentialed CORS, disabling it removes that risk with no behavior change.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing and logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    logger.info(f"{request.method} {request.url.path} responded {response.status_code} in {process_time:.2f}ms")
    return response


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing the analytical request.",
            "path": request.url.path
        }
    )


# Root Metadata Endpoint
@app.get("/", tags=["System Root"])
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "documentation": "/docs",
        "health_check": f"{settings.api_prefix}/health",
        "dashboard_summary": f"{settings.api_prefix}/dashboard/summary"
    }


# Include Routers under API Prefix (/api/v1)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(cost.router, prefix=settings.api_prefix)
app.include_router(usage.router, prefix=settings.api_prefix)
app.include_router(anomalies.router, prefix=settings.api_prefix)
app.include_router(optimizations.router, prefix=settings.api_prefix)
app.include_router(carbon.router, prefix=settings.api_prefix)
app.include_router(forecast.router, prefix=settings.api_prefix)
app.include_router(ai_context.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
