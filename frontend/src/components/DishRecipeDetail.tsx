import type { Suggestion } from "../api/suggestions";

/** The ingredients + steps block of a recipe — shared by `DishCard` (one
 * per dish, `WeekPlan`/`SingleDish`) and each expanded row of
 * `MealPlanTable`, so the recipe reads the same wherever it's shown. */
export function DishRecipeDetail({ dish }: { dish: Suggestion }) {
  return (
    <>
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
    </>
  );
}
