"""
CloudSense AI — Carbon & GreenOps Router
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/carbon", tags=["Carbon & GreenOps"])


class MigrationSimulationRequest(BaseModel):
    resource_id: str = Field(..., description="Cloud asset identifier, e.g. vm-checkout-e2-micro-003")
    target_region_id: str = Field("europe-west6", description="Target region: europe-west6 (Zurich) or us-central1 (Iowa)")


@router.get("/summary", summary="Macro Electrical Energy & Scope 2/3 Carbon Totals")
async def get_carbon_summary():
    """Returns facility electrical energy, Scope 2 operational, and Scope 3 embodied emissions estimates."""
    return analytics_service.get_carbon_summary()


@router.get("/by-region", summary="Regional Carbon Footprint & Carbon Intensity")
async def get_carbon_by_region():
    """Returns energy consumption, emissions, and carbon efficiency per dollar spend by cloud region."""
    return analytics_service.get_carbon_by_region()


@router.get("/trends", summary="Daily Historical Carbon Emissions Trend")
async def get_carbon_trends():
    """Returns daily time-series of Scope 2 and Scope 3 emissions with moving averages."""
    return analytics_service.get_carbon_trends()


@router.post("/simulate-migration", summary="Simulate Workload Relocation to Low-Carbon Region")
async def simulate_migration(req: MigrationSimulationRequest):
    """Calculates carbon reduction and financial delta from migrating a workload to Zurich or Iowa."""
    return analytics_service.simulate_green_migration(resource_id=req.resource_id, target_region_id=req.target_region_id)
