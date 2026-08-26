import { useState } from "react";
import type { FormEvent } from "react";

interface ClarificationModalProps {
  question: string;
  options: string[] | null;
  submitting: boolean;
  onAnswer: (answer: string) => void;
}

/** Shown whenever the agent calls `demander_precision` instead of
 * proposing dishes. Answering (free text or a quick option) resumes the
 * same conversation via `POST /api/suggestions/runs/{run_id}/respond` —
 * see `FridgeInputForm`, which owns the run id and may show this again if
 * the next turn is *also* a clarification. */
export function ClarificationModal({ question, options, submitting, onAnswer }: ClarificationModalProps) {
  const [answer, setAnswer] = useState("");

  function handleSubmit(event: FormEvent): void {
    event.preventDefault();
    const trimmed = answer.trim();
    if (!trimmed) return;
    onAnswer(trimmed);
  }

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <h2>🤔 One more thing</h2>
        <p>{question}</p>

        {options && options.length > 0 && (
          <div className="modal-options">
            {options.map((option) => (
              <button
                key={option}
                type="button"
                className="btn btn-secondary"
                disabled={submitting}
                onClick={() => onAnswer(option)}
              >
                {option}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="clarification-answer">Your answer</label>
            <input
              id="clarification-answer"
              type="text"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              autoFocus
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting || !answer.trim()}
          >
            {submitting ? "Thinking…" : "Answer"}
          </button>
        </form>
      </div>
    </div>
  );
}
