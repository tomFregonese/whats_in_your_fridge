import { Link } from "react-router-dom";
import { ApiError } from "../api/client";

interface ApiErrorMessageProps {
  /** A caught error (from an API call) or a plain client-side validation
   * string — both render the same way, so callers don't need to branch. */
  error: unknown;
}

/** Turns a caught error into the most useful message available, instead of
 * a blanket "something went wrong": OpenRouter/model/vault failures
 * already carry a specific, human-readable message from the backend (see
 * `app.services.exceptions`) — rate limits, timeouts, a rejected token, an
 * unavailable model, a locked vault — this shows it as-is, with a link to
 * fix it where one unambiguously applies. A request that never reached the
 * server at all (the backend is down, not just erroring) gets its own
 * message rather than a misleading generic one. */
export function ApiErrorMessage({ error }: ApiErrorMessageProps) {
  if (!error) {
    return null;
  }

  if (typeof error === "string") {
    return <p className="error">{error}</p>;
  }

  if (!(error instanceof ApiError)) {
    return <p className="error">Can't reach the app's server — check that it's running.</p>;
  }

  if (error.status === 423) {
    return (
      <p className="error">
        {error.message} <Link to="/unlock">Unlock →</Link>
      </p>
    );
  }

  if (error.status === 409) {
    return (
      <p className="error">
        {error.message} <Link to="/settings">Settings →</Link>
      </p>
    );
  }

  // 429 (OpenRouter rate limit), 502 (auth/connection/empty response), 504
  // (timeout) all already carry a clear, specific message worth showing
  // as-is — no link, since "try again in a moment" is the whole fix.
  if (error.status === 429 || error.status === 502 || error.status === 504) {
    return <p className="error">{error.message}</p>;
  }

  return <p className="error">Something went wrong — please try again.</p>;
}
