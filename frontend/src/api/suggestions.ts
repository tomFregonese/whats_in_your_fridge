import { api } from "./client";

export interface FridgeInputItemPayload {
  ingredient_name: string;
  quantity_raw?: string;
}

export interface FridgeInputPayload {
  mode: "batch" | "single";
  free_text?: string;
  items: FridgeInputItemPayload[];
}

export interface Suggestion {
  dish_name: string;
  description: string;
  ingredients: string[];
  steps: string[];
  servings: number;
}

export interface SuggestionsResult {
  status: "completed" | "clarification_needed";
  fridge_input_id: number;
  suggestions: Suggestion[];
  notes_generales: string | null;
  run_id: number | null;
  question: string | null;
  options: string[] | null;
}

export function createSuggestions(payload: FridgeInputPayload): Promise<SuggestionsResult> {
  return api.post<SuggestionsResult>("/api/suggestions", payload);
}

export function respondToClarification(runId: number, answer: string): Promise<SuggestionsResult> {
  return api.post<SuggestionsResult>(`/api/suggestions/runs/${String(runId)}/respond`, { answer });
}
