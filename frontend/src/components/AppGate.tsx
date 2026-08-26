import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getAuthStatus } from "../api/auth";
import { getOnboardingStatus } from "../api/onboarding";

type Status = "loading" | "ready" | "needs-unlock" | "needs-onboarding" | "error";

/** Gates every route except `/unlock` and `/onboarding` themselves.
 * Checks auth (password set + unlocked) before onboarding, since nothing
 * else works while the vault is locked.
 *
 * A failed check is *not* treated as "needs onboarding" — the backend
 * being genuinely unreachable (container restarting, network blip) used
 * to masquerade as a wiped-out setup, which is a confusing thing to see
 * happen to your own data. It gets its own state instead. */
export function AppGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");

  async function check(): Promise<void> {
    setStatus("loading");
    try {
      const auth = await getAuthStatus();
      if (!auth.password_set) {
        setStatus("needs-onboarding");
        return;
      }
      if (!auth.unlocked) {
        setStatus("needs-unlock");
        return;
      }
      const onboarding = await getOnboardingStatus();
      setStatus(onboarding.onboarded ? "ready" : "needs-onboarding");
    } catch {
      setStatus("error");
    }
  }

  useEffect(() => {
    void check();
  }, []);

  if (status === "loading") {
    return <p className="page-loading">Loading…</p>;
  }
  if (status === "error") {
    return (
      <div className="centered-page">
        <div className="centered-card">
          <h1>🔌 Can't reach the server</h1>
          <p>Make sure the app's containers are running, then try again.</p>
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={() => void check()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  if (status === "needs-unlock") {
    return <Navigate to="/unlock" replace />;
  }
  if (status === "needs-onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}
