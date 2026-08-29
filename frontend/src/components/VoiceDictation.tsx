import { useRef, useState } from "react";
import { blobToBase64, WavRecorder } from "../audio/wavRecorder";
import type { DictationItem, FridgeStockItem } from "../api/fridgeStock";
import { bulkUpsertFridgeStockItems, streamDictation } from "../api/fridgeStock";
import { ApiErrorMessage } from "./ApiErrorMessage";

interface VoiceDictationProps {
  /** Called with the persisted result once the user reviews and confirms
   * — the parent (`Fridge.tsx`) merges these into its own list rather than
   * this component re-fetching everything itself. */
  onCommitted: (items: FridgeStockItem[]) => void;
}

function isRecordingSupported(): boolean {
  return Boolean(navigator.mediaDevices?.getUserMedia) && "AudioContext" in window;
}

/** `recorder.start()` rejects with a `DOMException` for anything from a
 * denied permission to a missing/busy device — none of which involve the
 * backend at all. Turned into a specific string here rather than passed
 * straight to `setError`: `ApiErrorMessage` treats any error that isn't an
 * `ApiError` as "the app's server is unreachable", which would be flatly
 * wrong (and confusing, since the rest of the page proves the server is
 * up fine) for what's actually a browser-level mic permission problem. */
function describeMicError(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  switch (name) {
    case "NotAllowedError":
      return (
        "Microphone access was denied. Allow it for this site — in Safari: " +
        "Settings for This Website → Microphone, and in macOS: System Settings → " +
        "Privacy & Security → Microphone → enable it for Safari — then try again."
      );
    case "NotFoundError":
      return "No microphone was found — connect one and try again.";
    case "NotReadableError":
      return "Couldn't access the microphone — it may be in use by another app.";
    case "SecurityError":
      return "The browser blocked microphone access on this page.";
    default:
      return "Couldn't start recording — check the microphone permission for this site and try again.";
  }
}

/** The review row below has one free-text quantity field, same as the
 * rest of the app (`Fridge.tsx`'s own add/edit form and stock list are
 * `quantity_raw`-only too) — `quantity_value`/`quantity_unit` are the
 * dictation pipeline's structured fields (see `agent/output_schema.py`),
 * not a second UI. This renders whichever the item actually has: the
 * structured value+unit when the model gave one (`quantity_raw` is null
 * in that case — see `agent/quantity_sanity_check.py`), falling back to
 * `quantity_raw` (a vague spoken amount like "a couple"). */
function formatQuantity(item: DictationItem): string {
  if (item.quantity_value !== null) {
    return item.quantity_unit ? `${item.quantity_value} ${item.quantity_unit}` : `${item.quantity_value}`;
  }
  return item.quantity_raw ?? "";
}

/** Dictate fridge items instead of typing them: records audio continuously,
 * transcribed locally (see `agent/stt_client.py`) and structured into
 * ingredient entries by a small local model (see `agent/nlp_client.py`) —
 * both stages run entirely on this machine, no OpenRouter token or
 * internet access needed.
 *
 * `WavRecorder` does simple silence detection on the raw audio it's
 * already capturing: a ~700ms pause cuts whatever was just said into its
 * own segment and keeps recording, so each dictated item gets sent for
 * processing as soon as it's finished rather than waiting for the whole
 * recording to end (`onSegment` below) — several segments can be
 * in-flight at once if the user keeps talking. A longer ~2s silence
 * auto-stops the whole recording (`onAutoStop`), same as clicking the
 * stop button by hand.
 *
 * Recording again does *not* clear the review list — it keeps appending,
 * same as another segment would. This matters once processing is
 * incremental: dictate 3 items, it auto-stops, the 3rd is still
 * resolving, and the user immediately taps the mic again to add a 4th —
 * clearing on start would silently drop that still-in-flight 3rd item.
 * The one place that *does* need to guard against a stray, already-in-
 * flight segment landing after the fact is Discard (see `sessionIdRef`
 * below) — that's the one action that means "throw this whole batch
 * away."
 *
 * Uses `getUserMedia`/`AudioContext` rather than the browser's
 * `SpeechRecognition` API on purpose: it's supported everywhere including
 * Firefox, and — since it only captures raw audio, leaving recognition to
 * the backend — has no dependency on the browser's UI language, so
 * dictating in a different language than the browser is set to just
 * works. */
