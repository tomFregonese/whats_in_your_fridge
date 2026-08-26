import type { Suggestion } from "../api/suggestions";
import { DishCard } from "./DishCard";

interface SingleDishProps {
  suggestions: Suggestion[];
  notesGenerales?: string | null;
}

/** Single-dish mode: the simplified result screen — no "N dishes" framing,
 * just the one thing to cook. */
export function SingleDish({ suggestions, notesGenerales }: SingleDishProps) {
  return (
    <>
      <div className="page-header">
        <h1>Here's what to cook</h1>
        {notesGenerales && <p className="plan-notes">{notesGenerales}</p>}
      </div>

      {suggestions.map((dish) => (
        <DishCard dish={dish} key={dish.dish_name} />
      ))}
    </>
  );
}
