import { api } from "./client";

export interface Equipment {
  id: number;
  name: string;
}

export function listEquipment(): Promise<Equipment[]> {
  return api.get<Equipment[]>("/api/equipment");
}

export function addEquipment(name: string): Promise<Equipment> {
  return api.post<Equipment>("/api/equipment", { name });
}

export function deleteEquipment(id: number): Promise<void> {
  return api.delete(`/api/equipment/${id}`);
}
