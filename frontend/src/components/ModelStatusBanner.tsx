import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ApiError } from "../api/client";
import { getModelStatus } from "../api/settings";

/** Polls `GET /api/settings/model-status` once per mount and shows a
 * persistent, clickable warning when the configured model has dropped out
 * of OpenRouter's `:free` catalog. Silent whenever there's nothing to warn
 * about: no model chosen yet (covered by the Home/Settings pickers
 * themselves), the model is still available, or onboarding/unlock hasn't
 * happened yet (the 409/423 the endpoint returns in those cases). */
export function ModelStatusBanner() {
  const [unavailableModelId, setUnavailableModelId] = useState<string | null>(null);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    getModelStatus()
      .then((status) => {
        if (!cancelled) {
          setUnavailableModelId(status.model_id !== null && !status.available ? status.model_id : null);
        }
      })
      .catch((error: unknown) => {
        // 409 (not onboarded) / 423 (vault locked) just mean "nothing to
        // report yet" — anything else is swallowed too, since a broken
        // status check shouldn't block the rest of the app from rendering.
        if (!(error instanceof ApiError)) {
          console.error("Failed to fetch model status", error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  if (unavailableModelId === null || location.pathname === "/settings") {
    return null;
  }

  return (
    <Link to="/settings" className="model-status-banner">
      <span className="model-status-banner-icon">⚠️</span>
      <span>
        Model <strong>{unavailableModelId}</strong> is no longer available on OpenRouter — pick
        another one in Settings.
      </span>
    </Link>
  );
}
