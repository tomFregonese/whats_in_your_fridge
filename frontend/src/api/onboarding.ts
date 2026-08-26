import { api } from "./client";
import type { SettingsOut } from "./settings";

export interface OnboardingStatus {
  onboarded: boolean;
}

export interface OnboardingPayload {
  default_servings: number;
  allergies: string[];
  preference_notes: string[];
  openrouter_model_id?: string;
}

export function getOnboardingStatus(): Promise<OnboardingStatus> {
  return api.get<OnboardingStatus>("/api/onboarding/status");
}

export function completeOnboarding(payload: OnboardingPayload): Promise<SettingsOut> {
  return api.post<SettingsOut>("/api/onboarding", payload);
}
