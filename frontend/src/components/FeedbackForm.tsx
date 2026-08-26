import { useState } from "react";
import { submitFeedback } from "../api/feedback";
import { ApiErrorMessage } from "./ApiErrorMessage";

interface FeedbackFormProps {
  suggestionId: number;
}

/** Thumbs up/down + an optional comment for one dish. A comment feeds back
 * into future generations as a soft preference note (see the backend's
 * `FeedbackService` docstring) — this form doesn't say so explicitly, it
 * just reads as ordinary feedback.
 *
 * "Submitted" is local UI state only: revisiting this plan later (e.g. from
 * `MealPlanHistory`) shows a blank form again, even though a resubmission
 * would just update the same row server-side — a deliberate V1
 * simplification, not a bug. */
export function FeedbackForm({ suggestionId }: FeedbackFormProps) {
  const [liked, setLiked] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const canSubmit = liked !== null || comment.trim().length > 0;

  async function handleSubmit(): Promise<void> {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback(suggestionId, {
        ...(liked !== null ? { liked } : {}),
        ...(comment.trim() ? { comment: comment.trim() } : {}),
      });
      setSubmitted(true);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return <p className="feedback-submitted">✓ Thanks for the feedback!</p>;
  }

  return (
    <div className="feedback-form">
      <div className="feedback-thumbs">
        <button
          type="button"
          className={`feedback-thumb ${liked === true ? "active" : ""}`}
          aria-label="Liked it"
          aria-pressed={liked === true}
          onClick={() => setLiked(liked === true ? null : true)}
        >
          👍
        </button>
        <button
          type="button"
          className={`feedback-thumb ${liked === false ? "active" : ""}`}
          aria-label="Didn't like it"
          aria-pressed={liked === false}
          onClick={() => setLiked(liked === false ? null : false)}
        >
          👎
        </button>
        <input
          type="text"
          placeholder="Add a comment (optional)"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          aria-label="Feedback comment"
        />
      </div>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={submitting || !canSubmit}
        onClick={() => void handleSubmit()}
      >
        {submitting ? "Sending…" : "Send feedback"}
      </button>
      <ApiErrorMessage error={error} />
    </div>
  );
}
