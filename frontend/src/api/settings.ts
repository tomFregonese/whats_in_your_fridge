import { api } from "./client";

export interface SettingsOut {
  default_servings: number;
  openrouter_model_id: string | null;
}

export function getSettings(): Promise<SettingsOut> {
  return api.get<SettingsOut>("/api/settings");
}

export function updateSettings(defaultServings: number): Promise<SettingsOut> {
  return api.patch<SettingsOut>("/api/settings", { default_servings: defaultServings });
}
