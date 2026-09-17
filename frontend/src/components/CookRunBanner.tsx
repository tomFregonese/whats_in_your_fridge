import { Link, useLocation } from "react-router-dom";
import { useCookRun } from "../context/CookRunContext";

/** Persistent reminder, on every page except Home itself, that a "Cook"
 * request is still running — it survives navigation (see
 * `CookRunProvider`), but nothing else would hint that it's still going
 * once its form has scrolled out of view. */
export function CookRunBanner() {
  const location = useLocation();
  const { streamingActive, clarification, ideas } = useCookRun();

  if (!streamingActive || location.pathname === "/") {
    return null;
  }

  const label = clarification
    ? "The AI needs your answer to keep cooking — tap to answer"
    : ideas
      ? "Dish ideas are ready — tap to pick what to cook"
      : "Still cooking up your suggestions…";

  return (
    <Link to="/" className="cook-run-banner">
      <span className="cook-run-banner-icon">🍳</span>
      <span>{label}</span>
    </Link>
  );
}
