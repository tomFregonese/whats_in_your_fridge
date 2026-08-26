import { useEffect, useState } from "react";
import { AppLayout } from "../components/AppLayout";
import { ModelField } from "../components/ModelField";
import { ServingsField } from "../components/ServingsField";
import type { SettingsOut } from "../api/settings";
import { getSettings, updateSettings } from "../api/settings";

export function Home() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);

  useEffect(() => {
    void getSettings().then(setSettings);
  }, []);

  async function handleSaveServings(value: number): Promise<void> {
    setSettings(await updateSettings(value, settings?.openrouter_model_id ?? undefined));
  }

  async function handleSelectModel(modelId: string): Promise<void> {
    if (!settings) return;
    setSettings(await updateSettings(settings.default_servings, modelId));
  }

  return (
    <AppLayout>
      <div className="page-header">
        <h1>Welcome back</h1>
        <p>Here's your kitchen setup at a glance.</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>🍳 Kitchen setup</h2>
        </div>
        {settings ? (
          <>
            <ServingsField value={settings.default_servings} onSave={handleSaveServings} />
            <ModelField
              selectedId={settings.openrouter_model_id}
              onSelect={handleSelectModel}
            />
          </>
        ) : (
          <p className="empty">Loading…</p>
        )}
      </div>

      <div className="card">
        <div className="empty-state">
          <span className="icon">🥕</span>
          <p>
            Fridge input and meal suggestions are coming in a later milestone. Your setup above is
            already saved and ready for when they land.
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
