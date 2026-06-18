"""
MeraCodeLikhDo — FastAPI Application Entry Point
AI-Driven Crop Monitoring & Irrigation Advisory System
ISRO BAH Hackathon 2026
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import crop_map, stress_map, advisory, nlg, pipeline_status
from app.core.config import settings

app = FastAPI(
    title="MeraCodeLikhDo — AI Crop & Irrigation API",
    description=(
        "Satellite-driven precision agriculture API. "
        "Provides crop type classification, phenology-aware moisture stress detection, "
        "water deficit estimation, and multilingual irrigation advisories "
        "using fused optical (Sentinel-2/Landsat) and SAR (Sentinel-1/EOS-04) data."
    ),
    version="1.0.0",
    contact={
        "name": "Team MeraCodeLikhDo",
        "email": "gaurav@meracodelikhdo.in",
    },
    license_info={
        "name": "MIT",
    },
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js frontend on localhost:3000
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(crop_map.router,       prefix="/api/v1/crop-map",    tags=["Crop Classification"])
app.include_router(stress_map.router,     prefix="/api/v1/stress",      tags=["Stress Detection"])
app.include_router(advisory.router,       prefix="/api/v1/advisory",    tags=["Irrigation Advisory"])
app.include_router(nlg.router,            prefix="/api/v1/nlg",         tags=["Multilingual NLG"])
app.include_router(pipeline_status.router,prefix="/api/v1/pipeline",   tags=["Pipeline Status"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "project": "MeraCodeLikhDo — AI Crop Monitoring & Irrigation Advisory",
        "team": "Gaurav Tiwari, Shubham Singh, Prajjwal Singh, Krishna Gupta",
        "hackathon": "ISRO BAH 2026",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