export function VoiceDictation({ onCommitted }: VoiceDictationProps) {
  const [recording, setRecording] = useState(false);
  const [processingCount, setProcessingCount] = useState(0);
  const [committing, setCommitting] = useState(false);
  const [items, setItems] = useState<DictationItem[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const recorderRef = useRef<WavRecorder | null>(null);
  // Bumped only by `discardItems()` — checked before a segment's result is
  // applied, so a chunk already in flight when the user discards doesn't
  // repopulate the list right after. Not touched by start/cancel: a
  // segment already sent to the backend represents something the user
  // actually said, and should land normally regardless of what the
  // recorder does afterwards.
  const sessionIdRef = useRef(0);

  async function processSegment(blob: Blob, sessionId: number): Promise<void> {
    setProcessingCount((n) => n + 1);
    try {
      const audioBase64 = await blobToBase64(blob);
      await streamDictation(audioBase64, "wav", {
        onItems: (newItems) => {
          if (sessionIdRef.current !== sessionId) return;
          setItems((prev) => [...(prev ?? []), ...newItems]);
        },
        // A plain string, not `new Error(detail)`: the backend already sent
        // a specific, human-readable reason (timeout, rate limit, model
        // failed to comply, ...) in `detail`. Wrapping it in an `Error`
        // made `ApiErrorMessage` unable to tell it apart from a real
        // network failure, so it fell back to "can't reach the app's
        // server" — hiding the actual reason behind a misleading message.
        onError: (detail) => {
          if (sessionIdRef.current !== sessionId) return;
          setError(detail);
        },
      });
    } catch (err) {
      if (sessionIdRef.current === sessionId) setError(err);
    } finally {
      setProcessingCount((n) => n - 1);
    }
  }

  async function startRecording(): Promise<void> {
    setError(null);
    const sessionId = sessionIdRef.current;
    const recorder = new WavRecorder();
    try {
      await recorder.start({
        onSegment: (blob) => void processSegment(blob, sessionId),
        onAutoStop: () => finalizeRecording(),
      });
    } catch (err) {
      setError(describeMicError(err));
      return;
    }
    recorderRef.current = recorder;
    setRecording(true);
  }

  /** Ends the recording, flushing any trailing unsent speech — called by
   * both the manual stop button and `WavRecorder`'s auto-stop, which is
   * an addition to that button, not a replacement for it. */
  function finalizeRecording(): void {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    if (!recorder) return;

    const sessionId = sessionIdRef.current;
    const trailing = recorder.stop();
    if (trailing) void processSegment(trailing, sessionId);
  }

  function cancelRecording(): void {
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setRecording(false);
  }

  function discardItems(): void {
    sessionIdRef.current += 1;
    setItems(null);
  }

  function updateItem(index: number, patch: Partial<DictationItem>): void {
    setItems((prev) => prev?.map((item, i) => (i === index ? { ...item, ...patch } : item)) ?? null);
  }

  function removeItem(index: number): void {
    setItems((prev) => prev?.filter((_, i) => i !== index) ?? null);
  }

  async function handleConfirm(): Promise<void> {
    if (!items || items.length === 0) return;
    setCommitting(true);
    setError(null);
    try {
      const created = await bulkUpsertFridgeStockItems(
        items.map((item) => ({
          ingredient_name: item.ingredient_name,
          quantity_value: item.quantity_value,
          quantity_unit: item.quantity_unit,
          quantity_raw: item.quantity_raw,
        })),
      );
      onCommitted(created);
      setItems(null);
    } catch (err) {
      setError(err);
    } finally {
      setCommitting(false);
    }
  }

  if (!isRecordingSupported()) {
    return (
      <p className="empty">
        Voice dictation isn't supported in this browser — use the form below.
      </p>
    );
  }

  return (
    <div className="field">
      <div className="dictation-controls">
        {!recording ? (
          <button
            type="button"
            className="btn btn-icon mic-button"
            onClick={() => void startRecording()}
            aria-label="Start dictating"
          >
            🎙️
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-icon mic-button recording"
              onClick={finalizeRecording}
              aria-label="Stop and process"
            >
              ⏹️
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={cancelRecording}>
              Cancel
            </button>
          </>
        )}
        {recording && (
          <span className="connection-status">
            <span className="connection-dot pending" />
            Recording…
          </span>
        )}
        {processingCount > 0 && (
          <span className="connection-status">
            <span className="connection-dot pending" />
            Processing {processingCount} segment{processingCount > 1 ? "s" : ""}…
          </span>
        )}
      </div>

      <ApiErrorMessage error={error} />

      {items && items.length > 0 && (
        <div className="dictation-review">
          {items.map((item, index) => (
            <div key={index} className="ingredient-input-row">
              <input
                type="text"
                value={item.ingredient_name}
                onChange={(event) => updateItem(index, { ingredient_name: event.target.value })}
                aria-label="Ingredient name"
              />
              <input
                type="text"
                value={formatQuantity(item)}
                onChange={(event) =>
                  // A manual edit here is always freeform text, same as
                  // everywhere else in the app — replaces the structured
                  // value+unit rather than trying to keep them in sync
                  // with hand-typed text.
                  updateItem(index, {
                    quantity_raw: event.target.value,
                    quantity_value: null,
                    quantity_unit: null,
                  })
                }
                aria-label="Quantity"
              />
              <button
                type="button"
                className="btn btn-danger-ghost"
                onClick={() => removeItem(index)}
                aria-label={`Remove ${item.ingredient_name}`}
              >
                ×
              </button>
            </div>
          ))}
          <div className="dictation-review-actions">
            <button
              type="button"
              className="btn btn-primary"
              // Gated on `processingCount` too: a fast talker could
              // otherwise commit before their last dictated item lands.
              disabled={committing || processingCount > 0}
              onClick={() => void handleConfirm()}
            >
              {committing ? "Adding…" : "Add to fridge"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={discardItems}>
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
