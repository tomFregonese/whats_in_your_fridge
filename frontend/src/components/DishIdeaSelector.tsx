import { useState } from "react";
import type { FormEvent } from "react";
import type { DishIdea } from "../api/suggestions";

interface DishIdeaSelectorProps {
  ideas: DishIdea[];
  mode: "batch" | "single";
  submitting: boolean;
  onConfirm: (selectedIndexes: number[]) => void;
}

/** Shown once the agent has proposed a shortlist of dish ideas (name +
 * description only — no ingredients/steps yet, see `agent/loop.py`'s
 * `IDEAS` phase). The user picks which one(s) they actually want cooked
 * before the full recipe is generated for exactly those — `single` mode
 * picks exactly one (radio), `batch` mode picks one or more (checkboxes).
 * Rendered inline by `FridgeInputForm`, not as a modal like
 * `ClarificationModal` — a shortlist with descriptions needs more room. */
export function DishIdeaSelector({ ideas, mode, submitting, onConfirm }: DishIdeaSelectorProps) {
  const [selected, setSelected] = useState<number[]>([]);

  function toggle(index: number): void {
    if (mode === "single") {
      setSelected([index]);
      return;
    }
    setSelected((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index],
    );
  }

  function handleSubmit(event: FormEvent): void {
    event.preventDefault();
    if (selected.length === 0) return;
    onConfirm(selected);
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>🍽️ Pick what to cook</h2>
      </div>
      <p className="card-description">
        {mode === "single"
          ? "Choose one of these ideas — we'll generate the full recipe once you pick."
          : "Choose the dishes you want for the week — we'll generate full recipes only for those."}
      </p>

      <form onSubmit={handleSubmit}>
        <ul className="idea-picker">
          {ideas.map((idea) => (
            <li key={idea.index}>
              <label>
                <input
                  type={mode === "single" ? "radio" : "checkbox"}
                  name="dish-idea"
                  checked={selected.includes(idea.index)}
                  onChange={() => toggle(idea.index)}
                />
                <span className="idea-picker-text">
                  <span className="idea-name">{idea.dish_name}</span>
                  <span className="idea-description">{idea.description}</span>
                  {idea.leftover_of_dish_name && (
                    <span className="badge badge-neutral idea-leftover-badge">
                      ♻️ reuses "{idea.leftover_of_dish_name}"
                      {idea.transformation_note && ` — ${idea.transformation_note}`}
                    </span>
                  )}
                </span>
              </label>
            </li>
          ))}
        </ul>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={submitting || selected.length === 0}
        >
          {submitting ? "Cooking up the recipe…" : "Confirm selection"}
        </button>
      </form>
    </div>
  );
}
