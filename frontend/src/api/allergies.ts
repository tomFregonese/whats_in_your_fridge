import { api } from "./client";

export interface Allergy {
  id: number;
  ingredient_name: string;
  notes: string | null;
}

export function listAllergies(): Promise<Allergy[]> {
  return api.get<Allergy[]>("/api/allergies");
}

export function addAllergy(ingredientName: string, notes?: string): Promise<Allergy> {
  return api.post<Allergy>("/api/allergies", {
    ingredient_name: ingredientName,
    notes: notes ?? null,
  });
}

export function deleteAllergy(id: number): Promise<void> {
  return api.delete(`/api/allergies/${id}`);
}
