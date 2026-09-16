import { Fragment, useState } from "react";
import * as XLSX from "xlsx";
import type { AgendaEntry, Suggestion } from "../api/suggestions";
import { updateSuggestion } from "../api/suggestions";
import { ApiErrorMessage } from "./ApiErrorMessage";
import { DishRecipeDetail } from "./DishRecipeDetail";
import { FeedbackForm } from "./FeedbackForm";

interface MealPlanTableProps {
  suggestions: Suggestion[];
  agenda: AgendaEntry[];
  onSuggestionUpdated: (updated: Suggestion) => void;
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

interface Row {
  key: string;
  dayLabel: string | null;
  dish: Suggestion;
  storage: AgendaEntry["storage"] | null;
  warning: string | null;
}

function buildRows(suggestions: Suggestion[], agenda: AgendaEntry[]): Row[] {
  const byId = new Map(suggestions.map((dish) => [dish.id, dish]));
  if (agenda.length === 0) {
    return suggestions.map((dish) => ({
      key: `dish-${String(dish.id)}`,
      dayLabel: null,
      dish,
      storage: null,
      warning: null,
    }));
  }
  const rows: Row[] = [];
  for (const entry of agenda) {
    const dish = byId.get(entry.suggestion_id);
    if (!dish) continue;
    rows.push({
      key: `${String(entry.day_index)}-${String(entry.suggestion_id)}`,
      dayLabel: entry.day_index === 0 ? "Today" : `Day ${String(entry.day_index)}`,
      dish,
      storage: entry.storage,
      warning: entry.warning,
    });
  }
  return rows;
}

type ExportFormat = "xlsx" | "csv";

/** `bookType: "xlsx"` covers Excel, Numbers, and Google Sheets alike —
 * Numbers has no third-party-writable native format, but opens a `.xlsx`
 * file natively just as well as Excel does, so there's no separate
 * "Numbers" export to build. `csv` is offered alongside for anything that
 * prefers a plain, tool-agnostic tabular file. */
function exportPlan(rows: Row[], byId: Map<number, Suggestion>, format: ExportFormat): void {
  const data = rows.map((row) => ({
    Day: row.dayLabel ?? "",
    Dish: row.dish.dish_name,
    "Reuses leftovers of": row.dish.leftover_of_suggestion_id
      ? (byId.get(row.dish.leftover_of_suggestion_id)?.dish_name ?? "")
      : "",
    "Leftover note": row.dish.leftover_transformation ?? "",
    Portions: row.dish.servings,
    Storage: row.storage ? STORAGE_LABEL[row.storage] : "",
    Warning: row.warning ?? "",
  }));
  const sheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, sheet, "Meal plan");
  XLSX.writeFile(workbook, `meal-plan.${format}`, { bookType: format });
}

/** Single, unified table for a plan's day-by-day schedule: one row per
 * agenda day (or per dish, for a batch plan generated without a `days`
 * count — `agenda` is then empty, see `AgendaEntry`'s docstring), each
 * editable in place and expandable to the full recipe. Replaces the former
 * `MealAgenda` + `WeekPlan` pair so the schedule and the recipes read as
 * one linked artifact: a dish that reuses another's leftovers shows which
 * one, and how, right in its row. Only used for `mode === "batch"`
 * (`SingleDish` still handles the single-dish case, which has no agenda). */
