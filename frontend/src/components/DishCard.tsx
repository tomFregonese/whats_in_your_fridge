import type { Suggestion } from "../api/suggestions";
import { FeedbackForm } from "./FeedbackForm";

/** One proposed dish — shared by `WeekPlan` (one per dish) and `SingleDish`
 * (usually just one, but stays a list to match the backend's shape). */
export function DishCard({ dish }: { dish: Suggestion }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>{dish.dish_name}</h2>
        <span className="badge badge-neutral">{dish.servings} servings</span>
      </div>
      <p className="card-description">{dish.description}</p>

      <div className="field-row">
        <span className="badge badge-neutral">🧊 keeps {dish.fridge_days} day(s) in fridge</span>
        {dish.freezer_friendly && <span className="badge badge-neutral">❄️ freezer-friendly</span>}
      </div>

      <div className="field">
        <span className="field-label">Ingredients</span>
        <ul className="tag-list">
          {dish.ingredients.map((ingredient) => (
            <li key={ingredient.name}>
              <span>
                {ingredient.name}
                {ingredient.quantity && ` (${ingredient.quantity})`}
              </span>
              {ingredient.to_buy && <span className="badge badge-warning">🛒 to buy</span>}
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

      <FeedbackForm suggestionId={dish.id} />
    </div>
  );
}
