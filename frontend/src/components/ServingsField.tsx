import { useState } from "react";
import type { FormEvent } from "react";

interface ServingsFieldProps {
  value: number;
  onSave: (value: number) => Promise<void>;
}

/** Reusable "default servings" editor — used on both Home (quick access)
 * and Settings (full household config). */
export function ServingsField({ value, onSave }: ServingsFieldProps) {
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave(draft);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="inline-form">
      <div className="field">
        <label htmlFor="servings">Default number of servings</label>
        <input
          id="servings"
          type="number"
          min={1}
          value={draft}
          onChange={(event) => setDraft(Number(event.target.value))}
        />
      </div>
      <button type="submit" className="btn btn-primary" disabled={saving || draft === value}>
        {saving ? "Saving…" : "Save"}
      </button>
    </form>
  );
}
