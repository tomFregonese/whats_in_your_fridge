import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { Allergy } from "../api/allergies";
import { addAllergy, deleteAllergy, listAllergies } from "../api/allergies";
import { setToken as saveToken } from "../api/auth";
import type { PreferenceNote } from "../api/preferences";
import { addPreference, deletePreference, listPreferences } from "../api/preferences";
import type { SettingsOut } from "../api/settings";
import { getSettings, updateSettings } from "../api/settings";
import { AppLayout } from "../components/AppLayout";
import { ModelField } from "../components/ModelField";
import { ServingsField } from "../components/ServingsField";

export function Settings() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);
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
    setAllergies(allergiesResult);
    setPreferences(preferencesResult);
    setLoading(false);
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function handleSaveServings(value: number): Promise<void> {
    setSettings(await updateSettings(value, settings?.openrouter_model_id ?? undefined));
  }

  async function handleSelectModel(modelId: string): Promise<void> {
    if (!settings) return;
    setSettings(await updateSettings(settings.default_servings, modelId));
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
      <AppLayout>
        <p className="empty">Loading…</p>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Everything you can configure lives here.</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>🍽️ Household</h2>
        </div>
        <ServingsField value={settings.default_servings} onSave={handleSaveServings} />
      </div>

      <div className="card">
        <div className="card-header">
          <h2>🔌 OpenRouter</h2>
          {settings.openrouter_token_configured ? (
            <span className="badge badge-success">✓ Configured</span>
          ) : (
            <span className="badge badge-neutral">Not configured</span>
          )}
        </div>
        <TokenField
          configured={settings.openrouter_token_configured}
          onSaved={() =>
            setSettings((prev) => (prev ? { ...prev, openrouter_token_configured: true } : prev))
          }
        />
        <ModelField selectedId={settings.openrouter_model_id} onSelect={handleSelectModel} />
      </div>

      <div className="card">
        <div className="card-header">
          <h2>🥜 Allergies</h2>
        </div>
        <form onSubmit={(event) => void handleAddAllergy(event)} className="inline-form">
          <input
            type="text"
            placeholder="e.g. peanut"
            value={newAllergyName}
            onChange={(event) => setNewAllergyName(event.target.value)}
            aria-label="New allergy"
          />
          <button type="submit" className="btn btn-secondary">
            Add
          </button>
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
      </div>

      <div className="card">
        <div className="card-header">
          <h2>💬 Preferences</h2>
        </div>
        <form onSubmit={(event) => void handleAddPreference(event)} className="inline-form">
          <input
            type="text"
            placeholder="e.g. loves spicy food"
            value={newPreference}
            onChange={(event) => setNewPreference(event.target.value)}
            aria-label="New preference note"
          />
          <button type="submit" className="btn btn-secondary">
            Add
          </button>
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
      </div>

      <div className="card">
        <div className="card-header">
          <h2>🔒 Security</h2>
        </div>
        <div className="field-row">
          <div className="field">
            <span className="field-label">App password</span>
            <span className="empty">Change it whenever you like.</span>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" disabled title="Coming in a later update">
            Change password
          </button>
        </div>
      </div>
    </AppLayout>
  );
}

function TokenField({ configured, onSaved }: { configured: boolean; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      await saveToken(trimmed);
      setValue("");
      setEditing(false);
      onSaved();
    } finally {
      setSubmitting(false);
    }
  }

  if (!editing) {
    return (
      <div className="field-row">
        <div className="field">
          <span className="field-label">API key</span>
          <span className="empty">{configured ? "•••• (hidden)" : "No token saved yet"}</span>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditing(true)}>
          {configured ? "Replace" : "Add token"}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="inline-form">
      <input
        type="password"
        placeholder="OpenRouter API key"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        aria-label="OpenRouter API key"
        autoFocus
      />
      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? "Saving…" : "Save"}
      </button>
      <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>
        Cancel
      </button>
    </form>
  );
}
