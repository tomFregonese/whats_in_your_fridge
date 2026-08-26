import { Link, useLocation } from "react-router-dom";
import type { SuggestionsResult as SuggestionsResultType } from "../api/suggestions";
import { AppLayout } from "../components/AppLayout";

export function SuggestionsResult() {
  const location = useLocation();
  const result = (location.state as { result?: SuggestionsResultType } | null)?.result;

  if (!result) {
    return (
      <AppLayout>
        <div className="card">
          <div className="empty-state">
            <span className="icon">🤔</span>
            <p>No suggestions to show yet — start by telling us what's in your fridge.</p>
          </div>
          <Link to="/" className="btn btn-primary btn-block">
            Back to fridge input
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Here's what we suggest</h1>
        <p>Mocked for now — real suggestions land once the OpenRouter agent is wired in.</p>
      </div>

      {result.suggestions.map((dish) => (
        <div className="card" key={dish.dish_name}>
          <div className="card-header">
            <h2>{dish.dish_name}</h2>
            <span className="badge badge-neutral">{dish.servings} servings</span>
          </div>
          <p className="card-description">{dish.description}</p>

          <div className="field">
            <span className="field-label">Ingredients</span>
            <ul className="tag-list">
              {dish.ingredients.map((ingredient) => (
                <li key={ingredient}>
                  <span>{ingredient}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="field">
            <span className="field-label">Steps</span>
            <ol className="steps-list">
              {dish.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </div>
      ))}

      <Link to="/" className="btn btn-secondary">
        ← Start over
      </Link>
    </AppLayout>
  );
}
