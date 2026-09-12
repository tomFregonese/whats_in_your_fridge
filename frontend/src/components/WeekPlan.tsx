import type { Suggestion } from "../api/suggestions";
import { DishCard } from "./DishCard";
import { ShoppingList } from "./ShoppingList";

interface WeekPlanProps {
  suggestions: Suggestion[];
  notesGenerales?: string | null;
}

/** Batch-cooking mode: every dish suggested for the week, one card each. */
export function WeekPlan({ suggestions, notesGenerales }: WeekPlanProps) {
  return (
    <>
      <div className="page-header">
        <h1>Your week's plan</h1>
        <p>
          {suggestions.length} dish{suggestions.length === 1 ? "" : "es"} to batch-cook.
        </p>
        {notesGenerales && <p className="plan-notes">{notesGenerales}</p>}
      </div>

      <ShoppingList suggestions={suggestions} />

      {suggestions.map((dish) => (
        <DishCard dish={dish} key={dish.dish_name} />
      ))}
    </>
  );
}
