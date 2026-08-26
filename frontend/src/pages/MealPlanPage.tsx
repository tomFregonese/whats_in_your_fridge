import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { MealPlan } from "../api/mealPlans";
import { getMealPlan } from "../api/mealPlans";
import { AppLayout } from "../components/AppLayout";
import { SingleDish } from "../components/SingleDish";
import { WeekPlan } from "../components/WeekPlan";

/** Routed at `/plan/:id`. Backs both `WeekPlan` (batch) and `SingleDish`
 * (single) — branches on the persisted plan's `mode`.
 *
 * Reached either right after a generation completes (`FridgeInputForm`
 * navigates here and passes the fresh `notes_generales` via router state —
 * it isn't persisted, see the backend's `SuggestionService` docstring, so
 * it's only present on that first visit) or from `MealPlanHistory` (no
 * state — notes are simply absent on replays).
 */
export function MealPlanPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const notesGenerales = (location.state as { notesGenerales?: string | null } | null)
    ?.notesGenerales;

  const [mealPlan, setMealPlan] = useState<MealPlan | null>(null);
  const [notFound, setNotFound] = useState(false);

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

  return (
    <AppLayout>
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
