import { api } from "./client";

export interface AuthStatus {
  password_set: boolean;
  unlocked: boolean;
}

export function getAuthStatus(): Promise<AuthStatus> {
  return api.get<AuthStatus>("/api/auth/status");
}

export function setupPassword(password: string): Promise<void> {
  return api.post<void>("/api/auth/setup", { password });
}

export function unlock(password: string): Promise<void> {
  return api.post<void>("/api/auth/unlock", { password });
}
