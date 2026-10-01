import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import Sidebar from "../components/Sidebar.jsx";
import QueryInput from "../components/QueryInput.jsx";
import SystemStatus from "../components/SystemStatus.jsx";
import RankingWeights from "../components/RankingWeights.jsx";

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.systemStatus().then(setStatus).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="shell">
      <Sidebar active="Research" />
      <main className="main">
        <div className="column">
          <div className="hero">
            <h1 className="headline-display">What do you want to research?</h1>
            <p className="muted">Grounded, cited answers over live arXiv AI/ML literature</p>
          </div>
          <QueryInput onSubmit={() => {}} disabled />
          <p className="search-hint caption muted">The query pipeline is enabled in Phase 7</p>
          {error && <p className="error">Backend unreachable: {error}</p>}
          {!status && !error && <p className="muted">Loading…</p>}
          {status && (
            <div className="grid">
              <SystemStatus status={status} />
              <RankingWeights ranking={status.ranking} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
