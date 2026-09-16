import { api } from "./client";

export interface FridgeInputItemPayload {
  ingredient_name: string;
  quantity_raw?: string;
  fridge_stock_item_id?: number;
}

/** How strictly a generation should stick to what's already available —
 * orthogonal to `mode` (session shape). Defaults to `fridge_plus_shopping`
 * on the backend when omitted, matching this app's original behavior. */
export type SourcingMode = "fridge_only" | "fridge_plus_shopping" | "shopping_only";

export interface FridgeInputPayload {
  mode: "batch" | "single";
  sourcing_mode: SourcingMode;
  /** Required by the backend when `mode === "batch"` — how many days this
   * batch-cooking session should cover, sizing the idea shortlist and
   * later the agenda (see `MealPlanTable`). Ignored in `single` mode. */
  days?: number;
  free_text?: string;
  items: FridgeInputItemPayload[];
}

export interface Ingredient {
  name: string;
  quantity: string | null;
  /** Not in the fridge/pantry — needs to be bought (see the shopping
   * list, aggregated across a plan's dishes by `ShoppingList`). */
  to_buy: boolean;
}

export interface Suggestion {
  id: number;
  dish_name: string;
  description: string;
  ingredients: Ingredient[];
  steps: string[];
  servings: number;
  /** Estimated days this dish keeps refrigerated after cooking. */
  fridge_days: number;
  freezer_friendly: boolean;
  /** Id of another `Suggestion` in the same plan whose leftovers this dish
   * transforms (e.g. yesterday's pasta turned into today's gratin) — see
   * `MealPlanTable`. `null` for a standalone dish. */
  leftover_of_suggestion_id: number | null;
  /** How the leftovers were transformed into this dish — set whenever
   * `leftover_of_suggestion_id` is. */
  leftover_transformation: string | null;
}

/** One day of a batch-cooking agenda (see `MealPlanTable`) — which dish is
 * eaten on `day_index` (0 = the day the batch is cooked) and how it needs
 * to be stored to get there. Persisted, so present both right after
 * generation and on later `GET /api/meal-plans/{id}` reads — unlike
 * `notes_generales`/`removed_stock_items`. Only populated for a batch
 * plan generated with a `days` count. */
export interface AgendaEntry {
  day_index: number;
  suggestion_id: number;
  storage: "fresh" | "frozen" | "at_risk";
  warning: string | null;
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
  /** Exact `dish_name` of another idea in this same shortlist whose
   * leftovers this one reuses — `null` for a standalone idea. */
  leftover_of_dish_name: string | null;
  /** How the leftovers are turned into this dish — set whenever
   * `leftover_of_dish_name` is. */
  transformation_note: string | null;
}

export interface SuggestionsResult {
  status: "completed" | "clarification_needed" | "ideas_proposed";
  fridge_input_id: number;
  meal_plan_id: number | null;
  suggestions: Suggestion[];
  ideas: DishIdea[];
  notes_generales: string | null;
  removed_stock_items: RemovedStockItem[];
  agenda: AgendaEntry[];
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

export interface SuggestionUpdateInput {
  dish_name: string;
  servings: number;
  leftover_transformation: string | null;
}

/** Backs the meal-plan table's inline edit — full-replace of the editable
 * fields, same convention as `updateFridgeStockItem`. */
export function updateSuggestion(
  id: number,
  input: SuggestionUpdateInput,
): Promise<Suggestion> {
  return api.patch<Suggestion>(`/api/suggestions/${String(id)}`, input);
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
