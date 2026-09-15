"""
CloudSense AI — FinOps Copilot Chat Router
Thin HTTP layer exposing the Gemini-grounded conversational copilot.

All Gemini reasoning, tool-calling, and anti-hallucination grounding logic
lives in `src.ai.copilot.GeminiFinOpsCopilot` — this router only validates
the incoming request and delegates to it.
"""

from fastapi import APIRouter
from src.ai.schemas import ChatRequest, ChatResponse
from src.ai.copilot import copilot

router = APIRouter(prefix="/chat", tags=["AI Grounding & Copilot Context"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the CloudSense AI FinOps Copilot a Question",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Sends a natural-language FinOps/GreenOps question to the Gemini-grounded
    copilot and returns a structured, tool-grounded answer.

    Operates in one of two modes, selected automatically:
    - **Live Gemini mode**: used when a valid `GEMINI_API_KEY` is configured.
      Gemini performs tool calling against the verified analytics backend and
      synthesizes an explanation strictly from tool results.
    - **Deterministic grounded mode** (default / offline-safe): used when no
      API key is configured, or `CLOUDSENSE_AI_MOCK_MODE` is enabled. Produces
      the same structured, tool-grounded answers using rule-based intent
      routing over the exact same verified analytics tools — no external
      network calls, no hallucination risk, fully testable in CI.

    In both modes, every numerical figure in the answer originates directly
    from `src.ai.tools.TOOLS_REGISTRY`, which reads from the validated
    analytics warehouse (`AnalyticsService`). The copilot never invents,
    estimates, or independently calculates numbers.
    """
    return copilot.chat(request)
