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
  status: "completed";
  fridge_input_id: number;
  suggestions: Suggestion[];
}

export function createSuggestions(payload: FridgeInputPayload): Promise<SuggestionsResult> {
  return api.post<SuggestionsResult>("/api/suggestions", payload);
}
