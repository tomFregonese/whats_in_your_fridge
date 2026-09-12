import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { addFridgeStockItem } from "../api/fridgeStock";
import type { MealPlan } from "../api/mealPlans";
import { getMealPlan } from "../api/mealPlans";
import type { RemovedStockItem } from "../api/suggestions";
import { AppLayout } from "../components/AppLayout";
import { MealAgenda } from "../components/MealAgenda";
import { SingleDish } from "../components/SingleDish";
import { WeekPlan } from "../components/WeekPlan";

/** Routed at `/plan/:id`. Backs both `WeekPlan` (batch) and `SingleDish`
 * (single) — branches on the persisted plan's `mode`.
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

  return (
    <AppLayout>
      {removedStockItems.length > 0 && (
        <div className="card">
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

      {mealPlan.agenda.length > 0 && (
        <MealAgenda agenda={mealPlan.agenda} suggestions={mealPlan.suggestions} />
      )}

      {mealPlan.mode === "single" ? (
        <SingleDish suggestions={mealPlan.suggestions} notesGenerales={notesGenerales} />
      ) : (
        <WeekPlan suggestions={mealPlan.suggestions} notesGenerales={notesGenerales} />
      )}
      <Link to="/" className="btn btn-secondary">
        ← Start over
      </Link>
    </AppLayout>
  );
}
