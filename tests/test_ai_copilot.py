"""
CloudSense AI — Unit & Integration Test Suite for the Gemini FinOps Copilot
Tests the /api/v1/chat endpoint, intent routing, tool grounding, mock-mode
behavior, invalid-request handling, and tool-failure resilience.

All tests run in the deterministic/offline grounded mode by default (no
network calls, no Gemini API key required), matching how CI must be able to
exercise this layer. A separate, explicitly-skipped test class exists for
live Gemini verification when a real API key is configured.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.api.main import app
from src.ai.copilot import copilot, GeminiFinOpsCopilot
from src.ai.schemas import ChatRequest
from src.ai.tools import TOOLS_REGISTRY
from src.api.services.analytics_service import analytics_service


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------
# 14. Mock mode without API key
# -----------------------------------------------------------------------
def test_copilot_runs_in_mock_mode_without_api_key():
    """The global copilot instance must operate in deterministic mode when
    no GEMINI_API_KEY / CLOUDSENSE_GEMINI_API_KEY is configured in this
    test environment, guaranteeing the app is fully testable offline."""
    assert copilot.mock_mode is True
    assert copilot.client is None


# -----------------------------------------------------------------------
# 1. Chat endpoint health / basic request
# -----------------------------------------------------------------------
def test_chat_endpoint_basic_request(client):
    """A well-formed chat request returns a 200 with a fully-shaped ChatResponse."""
    res = client.post("/api/v1/chat", json={"message": "Give me a quick FinOps overview."})
    assert res.status_code == 200
    data = res.json()
    for field in ["answer", "tools_used", "analytical_sources", "relevant_metrics", "warnings", "is_grounded"]:
        assert field in data
    assert isinstance(data["answer"], str) and len(data["answer"]) > 0
    assert data["is_grounded"] is True


# -----------------------------------------------------------------------
# 2. Cost question
# -----------------------------------------------------------------------
def test_chat_cost_summary_question(client):
    """A general cost question is grounded via get_cost_summary and matches AnalyticsService exactly."""
    res = client.post("/api/v1/chat", json={"message": "What is my total cloud spend?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_cost_summary" in data["tools_used"]

    expected = analytics_service.get_cost_summary()
    assert data["relevant_metrics"]["total_net_spend_usd"] == expected["total_net_cost_usd"]
    assert data["relevant_metrics"]["avg_daily_spend_usd"] == expected["avg_daily_cost_usd"]
    assert str(expected["total_net_cost_usd"]) in data["answer"] or f"{expected['total_net_cost_usd']:,.2f}" in data["answer"]


# -----------------------------------------------------------------------
# 3. Cost breakdown question
# -----------------------------------------------------------------------
def test_chat_cost_breakdown_question(client):
    """A breakdown-by-service question is grounded via get_cost_breakdown."""
    res = client.post("/api/v1/chat", json={"message": "Give me a spend breakdown by service."})
    assert res.status_code == 200
    data = res.json()
    assert "get_cost_breakdown" in data["tools_used"]

    expected_top = analytics_service.get_cost_by_dimension("service")[0]
    assert data["relevant_metrics"]["top_category"] == expected_top["dimension_value"]
    assert data["relevant_metrics"]["top_spend_usd"] == expected_top["net_cost_usd"]


# -----------------------------------------------------------------------
# 4. Cost trend question
# -----------------------------------------------------------------------
def test_chat_cost_trend_question(client):
    """A trend/history question is grounded via get_cost_trends, not the generic cost summary."""
    res = client.post("/api/v1/chat", json={"message": "Show me the daily cost trend over time."})
    assert res.status_code == 200
    data = res.json()
    assert "get_cost_trends" in data["tools_used"]

    expected_latest = analytics_service.get_cost_trends()[-1]
    assert data["relevant_metrics"]["latest_daily_spend_usd"] == expected_latest["net_cost_usd"]
    assert data["relevant_metrics"]["rolling_7d_usd"] == expected_latest["rolling_7d"]


# -----------------------------------------------------------------------
# 5. Anomaly question
# -----------------------------------------------------------------------
def test_chat_anomaly_question(client):
    """An anomaly question is grounded via get_anomalies and matches the anomaly_detection totals."""
    res = client.post("/api/v1/chat", json={"message": "Do we have any anomalies right now?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_anomalies" in data["tools_used"]

    expected = analytics_service.get_anomalies()
    assert data["relevant_metrics"]["total_anomalies"] == expected["total_anomalies"]
    assert data["relevant_metrics"]["unbudgeted_dollar_surge"] == expected["total_unbudgeted_dollar_impact"]


# -----------------------------------------------------------------------
# 6. Optimization question
# -----------------------------------------------------------------------
def test_chat_optimization_question(client):
    """A savings/optimization question is grounded via get_optimization_opportunities."""
    res = client.post("/api/v1/chat", json={"message": "How can I save money on my cloud bill?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_optimization_opportunities" in data["tools_used"]

    expected = analytics_service.get_optimizations()
    assert data["relevant_metrics"]["monthly_savings_usd"] == expected["total_potential_monthly_savings_usd"]
    assert data["relevant_metrics"]["annual_savings_usd"] == expected["total_potential_annual_savings_usd"]


# -----------------------------------------------------------------------
# 7. Carbon question
# -----------------------------------------------------------------------
def test_chat_carbon_question(client):
    """A carbon/emissions question is grounded via get_carbon_summary and includes the estimate disclaimer."""
    res = client.post("/api/v1/chat", json={"message": "What is our carbon footprint?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_carbon_summary" in data["tools_used"]
    assert any("estimate" in w.lower() for w in data["warnings"])

    expected = analytics_service.get_carbon_summary()
    assert data["relevant_metrics"]["total_carbon_kg"] == expected["total_carbon_kg_co2e"]
    assert data["relevant_metrics"]["total_energy_kwh"] == expected["total_energy_consumed_kwh"]


# -----------------------------------------------------------------------
# Utilization / underutilized-resources question
# -----------------------------------------------------------------------
def test_chat_utilization_question(client):
    """An underutilization question is grounded via get_resource_utilization, not the generic cost summary."""
    res = client.post("/api/v1/chat", json={"message": "Which resources are underutilized?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_resource_utilization" in data["tools_used"]

    expected = analytics_service.get_usage_summary()
    assert data["relevant_metrics"]["mean_cpu_pct"] == expected["overall_mean_cpu_pct"]
    assert data["relevant_metrics"]["idle_cost_waste_usd"] == expected["idle_cost_waste_usd"]


# -----------------------------------------------------------------------
# 8. Forecast question
# -----------------------------------------------------------------------
def test_chat_forecast_question(client):
    """A forecast question is grounded via get_forecast / get_forecast_models."""
    res = client.post("/api/v1/chat", json={"message": "What will my costs look like next month?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_forecast" in data["tools_used"]

    expected = analytics_service.get_forecast_projections(horizon_days=30)
    assert data["relevant_metrics"]["projected_30_days_spend_usd"] == expected["projected_total_usd"]


# -----------------------------------------------------------------------
# 9. Root-cause question
# -----------------------------------------------------------------------
def test_chat_root_cause_question(client):
    """A 'why did costs spike' question triggers root-cause synthesis over anomalies + top services + waste."""
    res = client.post("/api/v1/chat", json={"message": "Why did my costs suddenly increase?"})
    assert res.status_code == 200
    data = res.json()
    assert "run_root_cause_analysis" in data["tools_used"]
    assert len(data["warnings"]) > 0  # causation-hedging warning must be present
    assert "correlation" in data["warnings"][0].lower() or "correlation" in data["answer"].lower()


# -----------------------------------------------------------------------
# 10. Unavailable-data question
# -----------------------------------------------------------------------
def test_chat_unavailable_data_question(client):
    """Questions about unmonitored infrastructure (e.g. AWS) must state data is unavailable, never invent it."""
    res = client.post("/api/v1/chat", json={"message": "How much am I spending on AWS EC2?"})
    assert res.status_code == 200
    data = res.json()
    assert data["tools_used"] == []
    assert "not available" in data["answer"].lower()
    assert data["relevant_metrics"] == {}


# -----------------------------------------------------------------------
# 11. Invalid request
# -----------------------------------------------------------------------
def test_chat_invalid_request_too_short(client):
    """A message shorter than the schema's min_length must be rejected with 422, never reach the copilot."""
    res = client.post("/api/v1/chat", json={"message": "?"})
    assert res.status_code == 422


