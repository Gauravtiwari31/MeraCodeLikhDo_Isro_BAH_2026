"""
Multilingual NLG Advisory Service
===================================
USP 4.4: Farmer-First Multilingual Delivery Layer

Converts numeric deficit/stress/advisory outputs into short, plain-language
messages in Hindi (and other regional languages) for SMS, WhatsApp, or IVR
voice delivery — closing the last-mile gap between a geospatial model and
an actual farmer decision.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in templates (no LLM API key needed for demo)
# ---------------------------------------------------------------------------

ADVISORY_TEMPLATES_HI = {
    "no_action": (
        "🟢 आपके खेत में नमी पर्याप्त है। अभी सिंचाई की जरूरत नहीं है। "
        "अगले 8 दिनों में निगरानी जारी रखें।"
    ),
    "monitor": (
        "🟡 मिट्टी की नमी सामान्य से कम हो रही है। "
        "खेत की जाँच करें और यदि पत्तियाँ मुरझाएं तो सिंचाई की तैयारी करें।"
    ),
    "irrigate_soon": (
        "🟠 पानी की कमी बढ़ रही है — अगले 2-3 दिनों में सिंचाई करें। "
        "उपज को नुकसान से बचाने के लिए समय पर सिंचाई करना जरूरी है।"
    ),
    "irrigate_now": (
        "🔴 गंभीर जल कमी! तुरंत सिंचाई करें। "
        "देर करने से फसल को अपूरणीय नुकसान हो सकता है।"
    ),
}

ADVISORY_TEMPLATES_EN = {
    "no_action": (
        "✅ Field moisture levels are adequate. No irrigation required at this time. "
        "Continue monitoring over the next 8 days."
    ),
    "monitor": (
        "⚠️ Soil moisture is declining below optimal levels. "
        "Check your field and prepare for irrigation if wilting is observed."
    ),
    "irrigate_soon": (
        "🚨 Water deficit is approaching a critical level. "
        "Plan irrigation within the next 2–3 days to protect your yield."
    ),
    "irrigate_now": (
        "🆘 Critical water deficit detected! Irrigate immediately. "
        "Further delay may cause irreversible crop damage and yield loss."
    ),
}

STAGE_NAMES_HI = {
    "pre_sowing":        "बुवाई से पहले",
    "sowing_emergence":  "बुवाई / अंकुरण",
    "vegetative":        "वानस्पतिक अवस्था",
    "flowering_heading": "फूल / बाली अवस्था",
    "maturity_harvest":  "पकाव / कटाई",
}

CROP_NAMES_HI = {
    "paddy_rice":  "धान",
    "wheat":       "गेहूँ",
    "maize":       "मक्का",
    "cotton":      "कपास",
    "sugarcane":   "गन्ना",
    "groundnut":   "मूँगफली",
    "vegetables":  "सब्जियाँ",
    "non_crop":    "अन-कृषि",
    "fallow":      "परती",
}


# ---------------------------------------------------------------------------
# Template-based generator (always available, no API key needed)
# ---------------------------------------------------------------------------

def generate_advisory_text_template(
    advisory_class: str,        # "no_action" | "monitor" | "irrigate_soon" | "irrigate_now"
    crop_name: str,
    growth_stage: str,
    deficit_mm: float,
    confidence_label: str,      # "HIGH" | "MEDIUM" | "LOW"
    language: str = "hi",       # "hi" | "en"
) -> Dict[str, str]:
    """
    Generate advisory text using built-in templates (no external API).
    Always works even in offline / demo mode.
    """
    templates_hi = ADVISORY_TEMPLATES_HI
    templates_en = ADVISORY_TEMPLATES_EN

    base_hi = templates_hi.get(advisory_class, templates_hi["monitor"])
    base_en = templates_en.get(advisory_class, templates_en["monitor"])

    crop_hi = CROP_NAMES_HI.get(crop_name, crop_name)
    stage_hi = STAGE_NAMES_HI.get(growth_stage, growth_stage)

    header_hi = f"📡 उपग्रह सलाह | फसल: {crop_hi} | अवस्था: {stage_hi}\n"
    header_en = f"📡 Satellite Advisory | Crop: {crop_name} | Stage: {growth_stage}\n"

    deficit_hi = f"\n💧 अनुमानित जल कमी: {deficit_mm:.1f} मिमी/8-दिन"
    deficit_en = f"\n💧 Estimated deficit: {deficit_mm:.1f} mm/8-day"

    confidence_hi = f"\n🎯 मॉडल विश्वास: {confidence_label}"
    confidence_en = f"\n🎯 Model confidence: {confidence_label}"

    footer_hi = "\n— टीम MeraCodeLikhDo | ISRO BAH 2026"
    footer_en = "\n— Team MeraCodeLikhDo | ISRO BAH 2026"

    msg_hi = header_hi + base_hi + deficit_hi + confidence_hi + footer_hi
    msg_en = header_en + base_en + deficit_en + confidence_en + footer_en

    return {
        "hi": msg_hi,
        "en": msg_en,
        "sms_hi": base_hi[:160],   # SMS 160-char limit
        "sms_en": base_en[:160],
        "advisory_class": advisory_class,
        "crop": crop_name,
        "stage": growth_stage,
        "deficit_mm": deficit_mm,
        "confidence": confidence_label,
    }


# ---------------------------------------------------------------------------
# LLM-enhanced generator (USP 4.4) — richer, context-aware language
# ---------------------------------------------------------------------------

async def generate_advisory_text_llm(
    advisory_class: str,
    crop_name: str,
    growth_stage: str,
    deficit_mm: float,
    confidence_label: str,
    target_languages: list[str] = ["hi", "en"],
    provider: str = "gemini",
    api_key: str = "",
) -> Dict[str, str]:
    """
    USP 4.4: LLM-based natural-language generation for multilingual advisory.

    Uses Google Gemini or OpenAI to generate richer, context-aware text
    in regional languages from the structured advisory data.

    Falls back to template-based generation if API unavailable.
    """
    # Always include template as fallback
    template_result = generate_advisory_text_template(
        advisory_class, crop_name, growth_stage, deficit_mm,
        confidence_label, language="hi",
    )

    if not api_key:
        logger.info("No LLM API key configured; using template-based NLG.")
        return template_result

    prompt = f"""You are an expert agricultural advisor for Indian farmers.
Generate a short, clear irrigation advisory message in {', '.join(target_languages)}.

Context:
- Crop: {crop_name} ({CROP_NAMES_HI.get(crop_name, crop_name)})
- Growth Stage: {growth_stage} ({STAGE_NAMES_HI.get(growth_stage, growth_stage)})
- Advisory: {advisory_class.replace('_', ' ').upper()}
- Water Deficit: {deficit_mm:.1f} mm over next 8 days
- Model Confidence: {confidence_label}

Rules:
- Hindi message ≤ 160 characters (SMS-friendly)
- English message ≤ 160 characters
- Use simple vocabulary a rural farmer can understand
- Include an action verb and urgency level
- Add an appropriate emoji

Respond in JSON format:
{{"hi": "<Hindi message>", "en": "<English message>"}}
"""

    try:
        if provider == "gemini":
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            import json, re
            json_str = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_str:
                parsed = json.loads(json_str.group())
                template_result.update(parsed)
                return template_result

        elif provider == "openai":
            from openai import AsyncOpenAI  # type: ignore
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            import json
            parsed = json.loads(response.choices[0].message.content)
            template_result.update(parsed)
            return template_result

    except Exception as e:
        logger.warning("LLM generation failed (%s); using template fallback.", e)

    return template_result
