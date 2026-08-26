import { api } from "./client";
import type { Suggestion } from "./suggestions";

export interface MealPlan {
  id: number;
  mode: "batch" | "single";
  created_at: string;
  suggestions: Suggestion[];
}

export function getMealPlan(id: number): Promise<MealPlan> {
  return api.get<MealPlan>(`/api/meal-plans/${String(id)}`);
}

export function listMealPlans(): Promise<MealPlan[]> {
  return api.get<MealPlan[]>("/api/meal-plans");
}
