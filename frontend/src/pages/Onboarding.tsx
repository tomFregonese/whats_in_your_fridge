import { Fragment, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthStatus, setToken as saveToken, setupPassword } from "../api/auth";
import { ApiError } from "../api/client";
import { completeOnboarding } from "../api/onboarding";
import { ModelPicker } from "../components/ModelPicker";
import { TagListInput } from "../components/TagListInput";

type Step = "loading" | "password" | "openrouter" | "details";

const STEP_NUMBER: Record<Exclude<Step, "loading">, 1 | 2 | 3> = {
  password: 1,
  openrouter: 2,
  details: 3,
};

export function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("loading");
  const [chosenModelId, setChosenModelId] = useState<string | undefined>(undefined);

  useEffect(() => {
    getAuthStatus()
      .then((status) => setStep(status.password_set ? "openrouter" : "password"))
      .catch(() => setStep("password"));
  }, []);

  if (step === "loading") {
    return <p className="page-loading">Loading…</p>;
  }
  if (step === "password") {
    return <PasswordStep onDone={() => setStep("openrouter")} />;
  }
  if (step === "openrouter") {
    return (
      <OpenRouterStep
        onDone={(modelId) => {
          setChosenModelId(modelId);
          setStep("details");
        }}
      />
    );
  }
  return (
    <DetailsStep
      openrouterModelId={chosenModelId}
      onDone={() => navigate("/", { replace: true })}
    />
  );
}

function OnboardingShell({
  step,
  title,
  subtitle,
  children,
}: {
  step: Exclude<Step, "loading">;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="centered-page">
      <div className="centered-card wide">
        <ProgressSteps current={STEP_NUMBER[step]} />
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {children}
      </div>
    </div>
  );
}

function ProgressSteps({ current }: { current: 1 | 2 | 3 }) {
  return (
    <div className="progress-steps">
      {([1, 2, 3] as const).map((step) => (
        <Fragment key={step}>
          {step > 1 && <span className="connector" />}
          <span className={`step ${step === current ? "active" : step < current ? "done" : ""}`}>
            {step < current ? "✓" : step}
          </span>
        </Fragment>
      ))}
    </div>
  );
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
    <OnboardingShell
      step="password"
      title="🔐 Welcome"
      subtitle="Choose a password to protect your OpenRouter token. It never leaves this device, and you'll need to re-enter it every time the app restarts."
    >
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
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Saving…" : "Continue"}
        </button>
      </form>
    </OnboardingShell>
  );
}

function OpenRouterStep({ onDone }: { onDone: (modelId: string) => void }) {
  const [token, setTokenValue] = useState("");
  const [modelId, setModelId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!modelId) {
      setError("Pick a model to continue.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await saveToken(token);
      onDone(modelId);
    } catch {
      setError("Something went wrong saving your token — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <OnboardingShell
      step="openrouter"
      title="🔌 Connect OpenRouter"
      subtitle="Paste your OpenRouter API key — it's encrypted at rest and never shown again — then pick a free model to use."
    >
      <form onSubmit={(event) => void handleSubmit(event)}>
        <div className="field">
          <label htmlFor="openrouter-token">OpenRouter API key</label>
          <input
            id="openrouter-token"
            type="password"
            value={token}
            onChange={(event) => setTokenValue(event.target.value)}
            required
            autoFocus
          />
        </div>

        <div className="field">
          <span className="field-label">Model</span>
          <ModelPicker selectedId={modelId} onSelect={setModelId} />
        </div>

        {error && <p className="error">{error}</p>}

        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Saving…" : "Continue"}
        </button>
      </form>
    </OnboardingShell>
  );
}

function DetailsStep({
  openrouterModelId,
  onDone,
}: {
  openrouterModelId?: string;
  onDone: () => void;
}) {
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
        openrouter_model_id: openrouterModelId,
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
    <OnboardingShell
      step="details"
      title="🥗 Almost there"
      subtitle="A few details before your first suggestions."
    >
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

        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Saving…" : "Get started"}
        </button>
      </form>
    </OnboardingShell>
  );
}
