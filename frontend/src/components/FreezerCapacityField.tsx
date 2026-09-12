import { useState } from "react";
import type { FormEvent } from "react";

interface FreezerCapacityFieldProps {
  value: number | null;
  onSave: (value: number) => Promise<void>;
}

/** Household freezer capacity, in number of dish portions — feeds the
 * agenda scheduler's freezer fallback (see `MealAgenda`,
 * `services/meal_agenda_service.py`). Blank means unlimited, the default
 * until set — there's no way to clear it back to blank once set in V1
 * (mirrors the backend Dto's documented limitation). */
export function FreezerCapacityField({ value, onSave }: FreezerCapacityFieldProps) {
  const [draft, setDraft] = useState(value?.toString() ?? "");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const parsed = Number(draft);
    if (!draft || !Number.isFinite(parsed) || parsed <= 0) return;
    setSaving(true);
    try {
      await onSave(parsed);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="inline-form">
      <div className="field">
        <label htmlFor="freezer-capacity">Freezer capacity (portions)</label>
        <input
          id="freezer-capacity"
          type="number"
          min={1}
          placeholder="Unlimited"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
      <button
        type="submit"
        className="btn btn-primary"
        disabled={saving || draft === (value?.toString() ?? "")}
      >
        {saving ? "Saving…" : "Save"}
      </button>
    </form>
  );
}
