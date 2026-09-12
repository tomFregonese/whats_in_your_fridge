import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { Allergy } from "../api/allergies";
import { addAllergy, deleteAllergy, listAllergies } from "../api/allergies";
import { setToken as saveToken } from "../api/auth";
import type { Equipment } from "../api/equipment";
import { addEquipment, deleteEquipment, listEquipment } from "../api/equipment";
import type { PreferenceNote } from "../api/preferences";
import { addPreference, deletePreference, listPreferences } from "../api/preferences";
import type { ConnectionTestResult, SettingsOut } from "../api/settings";
import { getSettings, testConnection, updateSettings } from "../api/settings";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import { AppLayout } from "../components/AppLayout";
import { FreezerCapacityField } from "../components/FreezerCapacityField";
import { ModelField } from "../components/ModelField";
import { ServingsField } from "../components/ServingsField";

const EQUIPMENT_SUGGESTIONS = [
  "oven",
  "microwave",
  "blender",
  "food processor",
  "slow cooker",
  "pressure cooker",
  "air fryer",
  "stand mixer",
  "rice cooker",
  "grill",
];

export function Settings() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [preferences, setPreferences] = useState<PreferenceNote[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [newAllergyName, setNewAllergyName] = useState("");
  const [newPreference, setNewPreference] = useState("");
  const [newEquipmentName, setNewEquipmentName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  async function loadAll(): Promise<void> {
    // `loading` already starts `true` (see useState above) — this only
    // ever runs once, on mount, so there's no case to re-arm it here.
    const [settingsResult, allergiesResult, preferencesResult, equipmentResult] =
      await Promise.all([getSettings(), listAllergies(), listPreferences(), listEquipment()]);
    setSettings(settingsResult);
    setAllergies(allergiesResult);
    setPreferences(preferencesResult);
    setEquipment(equipmentResult);
    setLoading(false);
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function handleSaveServings(value: number): Promise<void> {
    setError(null);
    try {
      setSettings(await updateSettings(value, settings?.openrouter_model_id ?? undefined));
    } catch (err) {
      setError(err);
    }
  }

  async function handleSaveFreezerCapacity(value: number): Promise<void> {
    if (!settings) return;
    setError(null);
    try {
      setSettings(
        await updateSettings(
          settings.default_servings,
          settings.openrouter_model_id ?? undefined,
          value,
        ),
      );
    } catch (err) {
      setError(err);
    }
  }

  async function handleSelectModel(modelId: string): Promise<void> {
    if (!settings) return;
    setError(null);
    try {
      setSettings(await updateSettings(settings.default_servings, modelId));
    } catch (err) {
      setError(err);
    }
  }

  async function handleAddAllergy(event: FormEvent): Promise<void> {
    event.preventDefault();
    const name = newAllergyName.trim();
    if (!name) return;
    setError(null);
    try {
      const created = await addAllergy(name);
      setAllergies((prev) =>
        [...prev, created].sort((a, b) => a.ingredient_name.localeCompare(b.ingredient_name)),
      );
      setNewAllergyName("");
    } catch (err) {
      setError(err);
    }
  }

  async function handleDeleteAllergy(id: number): Promise<void> {
    setError(null);
    try {
      await deleteAllergy(id);
      setAllergies((prev) => prev.filter((allergy) => allergy.id !== id));
    } catch (err) {
      setError(err);
    }
  }

  async function handleAddPreference(event: FormEvent): Promise<void> {
    event.preventDefault();
    const content = newPreference.trim();
    if (!content) return;
    setError(null);
    try {
      const created = await addPreference(content);
      setPreferences((prev) => [created, ...prev]);
      setNewPreference("");
    } catch (err) {
      setError(err);
    }
  }

  async function handleDeletePreference(id: number): Promise<void> {
    setError(null);
    try {
      await deletePreference(id);
      setPreferences((prev) => prev.filter((note) => note.id !== id));
    } catch (err) {
      setError(err);
    }
  }

  async function handleAddEquipment(name: string): Promise<void> {
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    try {
      const created = await addEquipment(trimmed);
      setEquipment((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setNewEquipmentName("");
    } catch (err) {
      setError(err);
    }
  }

  async function handleDeleteEquipment(id: number): Promise<void> {
    setError(null);
    try {
      await deleteEquipment(id);
      setEquipment((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(err);
    }
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

      <ApiErrorMessage error={error} />

      <div className="card">
        <div className="card-header">
          <h2>🍽️ Household</h2>
        </div>
        <ServingsField value={settings.default_servings} onSave={handleSaveServings} />
        <FreezerCapacityField
          value={settings.freezer_capacity_slots}
          onSave={handleSaveFreezerCapacity}
        />
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
        <ConnectionTestIndicator
          modelId={settings.openrouter_model_id}
          tokenConfigured={settings.openrouter_token_configured}
        />
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
          <h2>🔧 Equipment</h2>
        </div>
        <p className="card-description">
          A stovetop, pots/pans, knives and basic utensils are always assumed. List anything
          else you own — only dishes that fit this list will be suggested.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void handleAddEquipment(newEquipmentName);
          }}
          className="inline-form"
        >
          <input
            type="text"
            placeholder="e.g. oven"
            value={newEquipmentName}
            onChange={(event) => setNewEquipmentName(event.target.value)}
            aria-label="New equipment"
          />
          <button type="submit" className="btn btn-secondary">
            Add
          </button>
        </form>
        {EQUIPMENT_SUGGESTIONS.filter(
          (suggestion) =>
            !equipment.some((item) => item.name.toLowerCase() === suggestion.toLowerCase()),
        ).length > 0 && (
          <div className="tag-list suggestion-list">
            {EQUIPMENT_SUGGESTIONS.filter(
              (suggestion) =>
                !equipment.some((item) => item.name.toLowerCase() === suggestion.toLowerCase()),
            ).map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void handleAddEquipment(suggestion)}
              >
                + {suggestion}
              </button>
            ))}
          </div>
        )}
        {equipment.length === 0 ? (
          <p className="empty">No equipment recorded.</p>
        ) : (
          <ul className="tag-list">
            {equipment.map((item) => (
              <li key={item.id}>
                <span>{item.name}</span>
                <button
                  type="button"
                  onClick={() => void handleDeleteEquipment(item.id)}
                  aria-label={`Remove ${item.name}`}
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

function ConnectionTestIndicator({
  modelId,
  tokenConfigured,
}: {
  modelId: string | null;
  tokenConfigured: boolean;
}) {
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [detail, setDetail] = useState<string | null>(null);

  // Reset to idle when the model or token changes
  useEffect(() => {
    setStatus("idle");
    setDetail(null);
  }, [modelId, tokenConfigured]);

  async function handleTest(): Promise<void> {
    if (!modelId || !tokenConfigured) return;
    setStatus("testing");
    setDetail(null);
    try {
      const result: ConnectionTestResult = await testConnection(modelId);
      setStatus(result.ok ? "ok" : "fail");
      setDetail(result.detail);
    } catch {
      setStatus("fail");
      setDetail("Could not reach the server.");
    }
  }

  return (
    <div className="field-row">
      <div className="field">
        <span className="field-label">Connection</span>
        {status === "idle" && <span className="empty">Not tested yet</span>}
        {status === "ok" && (
          <span className="connection-status">
            <span className="connection-dot ok" />
            Connected
          </span>
        )}
        {status === "fail" && (
          <span className="connection-status" title={detail ?? undefined}>
            <span className="connection-dot fail" />
            Failed{detail ? ` — ${detail}` : ""}
          </span>
        )}
        {status === "testing" && (
          <span className="connection-status">
            <span className="connection-dot pending" />
            Testing…
          </span>
        )}
      </div>
      <button
        type="button"
        className="btn btn-secondary btn-sm connection-test-btn"
        disabled={status === "testing" || !modelId || !tokenConfigured}
        onClick={() => void handleTest()}
      >
        {status === "testing" ? "Testing…" : "Test connection"}
      </button>
    </div>
  );
}

function TokenField({ configured, onSaved }: { configured: boolean; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await saveToken(trimmed);
      setValue("");
      setEditing(false);
      onSaved();
    } catch (err) {
      setError(err);
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
    <>
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
      <ApiErrorMessage error={error} />
    </>
  );
}