def test_chat_invalid_request_missing_field(client):
    """A request missing the required 'message' field must be rejected with 422."""
    res = client.post("/api/v1/chat", json={})
    assert res.status_code == 422


# -----------------------------------------------------------------------
# 12. Tool failure
# -----------------------------------------------------------------------
def test_tool_raises_not_found_for_unknown_anomaly_id():
    """Calling a tool with an invalid identifier fails predictably (404), never silently fabricates data."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        TOOLS_REGISTRY["get_anomaly_details"]("ANOM-DOES-NOT-EXIST")
    assert exc_info.value.status_code == 404


def test_live_gemini_chat_returns_live_answer_on_successful_tool_call(monkeypatch):
    """
    Regression test for a real bug found in Phase 7: _execute_live_gemini_chat
    referenced an undefined variable ('user_msg' instead of 'request.message')
    on the success path, right before constructing the returned ChatResponse.
    This raised a NameError on every successful live tool call, which was
    then silently caught by the method's own broad `except Exception` and
    mis-reported as a graceful fallback to deterministic mode — meaning live
    mode never actually returned a live-generated answer for any tool-calling
    conversation, even with a valid API key. This test fakes a SUCCESSFUL
    tool call (not a failure) and asserts the live path completes and
    returns the live-generated answer verbatim, never silently rerouting to
    the deterministic engine.
    """
    live_copilot = GeminiFinOpsCopilot()
    live_copilot.mock_mode = False

    class _FakeFunctionCall:
        name = "get_carbon_summary"
        args = {}

    class _FakeCandidateContent:
        role = "model"
        parts = []

    class _FakeCandidate:
        content = _FakeCandidateContent()

    class _FakeFirstResponse:
        function_calls = [_FakeFunctionCall()]
        candidates = [_FakeCandidate()]
        text = None

    class _FakeSecondResponse:
        function_calls = None
        text = "LIVE_ANSWER_SENTINEL: carbon footprint synthesized by the live model."

    call_count = {"n": 0}

    class _FakeModels:
        def generate_content(self, model, contents, config):
            call_count["n"] += 1
            return _FakeFirstResponse() if call_count["n"] == 1 else _FakeSecondResponse()

    class _FakeClient:
        models = _FakeModels()

    live_copilot.client = _FakeClient()

    response = live_copilot.chat(ChatRequest(message="What is our carbon footprint?"))

    assert response.answer == "LIVE_ANSWER_SENTINEL: carbon footprint synthesized by the live model."
    assert "get_carbon_summary" in response.tools_used
    assert any("carbon" in w.lower() for w in response.warnings)
    assert response.is_grounded is True


def test_copilot_degrades_gracefully_when_live_tool_execution_fails(monkeypatch):
    """If a tool raises during live Gemini execution, the copilot must return a
    grounded 'unavailable' response instead of propagating a 500 error."""
    live_copilot = GeminiFinOpsCopilot()
    live_copilot.mock_mode = False

    class _FakeFunctionCall:
        name = "get_cost_summary"
        args = {}

    class _FakeCandidateContent:
        role = "model"
        parts = []

    class _FakeCandidate:
        content = _FakeCandidateContent()

    class _FakeResponse:
        function_calls = [_FakeFunctionCall()]
        candidates = [_FakeCandidate()]
        text = "Analysis completed successfully."

    class _FakeModels:
        def generate_content(self, model, contents, config):
            return _FakeResponse()

    class _FakeClient:
        models = _FakeModels()

    live_copilot.client = _FakeClient()

    def _broken_tool():
        raise RuntimeError("simulated analytics backend failure")

    monkeypatch.setitem(TOOLS_REGISTRY, "get_cost_summary", _broken_tool)

    response = live_copilot.chat(ChatRequest(message="What is my total spend?"))
    assert response.is_grounded is False
    assert any("failed" in w.lower() or "incomplete" in w.lower() for w in response.warnings), (
        "A tool failure must always be disclosed via `warnings`, regardless of what "
        "free-form text the model's second turn happens to return."
    )


# -----------------------------------------------------------------------
# 13. Grounding / hallucination protection
# -----------------------------------------------------------------------
def test_grounded_numbers_match_analytics_summary_exactly(client):
    """Every numerical figure surfaced by the copilot must trace back exactly
    to the validated analytics_summary.json — never independently computed."""
    res = client.post("/api/v1/chat", json={"message": "Summarize our cloud carbon emissions."})
    data = res.json()
    ground_truth = analytics_service.get_carbon_summary()

    assert data["relevant_metrics"]["total_carbon_kg"] == ground_truth["total_carbon_kg_co2e"]
    assert data["relevant_metrics"]["carbon_intensity"] == ground_truth["avg_carbon_intensity_gco2_per_dollar"]
    # The disclaimer required by MASTER_SYSTEM_INSTRUCTION must be surfaced, not omitted.
    assert any("estimate" in w.lower() for w in data["warnings"])


def test_copilot_never_fabricates_metrics_for_unsupported_queries(client):
    """For data outside the monitored estate, relevant_metrics must be empty —
    the copilot must not invent placeholder or approximate numbers."""
    res = client.post("/api/v1/chat", json={"message": "What's my Azure Blob Storage spend?"})
    data = res.json()
    assert data["relevant_metrics"] == {}
    assert data["tools_used"] == []


# -----------------------------------------------------------------------
# Live Gemini mode (only runs if a real API key is explicitly configured)
# -----------------------------------------------------------------------
@pytest.mark.skipif(
    not (os.getenv("GEMINI_API_KEY") or os.getenv("CLOUDSENSE_GEMINI_API_KEY")),
    reason="Live Gemini test requires a real GEMINI_API_KEY / CLOUDSENSE_GEMINI_API_KEY.",
)
def test_live_gemini_chat_smoke():
    """Smoke test for the live Gemini tool-calling path. Skipped unless a real API key is present."""
    live_copilot = GeminiFinOpsCopilot()
    assert live_copilot.mock_mode is False
    response = live_copilot.chat(ChatRequest(message="What is my total cloud spend?"))
    assert response.is_grounded is True
    assert isinstance(response.answer, str) and len(response.answer) > 0
