import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { FridgeStockItem } from "../api/fridgeStock";
import { listFridgeStockItems } from "../api/fridgeStock";
import type { DishIdea, RemovedStockItem } from "../api/suggestions";
import {
  createSuggestionsStream,
  respondToClarificationStream,
  selectIdeasStream,
} from "../api/suggestions";
import { ApiErrorMessage } from "./ApiErrorMessage";
import { ClarificationModal } from "./ClarificationModal";
import { DishIdeaSelector } from "./DishIdeaSelector";
import { FridgeStockPicker } from "./FridgeStockPicker";
import { ReasoningBlock } from "./ReasoningBlock";
import type { IngredientEntry } from "./IngredientListInput";
import { IngredientListInput } from "./IngredientListInput";

interface PendingClarification {
  runId: number;
  question: string;
  options: string[] | null;
}

/** SSE event shape from the streaming endpoint */
interface SseEvent {
  type: "reasoning" | "clarification" | "ideas" | "completed" | "error" | "done";
  content?: string;
  run_id?: number;
  question?: string;
  options?: string[] | null;
  ideas?: DishIdea[];
  meal_plan_id?: number;
  notes_generales?: string | null;
  removed_stock_items?: RemovedStockItem[];
  detail?: string;
}

export function FridgeInputForm() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"batch" | "single">("batch");
  const [stockItems, setStockItems] = useState<FridgeStockItem[]>([]);
  const [selectedStockIds, setSelectedStockIds] = useState<number[]>([]);
  const [ingredients, setIngredients] = useState<IngredientEntry[]>([]);
  const [freeText, setFreeText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [clarification, setClarification] = useState<PendingClarification | null>(null);
  const [ideas, setIdeas] = useState<DishIdea[] | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [streamingActive, setStreamingActive] = useState(false);
  const runIdRef = useRef<number | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const clarifyingRef = useRef(false);

  /** Clean up the EventSource connection */
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStreamingActive(false);
    clarifyingRef.current = false;
  }, []);

  // Cleanup on unmount
  useEffect(() => cleanup, [cleanup]);

  // Loaded once on mount — the picker below reads from it, and submit
  // needs the full items (not just ids) to build the request payload.
  useEffect(() => {
    void listFridgeStockItems().then(setStockItems);
  }, []);

  /** Handle a single SSE event — called synchronously from the message handler. */
  const handleSseEvent = useCallback(
    (event: SseEvent): void => {
      switch (event.type) {
        case "reasoning":
          setReasoning((prev) => prev + (event.content ?? ""));
          break;

        case "clarification": {
          const q = event.question ?? "";
          const opts = event.options ?? null;
          const rid = event.run_id ?? 0;
          clarifyingRef.current = true;
          setIdeas(null);
          setClarification({ runId: rid, question: q, options: opts });
          break;
        }

        case "ideas":
          setClarification(null);
          setIdeas(event.ideas ?? []);
          break;

        case "completed":
          clarifyingRef.current = false;
          setClarification(null);
          setIdeas(null);
          setStreamingActive(false);
          if (event.meal_plan_id) {
            navigate(`/plan/${String(event.meal_plan_id)}`, {
              state: {
                notesGenerales: event.notes_generales ?? null,
                removedStockItems: event.removed_stock_items ?? [],
              },
            });
          }
          break;

        case "error":
          setIdeas(null);
          setError(new Error(event.detail ?? "An unknown error occurred."));
          setStreamingActive(false);
          break;

        case "done":
          setStreamingActive(false);
          clarifyingRef.current = false;
          break;
      }
    },
    [navigate],
  );

  /** Called when the user answers a clarification question via the modal */
  const handleClarificationAnswer = useCallback(
    async (answer: string) => {
      const runId = runIdRef.current;
      if (!runId) return;
      setClarification(null);
      clarifyingRef.current = false;
      try {
        await respondToClarificationStream(runId, answer);
      } catch (err) {
        setError(err);
      }
    },
    [],
  );

  /** Called when the user confirms which dish idea(s) they want cooked */
  const handleIdeaSelectionConfirm = useCallback(async (selectedIndexes: number[]) => {
    const runId = runIdRef.current;
    if (!runId) return;
    setIdeas(null);
    try {
      await selectIdeasStream(runId, selectedIndexes);
    } catch (err) {
      setError(err);
    }
  }, []);

  /** Start streaming: POST to create the stream, then open SSE */
  const handleSubmit = useCallback(
    async (event: FormEvent): Promise<void> => {
      event.preventDefault();
      if (selectedStockIds.length === 0 && ingredients.length === 0 && !freeText.trim()) {
        setError("Pick something from your fridge, add an ingredient, or describe what you have.");
        return;
      }

      setSubmitting(true);
      setError(null);
      setReasoning("");
      setClarification(null);
      setIdeas(null);
      cleanup();

      try {
        const selectedStockItems = stockItems.filter((item) => selectedStockIds.includes(item.id));
        const { run_id } = await createSuggestionsStream({
          mode,
          free_text: freeText.trim() || undefined,
          items: [
            ...selectedStockItems.map((item) => ({
              ingredient_name: item.ingredient_name,
              quantity_raw: item.quantity_raw || undefined,
              fridge_stock_item_id: item.id,
            })),
            ...ingredients.map((item) => ({
              ingredient_name: item.name,
              quantity_raw: item.quantity || undefined,
            })),
          ],
        });

        runIdRef.current = run_id;
        setStreamingActive(true);
        setSubmitting(false);

        // Open a single SSE connection for the entire run
        const es = new EventSource(`/api/suggestions/runs/${String(run_id)}/events`);
        eventSourceRef.current = es;

        es.onmessage = (msg: MessageEvent) => {
          try {
            const event: SseEvent = JSON.parse(msg.data) as SseEvent;
            handleSseEvent(event);
            // Close the EventSource on terminal events so the browser
            // doesn't loop endless reconnection attempts.
            if (event.type === "done" || event.type === "error" || event.type === "completed") {
              es.close();
              eventSourceRef.current = null;
            }
          } catch {
            // Ignore malformed SSE events
          }
        };

        es.onerror = () => {
          // The browser's EventSource auto-reconnects on transient errors.
          // We rely on the backend sending a "done" or "error" event.
        };
      } catch (err) {
        setError(err);
        setSubmitting(false);
        setStreamingActive(false);
      }
    },
    [selectedStockIds, stockItems, ingredients, freeText, mode, cleanup, handleSseEvent],
  );

  return (
    <>
      <div className="card">
        <div className="card-header">
          <h2>🥕 What's in your fridge?</h2>
        </div>
        <p className="card-description">Tell us what you've got, and we'll suggest what to cook.</p>

        <form onSubmit={(event) => void handleSubmit(event)}>
          <div className="field">
            <span className="field-label">Mode</span>
            <div className="segmented">
              <button
                type="button"
                className={mode === "batch" ? "active" : ""}
                onClick={() => setMode("batch")}
              >
                Batch cooking
              </button>
              <button
                type="button"
                className={mode === "single" ? "active" : ""}
                onClick={() => setMode("single")}
              >
                Single dish
              </button>
            </div>
          </div>

          <div className="field">
            <span className="field-label">From your fridge</span>
            <FridgeStockPicker
              items={stockItems}
              selectedIds={selectedStockIds}
              onChange={setSelectedStockIds}
            />
          </div>

          <IngredientListInput
            items={ingredients}
            onChange={setIngredients}
            label="Anything else not in your fridge list?"
          />

          <div className="field">
            <label htmlFor="free-text">Anything else? (optional)</label>
            <textarea
              id="free-text"
              rows={3}
              value={freeText}
              onChange={(event) => setFreeText(event.target.value)}
              placeholder="e.g. also have half a lemon and some leftover rice"
            />
          </div>

          <ApiErrorMessage error={error} />

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Thinking…" : "Get suggestions"}
          </button>
        </form>
      </div>

      {streamingActive && <ReasoningBlock reasoning={reasoning} active={true} />}
      {reasoning && !streamingActive && !error && (
        <ReasoningBlock reasoning={reasoning} active={false} />
      )}

      {ideas && ideas.length > 0 && (
        <DishIdeaSelector
          ideas={ideas}
          mode={mode}
          submitting={false}
          onConfirm={(selectedIndexes) => void handleIdeaSelectionConfirm(selectedIndexes)}
        />
      )}

      {clarification && (
        <ClarificationModal
          question={clarification.question}
          options={clarification.options}
          submitting={false}
          onAnswer={handleClarificationAnswer}
        />
      )}
    </>
  );
}