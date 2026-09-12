import type { Suggestion } from "../api/suggestions";

interface ShoppingListProps {
  suggestions: Suggestion[];
}

/** Aggregates every `to_buy` ingredient across a plan's dishes into one
 * deduplicated list — a pure frontend computation, no dedicated endpoint
 * (see the backend's `PlatIngredient.a_acheter`). Renders nothing when no
 * dish flagged anything to buy. */
export function ShoppingList({ suggestions }: ShoppingListProps) {
  const items = new Map<string, string[]>();
  for (const dish of suggestions) {
    for (const ingredient of dish.ingredients) {
      if (!ingredient.to_buy) continue;
      const key = ingredient.name.trim().toLowerCase();
      const existing = items.get(key);
      const quantity = ingredient.quantity ?? "";
      if (existing) {
        if (quantity) existing.push(quantity);
      } else {
        items.set(key, quantity ? [quantity] : []);
      }
    }
  }

  if (items.size === 0) return null;

  return (
    <div className="card">
      <div className="card-header">
        <h2>🛒 Shopping list</h2>
      </div>
      <p className="card-description">Not in your fridge — pick these up before cooking.</p>
      <ul className="tag-list">
        {[...items.entries()].map(([name, quantities]) => (
          <li key={name}>
            <span>
              {name}
              {quantities.length > 0 && ` (${quantities.join(", ")})`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
