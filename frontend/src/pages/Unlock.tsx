import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { unlock } from "../api/auth";
import { ApiError } from "../api/client";

export function Unlock() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await unlock(password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Incorrect password."
          : "Something went wrong — please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="centered-page">
      <div className="centered-card">
        <h1>🔒 Locked</h1>
        <p>Enter your app password to continue.</p>
        <form onSubmit={(event) => void handleSubmit(event)}>
          <div className="field">
            <label htmlFor="unlock-password">Password</label>
            <input
              id="unlock-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoFocus
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Unlocking…" : "Unlock"}
          </button>
        </form>
      </div>
    </div>
  );
}
