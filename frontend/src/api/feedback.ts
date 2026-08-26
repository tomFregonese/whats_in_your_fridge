import { api } from "./client";

export interface FeedbackPayload {
  liked?: boolean;
  comment?: string;
}

export function submitFeedback(suggestionId: number, payload: FeedbackPayload): Promise<void> {
  return api
    .post<{ id: number }>(`/api/suggestions/${String(suggestionId)}/feedback`, payload)
    .then(() => undefined);
}
