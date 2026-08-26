import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getAuthStatus } from "../api/auth";
import { getOnboardingStatus } from "../api/onboarding";

type Status = "loading" | "ready" | "needs-unlock" | "needs-onboarding";

/** Gates every route except `/unlock` and `/onboarding` themselves.
 * Checks auth (password set + unlocked) before onboarding, since nothing
 * else works while the vault is locked. */
export function AppGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");

  async function check(): Promise<void> {
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
      setStatus("needs-onboarding");
    }
  }

  useEffect(() => {
    void check();
  }, []);

  if (status === "loading") {
    return <p className="page-loading">Loading…</p>;
  }
  if (status === "needs-unlock") {
    return <Navigate to="/unlock" replace />;
  }
  if (status === "needs-onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}
