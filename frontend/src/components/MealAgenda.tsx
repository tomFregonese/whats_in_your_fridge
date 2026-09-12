import type { AgendaEntry, Suggestion } from "../api/suggestions";

interface MealAgendaProps {
  agenda: AgendaEntry[];
  suggestions: Suggestion[];
}

const STORAGE_LABEL: Record<AgendaEntry["storage"], string> = {
  fresh: "🧊 fridge",
  frozen: "❄️ freezer",
  at_risk: "⚠️ at risk",
};

const STORAGE_BADGE_CLASS: Record<AgendaEntry["storage"], string> = {
  fresh: "badge-neutral",
  frozen: "badge-neutral",
  at_risk: "badge-danger",
};

/** Batch-cooking agenda: which dish is eaten on which day, and whether it
 * needs the freezer to get there — see the backend's
 * `services/meal_agenda_service.py` (a deterministic scheduler, never the
 * LLM). Only rendered when a plan has one (batch mode, generated with a
 * `days` count — see `MealPlanPage`). */
export function MealAgenda({ agenda, suggestions }: MealAgendaProps) {
  const byId = new Map(suggestions.map((dish) => [dish.id, dish]));
  const byDay = new Map<number, AgendaEntry[]>();
  for (const entry of agenda) {
    const existing = byDay.get(entry.day_index);
    if (existing) existing.push(entry);
    else byDay.set(entry.day_index, [entry]);
  }
  const days = [...byDay.keys()].sort((a, b) => a - b);

  return (
    <div className="card">
      <div className="card-header">
        <h2>📅 Agenda</h2>
      </div>
      <p className="card-description">
        When to eat what — the most perishable dishes come first.
      </p>
      <ul className="agenda-list">
        {days.map((day) => (
          <li key={day} className="agenda-day">
            <span className="agenda-day-label">{day === 0 ? "Today" : `Day ${String(day)}`}</span>
            <div className="agenda-day-entries">
              {(byDay.get(day) ?? []).map((entry) => {
                const dish = byId.get(entry.suggestion_id);
                return (
                  <div key={`${String(entry.day_index)}-${String(entry.suggestion_id)}`}>
                    <div className="agenda-entry">
                      <span>{dish?.dish_name ?? "Unknown dish"}</span>
                      <span className={`badge ${STORAGE_BADGE_CLASS[entry.storage]}`}>
                        {STORAGE_LABEL[entry.storage]}
                      </span>
                    </div>
                    {entry.warning && <p className="agenda-warning">{entry.warning}</p>}
                  </div>
                );
              })}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
