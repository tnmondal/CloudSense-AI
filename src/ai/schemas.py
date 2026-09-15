"""
CloudSense AI — Conversational AI Schemas
Defines request and response structures for the Gemini FinOps Copilot.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'model', or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000, description="User question or prompt for the FinOps Copilot")
    conversation_history: Optional[List[ChatMessage]] = Field(default=[], description="Prior dialogue context")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded, human-readable executive analysis")
    tools_used: List[str] = Field(default=[], description="List of backend analytical tools executed by Gemini")
    analytical_sources: List[str] = Field(default=[], description="Data warehouse fact/mart tables referenced")
    relevant_metrics: Dict[str, Any] = Field(default={}, description="Extracted numerical values used in the answer")
    warnings: List[str] = Field(default=[], description="Environmental or statistical limitations/hedging notes")
    is_grounded: bool = Field(default=True, description="Flag confirming output is strictly bounded by tool facts")
