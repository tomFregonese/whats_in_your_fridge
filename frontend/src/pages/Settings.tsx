import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { Allergy } from "../api/allergies";
import { addAllergy, deleteAllergy, listAllergies } from "../api/allergies";
import type { PreferenceNote } from "../api/preferences";
import { addPreference, deletePreference, listPreferences } from "../api/preferences";
import type { SettingsOut } from "../api/settings";
import { getSettings, updateSettings } from "../api/settings";

export function Settings() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);
  const [servingsDraft, setServingsDraft] = useState(4);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [preferences, setPreferences] = useState<PreferenceNote[]>([]);
  const [newAllergyName, setNewAllergyName] = useState("");
  const [newPreference, setNewPreference] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadAll(): Promise<void> {
    // `loading` already starts `true` (see useState above) — this only
    // ever runs once, on mount, so there's no case to re-arm it here.
    const [settingsResult, allergiesResult, preferencesResult] = await Promise.all([
      getSettings(),
      listAllergies(),
      listPreferences(),
    ]);
    setSettings(settingsResult);
    setServingsDraft(settingsResult.default_servings);
    setAllergies(allergiesResult);
    setPreferences(preferencesResult);
    setLoading(false);
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function handleServingsSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setSettings(await updateSettings(servingsDraft));
  }

  async function handleAddAllergy(event: FormEvent): Promise<void> {
    event.preventDefault();
    const name = newAllergyName.trim();
    if (!name) return;
    const created = await addAllergy(name);
    setAllergies((prev) =>
      [...prev, created].sort((a, b) => a.ingredient_name.localeCompare(b.ingredient_name)),
    );
    setNewAllergyName("");
  }

  async function handleDeleteAllergy(id: number): Promise<void> {
    await deleteAllergy(id);
    setAllergies((prev) => prev.filter((allergy) => allergy.id !== id));
  }

  async function handleAddPreference(event: FormEvent): Promise<void> {
    event.preventDefault();
    const content = newPreference.trim();
    if (!content) return;
    const created = await addPreference(content);
    setPreferences((prev) => [created, ...prev]);
    setNewPreference("");
  }

  async function handleDeletePreference(id: number): Promise<void> {
    await deletePreference(id);
    setPreferences((prev) => prev.filter((note) => note.id !== id));
  }

  if (loading || !settings) {
    return (
      <main className="page settings">
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main className="page settings">
      <h1>Settings</h1>

      <section>
        <h2>Household</h2>
        <form onSubmit={(event) => void handleServingsSubmit(event)} className="inline-form">
          <div className="field">
            <label htmlFor="servings">Default number of servings</label>
            <input
              id="servings"
              type="number"
              min={1}
              value={servingsDraft}
              onChange={(event) => setServingsDraft(Number(event.target.value))}
            />
          </div>
          <button type="submit">Save</button>
        </form>
      </section>

      <section>
        <h2>Allergies</h2>
        <form onSubmit={(event) => void handleAddAllergy(event)} className="inline-form">
          <input
            type="text"
            placeholder="e.g. peanut"
            value={newAllergyName}
            onChange={(event) => setNewAllergyName(event.target.value)}
            aria-label="New allergy"
          />
          <button type="submit">Add</button>
        </form>
        {allergies.length === 0 ? (
          <p className="empty">No allergies recorded.</p>
        ) : (
          <ul className="tag-list">
            {allergies.map((allergy) => (
              <li key={allergy.id}>
                <span>{allergy.ingredient_name}</span>
                <button
                  type="button"
                  onClick={() => void handleDeleteAllergy(allergy.id)}
                  aria-label={`Remove ${allergy.ingredient_name}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Preferences</h2>
        <form onSubmit={(event) => void handleAddPreference(event)} className="inline-form">
          <input
            type="text"
            placeholder="e.g. loves spicy food"
            value={newPreference}
            onChange={(event) => setNewPreference(event.target.value)}
            aria-label="New preference note"
          />
          <button type="submit">Add</button>
        </form>
        {preferences.length === 0 ? (
          <p className="empty">No preferences recorded.</p>
        ) : (
          <ul className="tag-list">
            {preferences.map((note) => (
              <li key={note.id}>
                <span>{note.content}</span>
                <button
                  type="button"
                  onClick={() => void handleDeletePreference(note.id)}
                  aria-label="Remove note"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
