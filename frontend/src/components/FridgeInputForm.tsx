import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { SuggestionsResult } from "../api/suggestions";
import { createSuggestions, respondToClarification } from "../api/suggestions";
import { ClarificationModal } from "./ClarificationModal";
import type { IngredientEntry } from "./IngredientListInput";
import { IngredientListInput } from "./IngredientListInput";

interface PendingClarification {
  runId: number;
  question: string;
  options: string[] | null;
}

export function FridgeInputForm() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"batch" | "single">("batch");
  const [ingredients, setIngredients] = useState<IngredientEntry[]>([]);
  const [freeText, setFreeText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clarification, setClarification] = useState<PendingClarification | null>(null);

  function handleResult(result: SuggestionsResult): void {
    if (result.status === "clarification_needed" && result.run_id !== null && result.question) {
      // Could itself be answered with *another* clarification — this just
      // re-renders the modal with the new question in that case.
      setClarification({ runId: result.run_id, question: result.question, options: result.options });
      return;
    }
    setClarification(null);
    if (result.meal_plan_id === null) return; // never happens for "completed" in practice
    navigate(`/plan/${String(result.meal_plan_id)}`, {
      state: { notesGenerales: result.notes_generales },
    });
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (ingredients.length === 0 && !freeText.trim()) {
      setError("Add at least one ingredient or describe what's in your fridge.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await createSuggestions({
        mode,
        free_text: freeText.trim() || undefined,
        items: ingredients.map((item) => ({
          ingredient_name: item.name,
          quantity_raw: item.quantity || undefined,
        })),
      });
      handleResult(result);
    } catch {
      setError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleClarificationAnswer(answer: string): Promise<void> {
    if (!clarification) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await respondToClarification(clarification.runId, answer);
      handleResult(result);
    } catch {
      setClarification(null);
      setError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="card">
        <div className="card-header">
          <h2>🥕 What's in your fridge?</h2>
        </div>
        <p className="card-description">Tell us what you've got, and we'll suggest what to cook.</p>

        <form onSubmit={(event) => void handleSubmit(event)}>
          <div className="field">
            <span className="field-label">Mode</span>
            <div className="segmented">
              <button
                type="button"
                className={mode === "batch" ? "active" : ""}
                onClick={() => setMode("batch")}
              >
                Batch cooking
              </button>
              <button
                type="button"
                className={mode === "single" ? "active" : ""}
                onClick={() => setMode("single")}
              >
                Single dish
              </button>
            </div>
          </div>

          <IngredientListInput items={ingredients} onChange={setIngredients} />

          <div className="field">
            <label htmlFor="free-text">Anything else? (optional)</label>
            <textarea
              id="free-text"
              rows={3}
              value={freeText}
              onChange={(event) => setFreeText(event.target.value)}
              placeholder="e.g. also have half a lemon and some leftover rice"
            />
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Thinking…" : "Get suggestions"}
          </button>
        </form>
      </div>

      {clarification && (
        <ClarificationModal
          question={clarification.question}
          options={clarification.options}
          submitting={submitting}
          onAnswer={(answer) => void handleClarificationAnswer(answer)}
        />
      )}
    </>
  );
}
