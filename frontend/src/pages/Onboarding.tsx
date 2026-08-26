import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthStatus, setupPassword } from "../api/auth";
import { ApiError } from "../api/client";
import { completeOnboarding } from "../api/onboarding";
import { TagListInput } from "../components/TagListInput";

type Step = "loading" | "password" | "details";

export function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("loading");

  useEffect(() => {
    getAuthStatus()
      .then((status) => setStep(status.password_set ? "details" : "password"))
      .catch(() => setStep("password"));
  }, []);

  if (step === "loading") {
    return <p className="page-loading">Loading…</p>;
  }
  if (step === "password") {
    return <PasswordStep onDone={() => setStep("details")} />;
  }
  return <DetailsStep onDone={() => navigate("/", { replace: true })} />;
}

function PasswordStep({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await setupPassword(password);
      onDone();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Already set (e.g. another tab raced us) — just move on.
        onDone();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page onboarding">
      <h1>Welcome</h1>
      <p>
        Choose a password to protect your OpenRouter token. It never leaves this device, and
        you'll need to re-enter it every time the app restarts.
      </p>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <div className="field">
          <label htmlFor="new-password">Password</label>
          <input
            id="new-password"
            type="password"
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoFocus
          />
        </div>
        <div className="field">
          <label htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            type="password"
            minLength={8}
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Continue"}
        </button>
      </form>
    </main>
  );
}

function DetailsStep({ onDone }: { onDone: () => void }) {
  const [defaultServings, setDefaultServings] = useState(4);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [preferenceNotes, setPreferenceNotes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await completeOnboarding({
        default_servings: defaultServings,
        allergies,
        preference_notes: preferenceNotes,
      });
      onDone();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        onDone();
        return;
      }
      setError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page onboarding">
      <h1>Almost there</h1>
      <p>A few details before your first suggestions.</p>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <div className="field">
          <label htmlFor="default-servings">Default number of servings</label>
          <input
            id="default-servings"
            type="number"
            min={1}
            value={defaultServings}
            onChange={(event) => setDefaultServings(Number(event.target.value))}
            required
          />
        </div>

        <TagListInput
          label="Allergies / strict exclusions"
          placeholder="e.g. peanut"
          values={allergies}
          onChange={setAllergies}
        />

        <TagListInput
          label="Known preferences (optional)"
          placeholder="e.g. loves spicy food"
          values={preferenceNotes}
          onChange={setPreferenceNotes}
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Get started"}
        </button>
      </form>
    </main>
  );
}
