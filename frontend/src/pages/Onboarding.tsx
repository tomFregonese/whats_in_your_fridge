import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { completeOnboarding } from "../api/onboarding";
import { TagListInput } from "../components/TagListInput";

export function Onboarding() {
  const navigate = useNavigate();
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
      navigate("/", { replace: true });
    } catch (err) {
      // Onboarding already done elsewhere (e.g. another tab) — just move on.
      if (err instanceof ApiError && err.status === 409) {
        navigate("/", { replace: true });
        return;
      }
      setError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page onboarding">
      <h1>Welcome</h1>
      <p>Let's set a few things up before your first suggestions.</p>

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
