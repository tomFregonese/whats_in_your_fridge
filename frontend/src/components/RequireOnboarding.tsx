import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getOnboardingStatus } from "../api/onboarding";

type Status = "loading" | "onboarded" | "not-onboarded";

/** Redirects to `/onboarding` until `GET /api/onboarding/status` says the
 * household is configured — every other route is wrapped in this. */
export function RequireOnboarding({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    getOnboardingStatus()
      .then((result) => setStatus(result.onboarded ? "onboarded" : "not-onboarded"))
      .catch(() => setStatus("not-onboarded"));
  }, []);

  if (status === "loading") {
    return <p className="page-loading">Loading…</p>;
  }
  if (status === "not-onboarded") {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}
