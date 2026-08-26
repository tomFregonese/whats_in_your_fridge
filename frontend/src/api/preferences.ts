import { api } from "./client";

export interface PreferenceNote {
  id: number;
  content: string;
  source: string;
  created_at: string;
}

export function listPreferences(): Promise<PreferenceNote[]> {
  return api.get<PreferenceNote[]>("/api/preferences");
}

export function addPreference(content: string): Promise<PreferenceNote> {
  return api.post<PreferenceNote>("/api/preferences", { content });
}

export function deletePreference(id: number): Promise<void> {
  return api.delete(`/api/preferences/${id}`);
}
