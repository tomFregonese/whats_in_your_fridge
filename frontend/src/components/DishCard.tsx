import type { Suggestion } from "../api/suggestions";
import { DishRecipeDetail } from "./DishRecipeDetail";
import { FeedbackForm } from "./FeedbackForm";

/** One proposed dish — used by `SingleDish` (usually just one dish, but
 * stays a list to match the backend's shape). Batch-mode plans render
 * through `MealPlanTable` instead, which shares `DishRecipeDetail` with
 * this component for the recipe body. */
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

      <DishRecipeDetail dish={dish} />

      <FeedbackForm suggestionId={dish.id} />
    </div>
  );
}
