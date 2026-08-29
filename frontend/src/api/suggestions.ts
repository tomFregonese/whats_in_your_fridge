import { api } from "./client";

export interface FridgeInputItemPayload {
  ingredient_name: string;
  quantity_raw?: string;
  fridge_stock_item_id?: number;
}

export interface FridgeInputPayload {
  mode: "batch" | "single";
  free_text?: string;
  items: FridgeInputItemPayload[];
}

export interface Suggestion {
  id: number;
  dish_name: string;
  description: string;
  ingredients: string[];
  steps: string[];
  servings: number;
}

/** One fridge stock item automatically removed once a meal plan completes
 * (see the backend's `SuggestionService`/`FridgeStockService.deduct`).
 * Like `notes_generales`, only ever present on the response of the
 * generation call that produced it — never on a later `GET
 * /api/meal-plans/{id}` replay. */
export interface RemovedStockItem {
  id: number;
  ingredient_name: string;
  quantity_value: number | null;
  quantity_unit: string | null;
  quantity_raw: string | null;
}

/** One proposed dish idea — name + description only, no ingredients/steps
 * yet (see `DishIdeaSelector`). `index` is its position in the proposed
 * shortlist, and the key `selectIdeas`/`selectIdeasStream` select by. */
export interface DishIdea {
  index: number;
  dish_name: string;
  description: string;
}

export interface SuggestionsResult {
  status: "completed" | "clarification_needed" | "ideas_proposed";
  fridge_input_id: number;
  meal_plan_id: number | null;
  suggestions: Suggestion[];
  ideas: DishIdea[];
  notes_generales: string | null;
  removed_stock_items: RemovedStockItem[];
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

export function selectIdeas(
  runId: number,
  selectedIndexes: number[],
): Promise<SuggestionsResult> {
  return api.post<SuggestionsResult>(`/api/suggestions/runs/${String(runId)}/select`, {
    selected_indexes: selectedIndexes,
  });
}

/* ------------------------------------------------------------------ */
/* Streaming endpoint — returns the run_id to subscribe to SSE events  */
/* ------------------------------------------------------------------ */

export interface StreamStartResult {
  run_id: number;
}

export function createSuggestionsStream(payload: FridgeInputPayload): Promise<StreamStartResult> {
  return api.post<StreamStartResult>("/api/suggestions/stream", payload);
}

export function respondToClarificationStream(runId: number, answer: string): Promise<{ status: string }> {
  return api.post<{ status: string }>(`/api/suggestions/runs/${String(runId)}/respond-stream`, { answer });
}

export function selectIdeasStream(
  runId: number,
  selectedIndexes: number[],
): Promise<{ status: string }> {
  return api.post<{ status: string }>(`/api/suggestions/runs/${String(runId)}/select-stream`, {
    selected_indexes: selectedIndexes,
  });
}
