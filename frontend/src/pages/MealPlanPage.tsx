import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { addFridgeStockItem } from "../api/fridgeStock";
import type { MealPlan } from "../api/mealPlans";
import { getMealPlan } from "../api/mealPlans";
import type { RemovedStockItem, Suggestion } from "../api/suggestions";
import { AppLayout } from "../components/AppLayout";
import { MealPlanTable } from "../components/MealPlanTable";
import { ShoppingList } from "../components/ShoppingList";
import { SingleDish } from "../components/SingleDish";

/** Routed at `/plan/:id`. Backs both `MealPlanTable` (batch) and
 * `SingleDish` (single) — branches on the persisted plan's `mode`.
 *
 * Reached either right after a generation completes (`FridgeInputForm`
 * navigates here and passes the fresh `notes_generales`/`removedStockItems`
 * via router state — neither is persisted, see the backend's
 * `SuggestionService` docstring, so both are only present on that first
 * visit) or from `MealPlanHistory` (no state — both are simply absent on
 * replays).
 */
export function MealPlanPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as {
    notesGenerales?: string | null;
    removedStockItems?: RemovedStockItem[];
  } | null;
  const notesGenerales = state?.notesGenerales;

  const [mealPlan, setMealPlan] = useState<MealPlan | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [removedStockItems, setRemovedStockItems] = useState<RemovedStockItem[]>(
    state?.removedStockItems ?? [],
  );

  useEffect(() => {
    setMealPlan(null);
    setNotFound(false);
    if (!id) return;
    getMealPlan(Number(id))
      .then(setMealPlan)
      .catch(() => setNotFound(true));
  }, [id]);

  if (notFound) {
    return (
      <AppLayout>
        <div className="card">
          <div className="empty-state">
            <span className="icon">🤔</span>
            <p>This meal plan couldn't be found.</p>
          </div>
          <Link to="/" className="btn btn-primary btn-block">
            Back to fridge input
          </Link>
        </div>
      </AppLayout>
    );
  }

  if (!mealPlan) {
    return (
      <AppLayout>
        <p className="empty">Loading…</p>
      </AppLayout>
    );
  }

  async function handlePutBack(item: RemovedStockItem): Promise<void> {
    await addFridgeStockItem({
      ingredient_name: item.ingredient_name,
      quantity_value: item.quantity_value,
      quantity_unit: item.quantity_unit,
      quantity_raw: item.quantity_raw,
    });
    setRemovedStockItems((prev) => prev.filter((i) => i.id !== item.id));
  }

  function handleSuggestionUpdated(updated: Suggestion): void {
    setMealPlan((prev) =>
      prev
        ? {
            ...prev,
            suggestions: prev.suggestions.map((s) => (s.id === updated.id ? updated : s)),
          }
        : prev,
    );
  }

  return (
    <AppLayout>
      {removedStockItems.length > 0 && (
        <div className="card no-print">
          <div className="card-header">
            <h2>🧊 Updated your fridge</h2>
          </div>
          <p className="card-description">
            These were used in this plan and removed from your fridge stock.
          </p>
          <ul className="fridge-item-list">
            {removedStockItems.map((item) => (
              <li key={item.id} className="fridge-item-row">
                <span className="fridge-item-name">
                  {item.ingredient_name}
                  {item.quantity_raw && <span className="model-meta"> · {item.quantity_raw}</span>}
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void handlePutBack(item)}
                >
                  Put back
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {mealPlan.mode === "single" ? (
        <SingleDish suggestions={mealPlan.suggestions} notesGenerales={notesGenerales} />
      ) : (
        <>
          <div className="page-header">
            <h1>Your week's plan</h1>
            <p>
              {mealPlan.suggestions.length} dish{mealPlan.suggestions.length === 1 ? "" : "es"} to
              batch-cook.
            </p>
            {notesGenerales && <p className="plan-notes">{notesGenerales}</p>}
          </div>
          <ShoppingList suggestions={mealPlan.suggestions} />
          <MealPlanTable
            suggestions={mealPlan.suggestions}
            agenda={mealPlan.agenda}
            onSuggestionUpdated={handleSuggestionUpdated}
          />
        </>
      )}
      <Link to="/" className="btn btn-secondary no-print">
        ← Start over
      </Link>
    </AppLayout>
  );
}