export function MealPlanTable({ suggestions, agenda, onSuggestionUpdated }: MealPlanTableProps) {
  const byId = new Map(suggestions.map((dish) => [dish.id, dish]));
  const rows = buildRows(suggestions, agenda);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [draftDishName, setDraftDishName] = useState("");
  const [draftServings, setDraftServings] = useState("");
  const [draftLeftoverNote, setDraftLeftoverNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function toggleExpand(key: string): void {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function startEdit(row: Row): void {
    setEditingKey(row.key);
    setDraftDishName(row.dish.dish_name);
    setDraftServings(String(row.dish.servings));
    setDraftLeftoverNote(row.dish.leftover_transformation ?? "");
    setError(null);
  }

  async function saveEdit(dish: Suggestion): Promise<void> {
    const trimmedName = draftDishName.trim();
    const parsedServings = Number(draftServings);
    if (!trimmedName || !Number.isFinite(parsedServings) || parsedServings <= 0) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSuggestion(dish.id, {
        dish_name: trimmedName,
        servings: parsedServings,
        leftover_transformation: draftLeftoverNote.trim() || null,
      });
      onSuggestionUpdated(updated);
      setEditingKey(null);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  function handlePrint(): void {
    setExpanded(new Set(rows.map((row) => row.key)));
    requestAnimationFrame(() => {
      window.print();
    });
  }

  const hasDayColumn = agenda.length > 0;
  const columnCount = hasDayColumn ? 6 : 5;

  return (
    <div className="card meal-plan-table-card">
      <div className="card-header">
        <h2>📅 Your plan</h2>
        <div className="meal-plan-table-actions no-print">
          <button type="button" className="btn btn-secondary btn-sm" onClick={handlePrint}>
            🖨️ Print
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => exportPlan(rows, byId, "xlsx")}
          >
            ⬇️ Export .xlsx
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => exportPlan(rows, byId, "csv")}
          >
            ⬇️ Export .csv
          </button>
        </div>
      </div>
      <p className="card-description">
        Edit a dish's name, portions, or leftover note right here — changes are saved
        automatically.
      </p>

      <ApiErrorMessage error={error} />

      <div className="table-scroll">
        <table className="meal-plan-table">
          <thead>
            <tr>
              {hasDayColumn && <th>Day</th>}
              <th>Dish</th>
              <th>Reuses leftovers of</th>
              <th>Portions</th>
              {hasDayColumn && <th>Storage</th>}
              <th className="no-print" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isEditing = editingKey === row.key;
              const isExpanded = expanded.has(row.key);
              const parentDish = row.dish.leftover_of_suggestion_id
                ? byId.get(row.dish.leftover_of_suggestion_id)
                : undefined;

              return (
                <Fragment key={row.key}>
                  <tr>
                    {hasDayColumn && <td>{row.dayLabel}</td>}
                    <td>
                      {isEditing ? (
                        <input
                          type="text"
                          value={draftDishName}
                          onChange={(event) => setDraftDishName(event.target.value)}
                          aria-label="Dish name"
                          autoFocus
                        />
                      ) : (
                        row.dish.dish_name
                      )}
                    </td>
                    <td>
                      {parentDish ? (
                        <span className="leftover-cell">
                          <span className="badge badge-neutral">♻️ {parentDish.dish_name}</span>
                          {isEditing ? (
                            <input
                              type="text"
                              value={draftLeftoverNote}
                              onChange={(event) => setDraftLeftoverNote(event.target.value)}
                              aria-label="Leftover transformation note"
                              placeholder="How the leftovers are transformed"
                            />
                          ) : (
                            row.dish.leftover_transformation && (
                              <span className="leftover-note">
                                {row.dish.leftover_transformation}
                              </span>
                            )
                          )}
                        </span>
                      ) : (
                        <span className="model-meta">—</span>
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          type="number"
                          min={1}
                          value={draftServings}
                          onChange={(event) => setDraftServings(event.target.value)}
                          aria-label="Portions"
                        />
                      ) : (
                        row.dish.servings
                      )}
                    </td>
                    {hasDayColumn && (
                      <td>
                        {row.storage && (
                          <span className={`badge ${STORAGE_BADGE_CLASS[row.storage]}`}>
                            {STORAGE_LABEL[row.storage]}
                          </span>
                        )}
                        {row.warning && <p className="agenda-warning">{row.warning}</p>}
                      </td>
                    )}
                    <td className="no-print meal-plan-table-row-actions">
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            disabled={saving}
                            onClick={() => void saveEdit(row.dish)}
                          >
                            {saving ? "Saving…" : "Save"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            disabled={saving}
                            onClick={() => setEditingKey(null)}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="btn btn-ghost btn-icon"
                            onClick={() => startEdit(row)}
                            aria-label="Edit"
                            title="Edit"
                          >
                            ✏️
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost btn-icon"
                            onClick={() => toggleExpand(row.key)}
                            aria-expanded={isExpanded}
                            aria-label={isExpanded ? "Hide recipe" : "Show recipe"}
                            title={isExpanded ? "Hide recipe" : "Show recipe"}
                          >
                            {isExpanded ? "▲" : "▼"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="meal-plan-table-detail-row">
                      <td colSpan={columnCount}>
                        <DishRecipeDetail dish={row.dish} />
                        <FeedbackForm suggestionId={row.dish.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
