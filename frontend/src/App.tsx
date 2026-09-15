import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AppLayout } from "./components/layout/AppLayout";
import { LoadingState } from "./components/ui/StateViews";

const OverviewPage = lazy(() => import("./pages/OverviewPage").then((m) => ({ default: m.OverviewPage })));
const CostPage = lazy(() => import("./pages/CostPage").then((m) => ({ default: m.CostPage })));
const UsagePage = lazy(() => import("./pages/UsagePage").then((m) => ({ default: m.UsagePage })));
const AnomaliesPage = lazy(() => import("./pages/AnomaliesPage").then((m) => ({ default: m.AnomaliesPage })));
const OptimizationPage = lazy(() =>
  import("./pages/OptimizationPage").then((m) => ({ default: m.OptimizationPage }))
);
const CarbonPage = lazy(() => import("./pages/CarbonPage").then((m) => ({ default: m.CarbonPage })));
const ForecastPage = lazy(() => import("./pages/ForecastPage").then((m) => ({ default: m.ForecastPage })));
const CopilotPage = lazy(() => import("./pages/CopilotPage").then((m) => ({ default: m.CopilotPage })));

function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <h1 className="text-2xl font-semibold text-ink">404</h1>
      <p className="text-sm text-ink-faint">This page doesn't exist in CloudSense AI.</p>
      <Link
        to="/"
        className="mt-2 rounded-lg border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-ink hover:bg-surface-border transition-colors"
      >
        Back to Overview
      </Link>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<LoadingState />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="cost"
            element={
              <Suspense fallback={<LoadingState />}>
                <CostPage />
              </Suspense>
            }
          />
          <Route
            path="usage"
            element={
              <Suspense fallback={<LoadingState />}>
                <UsagePage />
              </Suspense>
            }
          />
          <Route
            path="anomalies"
            element={
              <Suspense fallback={<LoadingState />}>
                <AnomaliesPage />
              </Suspense>
            }
          />
          <Route
            path="optimization"
            element={
              <Suspense fallback={<LoadingState />}>
                <OptimizationPage />
              </Suspense>
            }
          />
          <Route
            path="carbon"
            element={
              <Suspense fallback={<LoadingState />}>
                <CarbonPage />
              </Suspense>
            }
          />
          <Route
            path="forecast"
            element={
              <Suspense fallback={<LoadingState />}>
                <ForecastPage />
              </Suspense>
            }
          />
          <Route
            path="copilot"
            element={
              <Suspense fallback={<LoadingState />}>
                <CopilotPage />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
