import { ApiError, api } from "./client";

export interface FridgeStockItem {
  id: number;
  ingredient_name: string;
  quantity_value: number | null;
  quantity_unit: string | null;
  quantity_raw: string | null;
  updated_at: string;
}

export interface FridgeStockItemInput {
  ingredient_name: string;
  quantity_value?: number | null;
  quantity_unit?: string | null;
  quantity_raw?: string | null;
}

export function listFridgeStockItems(): Promise<FridgeStockItem[]> {
  return api.get<FridgeStockItem[]>("/api/fridge-stock");
}

export function addFridgeStockItem(input: FridgeStockItemInput): Promise<FridgeStockItem> {
  return api.post<FridgeStockItem>("/api/fridge-stock", input);
}

export function updateFridgeStockItem(
  id: number,
  input: FridgeStockItemInput,
): Promise<FridgeStockItem> {
  return api.patch<FridgeStockItem>(`/api/fridge-stock/${String(id)}`, input);
}

export function deleteFridgeStockItem(id: number): Promise<void> {
  return api.delete(`/api/fridge-stock/${String(id)}`);
}

/** One item parsed out of a dictated audio clip — no `id`, nothing is
 * persisted until reviewed and committed via `bulkUpsertFridgeStockItems`. */
export interface DictationItem {
  ingredient_name: string;
  quantity_value: number | null;
  quantity_unit: string | null;
  quantity_raw: string | null;
}

interface DictationSseEvent {
  type: "transcribing" | "transcribed" | "items" | "error" | "done";
  text?: string;
  items?: DictationItem[];
  detail?: string;
}

export interface DictationStreamCallbacks {
  onTranscribing?: () => void;
  onTranscribed?: (text: string) => void;
  onItems?: (items: DictationItem[]) => void;
  onError?: (detail: string) => void;
}

/** Streams a recorded audio clip through the backend — local transcription,
 * then a small local model to structure it (see
 * `app/dictation_streaming_service.py`), both stages entirely on this
 * machine — rather than waiting for one big JSON response: still gives
 * the user visible progress (which stage) for the ~1-4s wait instead of a
 * static spinner. `audioFormat` must match what `audioBase64` actually
 * encodes (`VoiceDictation` always produces `"wav"` — see its docstring
 * for why).
 *
 * Manual `fetch` + stream reading rather than `EventSource`: the browser's
 * native SSE client can only ever issue GET requests, and this needs to
 * POST the audio payload. */
export async function streamDictation(
  audioBase64: string,
  audioFormat: "wav" | "mp3",
  callbacks: DictationStreamCallbacks,
): Promise<void> {
  const response = await fetch("/api/fridge-stock/dictation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audio_base64: audioBase64, audio_format: audioFormat }),
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : response.statusText;
    throw new ApiError(response.status, detail);
  }
  if (!response.body) {
    throw new Error("Streaming responses aren't supported in this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      if (!rawEvent.startsWith("data: ")) continue;
      let event: DictationSseEvent;
      try {
        event = JSON.parse(rawEvent.slice("data: ".length)) as DictationSseEvent;
      } catch {
        continue; // ignore malformed SSE events
      }

      switch (event.type) {
        case "transcribing":
          callbacks.onTranscribing?.();
          break;
        case "transcribed":
          callbacks.onTranscribed?.(event.text ?? "");
          break;
        case "items":
          callbacks.onItems?.(event.items ?? []);
          break;
        case "error":
          callbacks.onError?.(event.detail ?? "An unknown error occurred.");
          break;
        case "done":
          return;
      }
    }
  }
}

export function bulkUpsertFridgeStockItems(
  items: FridgeStockItemInput[],
): Promise<FridgeStockItem[]> {
  return api.post<FridgeStockItem[]>("/api/fridge-stock/bulk", { items });
}
