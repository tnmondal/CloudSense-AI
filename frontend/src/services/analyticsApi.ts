import { apiClient } from "./apiClient";
import type {
  HealthResponse,
  DashboardSummary,
  CostSummary,
  CostDimensionBreakdown,
  CostDimension,
  CostTrendPoint,
  PaginatedCostResources,
  UsageSummary,
  ServiceUtilization,
  UtilizationCorrelation,
  AnomaliesResponse,
  OptimizationsResponse,
  CarbonSummary,
  CarbonRegionBreakdown,
  CarbonTrendPoint,
  GreenMigrationSimulation,
  ForecastSummary,
  ForecastModelResult,
  ForecastProjections,
  AiGroundingContext,
  ToolsManifestResponse,
  ChatRequest,
  ChatResponse,
} from "../types/api";

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export const getHealth = () =>
  apiClient.get<HealthResponse>("/health").then((r) => r.data);

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export const getDashboardSummary = () =>
  apiClient.get<DashboardSummary>("/dashboard/summary").then((r) => r.data);

// ---------------------------------------------------------------------------
// Cost
// ---------------------------------------------------------------------------
export const getCostSummary = () =>
  apiClient.get<CostSummary>("/cost/summary").then((r) => r.data);

// Only "service", "region", and "department" have dedicated endpoints in the
// backend (src/api/routers/cost.py). "environment" and "provider" breakdowns
// are computed by AnalyticsService but are not currently exposed as REST
// endpoints, so they are intentionally omitted here rather than guessed at.
const DIMENSION_PATHS: Record<Extract<CostDimension, "service" | "region" | "department">, string> = {
  service: "/cost/by-service",
  region: "/cost/by-region",
  department: "/cost/by-department",
};

export const getCostByDimension = (
  dimension: "service" | "region" | "department"
) =>
  apiClient
    .get<CostDimensionBreakdown[]>(DIMENSION_PATHS[dimension])
    .then((r) => r.data);

export const getCostTrends = () =>
  apiClient.get<CostTrendPoint[]>("/cost/trends").then((r) => r.data);

export interface CostResourcesParams {
  page?: number;
  page_size?: number;
  search?: string;
  department?: string;
}

export const getCostResources = (params: CostResourcesParams = {}) =>
  apiClient
    .get<PaginatedCostResources>("/cost/resources", { params })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Usage
// ---------------------------------------------------------------------------
export const getUsageSummary = () =>
  apiClient.get<UsageSummary>("/usage/summary").then((r) => r.data);

export const getServiceUtilization = () =>
  apiClient.get<ServiceUtilization[]>("/usage/services").then((r) => r.data);

export const getUtilizationCorrelations = () =>
  apiClient
    .get<UtilizationCorrelation[]>("/usage/correlations")
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Anomalies
// ---------------------------------------------------------------------------
export interface AnomaliesParams {
  severity?: string;
  limit?: number;
  offset?: number;
}

export const getAnomalies = (params: AnomaliesParams = {}) =>
  apiClient.get<AnomaliesResponse>("/anomalies", { params }).then((r) => r.data);

export const getAnomalyById = (anomalyId: string) =>
  apiClient
    .get(`/anomalies/${encodeURIComponent(anomalyId)}`)
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Optimizations
// ---------------------------------------------------------------------------
export interface OptimizationsParams {
  category?: string;
  limit?: number;
  offset?: number;
}

export const getOptimizations = (params: OptimizationsParams = {}) =>
  apiClient
    .get<OptimizationsResponse>("/optimizations", { params })
    .then((r) => r.data);

export const getOptimizationById = (recommendationId: string) =>
  apiClient
    .get(`/optimizations/${encodeURIComponent(recommendationId)}`)
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Carbon
// ---------------------------------------------------------------------------
export const getCarbonSummary = () =>
  apiClient.get<CarbonSummary>("/carbon/summary").then((r) => r.data);

export const getCarbonByRegion = () =>
  apiClient.get<CarbonRegionBreakdown[]>("/carbon/by-region").then((r) => r.data);

export const getCarbonTrends = () =>
  apiClient.get<CarbonTrendPoint[]>("/carbon/trends").then((r) => r.data);

export const simulateGreenMigration = (
  resourceId: string,
  targetRegionId?: string
) =>
  apiClient
    .post<GreenMigrationSimulation>("/carbon/simulate-migration", {
      resource_id: resourceId,
      target_region_id: targetRegionId,
    })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Forecast
// ---------------------------------------------------------------------------
export const getForecastSummary = () =>
  apiClient.get<ForecastSummary>("/forecast/summary").then((r) => r.data);

export const getForecastModels = () =>
  apiClient.get<ForecastModelResult[]>("/forecast/models").then((r) => r.data);

export const getForecastProjections = (horizonDays: number = 30) =>
  apiClient
    .get<ForecastProjections>("/forecast/projections", {
      params: { horizon_days: horizonDays },
    })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// AI Context / Tools Manifest
// ---------------------------------------------------------------------------
export const getAiGroundingContext = () =>
  apiClient.get<AiGroundingContext>("/ai/context").then((r) => r.data);

export const getAiToolsManifest = () =>
  apiClient.get<ToolsManifestResponse>("/ai/tools-manifest").then((r) => r.data);

// ---------------------------------------------------------------------------
// AI Copilot Chat
// ---------------------------------------------------------------------------
export const postChatMessage = (request: ChatRequest) =>
  apiClient.post<ChatResponse>("/chat", request).then((r) => r.data);
