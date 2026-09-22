import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { NewRunPage } from "./pages/NewRunPage";
import { RunsPage } from "./pages/RunsPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { ReviewWorkspacePage } from "./pages/ReviewWorkspacePage";
import { TestCasesPage } from "./pages/TestCasesPage";
import { ScriptsPage } from "./pages/ScriptsPage";
import { ExecutionsPage } from "./pages/ExecutionsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { CicdPage } from "./pages/CicdPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
import { ReviewsPage } from "./pages/secondary";
import { PlaceholderPage } from "./pages/PlaceholderPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="runs/new" element={<NewRunPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="runs/:runId" element={<RunDetailPage />} />
        <Route path="runs/:runId/review/:gate" element={<ReviewWorkspacePage />} />
        <Route path="reviews" element={<ReviewsPage />} />
        <Route path="test-cases" element={<TestCasesPage />} />
        <Route path="scripts" element={<ScriptsPage />} />
        <Route path="executions" element={<ExecutionsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="skills" element={<SkillsPage />} />
        <Route path="cicd" element={<CicdPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route
          path="*"
          element={<PlaceholderPage title="Not found" description="This route does not exist." />}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
