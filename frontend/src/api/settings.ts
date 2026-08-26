import { api } from "./client";

export interface SettingsOut {
  default_servings: number;
  openrouter_model_id: string | null;
  openrouter_token_configured: boolean;
}

export interface FreeModel {
  id: string;
  name: string;
  context_length: number | null;
  description: string | null;
}

export function getSettings(): Promise<SettingsOut> {
  return api.get<SettingsOut>("/api/settings");
}

export function updateSettings(
  defaultServings: number,
  openrouterModelId?: string,
): Promise<SettingsOut> {
  return api.patch<SettingsOut>("/api/settings", {
    default_servings: defaultServings,
    ...(openrouterModelId !== undefined ? { openrouter_model_id: openrouterModelId } : {}),
  });
}

export function listFreeModels(): Promise<FreeModel[]> {
  return api.get<FreeModel[]>("/api/settings/models");
}

export interface ModelStatus {
  model_id: string | null;
  available: boolean;
}

export function getModelStatus(): Promise<ModelStatus> {
  return api.get<ModelStatus>("/api/settings/model-status");
}
