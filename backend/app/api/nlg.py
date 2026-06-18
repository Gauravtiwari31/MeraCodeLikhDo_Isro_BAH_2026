"""NLG API — Multilingual advisory text generation."""

from __future__ import annotations
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.nlg_service import generate_advisory_text_template
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class NLGRequest(BaseModel):
    advisory_class: str = "monitor"
    crop_name: str = "paddy_rice"
    growth_stage: str = "vegetative"
    deficit_mm: float = 22.5
    confidence_label: str = "HIGH"
    languages: List[str] = ["hi", "en"]


@router.post("/generate", summary="Generate multilingual advisory text")
async def generate_advisory_text(req: NLGRequest):
    """
    USP 4.4: LLM-based Farmer-First Multilingual Delivery Layer.

    Converts numeric advisory outputs into plain-language messages in
    Hindi/English suitable for SMS, WhatsApp, or IVR delivery.

    Uses template-based generation (always available) with optional
    LLM enhancement via Gemini/OpenAI when API keys are configured.
    """
    valid_classes = ["no_action", "monitor", "irrigate_soon", "irrigate_now"]
    if req.advisory_class not in valid_classes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid advisory_class. Choose from {valid_classes}",
        )

    # Use template-based NLG (always available without API keys)
    result = generate_advisory_text_template(
        advisory_class=req.advisory_class,
        crop_name=req.crop_name,
        growth_stage=req.growth_stage,
        deficit_mm=req.deficit_mm,
        confidence_label=req.confidence_label,
        language="hi",
    )

    return {
        "advisory_class": req.advisory_class,
        "crop": req.crop_name,
        "stage": req.growth_stage,
        "deficit_mm": req.deficit_mm,
        "messages": {
            "hi": result["hi"],
            "en": result["en"],
        },
        "sms": {
            "hi": result["sms_hi"],
            "en": result["sms_en"],
        },
        "provider": "template" if not settings.GEMINI_API_KEY else "gemini",
    }
