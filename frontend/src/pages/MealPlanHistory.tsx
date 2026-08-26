import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { MealPlan } from "../api/mealPlans";
import { listMealPlans } from "../api/mealPlans";
import { AppLayout } from "../components/AppLayout";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Routed at `/history` — every persisted meal plan, most recent first
 * (the backend already orders them that way), read-only. Each row links
 * to `/plan/:id`, the same detail view a fresh generation lands on. */
export function MealPlanHistory() {
  const [plans, setPlans] = useState<MealPlan[] | null>(null);

  useEffect(() => {
    void listMealPlans().then(setPlans);
  }, []);

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Past plans</h1>
        <p>Everything you've cooked so far.</p>
      </div>

      {!plans ? (
        <p className="empty">Loading…</p>
      ) : plans.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="icon">📭</span>
            <p>No meal plans yet — your first one will show up here.</p>
          </div>
        </div>
      ) : (
        <ul className="history-list">
          {plans.map((plan) => (
            <li key={plan.id}>
              <Link to={`/plan/${String(plan.id)}`} className="history-item">
                <div className="history-item-main">
                  <span className="badge badge-neutral">
                    {plan.mode === "batch" ? "Batch" : "Single dish"}
                  </span>
                  <span className="history-item-date">{formatDate(plan.created_at)}</span>
                </div>
                <p className="history-item-dishes">
                  {plan.suggestions.map((dish) => dish.dish_name).join(" · ")}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppLayout>
  );
}
