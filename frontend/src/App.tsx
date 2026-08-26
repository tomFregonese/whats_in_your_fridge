import { useEffect, useState } from "react";
import { getHealth } from "./api/health";
import "./App.css";

type ApiStatus = "checking" | "ok" | "unreachable";

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <main className="shell">
      <h1>What's in your fridge?</h1>
      <p>Milestone 0 — skeleton wired up end to end.</p>
      <p>
        Backend API: <span className={`status status-${apiStatus}`}>{apiStatus}</span>
      </p>
    </main>
  );
}

export default App;
