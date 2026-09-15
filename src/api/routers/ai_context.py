"""
CloudSense AI — Gemini Grounding & AI Context Router
Supplies structured, validated analytical facts and function-calling schemas
to guarantee zero numerical hallucinations in future GenAI copilot integrations.
"""

from fastapi import APIRouter
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/ai", tags=["AI Grounding & Copilot Context"])


@router.get("/context", summary="Get Grounded Analytical Context for LLM Reasoning")
async def get_ai_grounding_context():
    """
    Returns a consolidated, verified factual packet designed for injection into Gemini prompts.
    Ensures the future AI assistant only interprets pre-computed facts and never fabricates numbers.
    """
    return analytics_service.get_gemini_context()


@router.get("/tools-manifest", summary="Get JSON Schema Tools Manifest for Gemini Tool Calling")
async def get_ai_tools_manifest():
    """Returns strongly typed function calling tool definitions ready for Gemini SDK registration."""
    return {"tools": analytics_service.get_gemini_tools_manifest()}
