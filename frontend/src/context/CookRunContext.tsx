import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import type { DishIdea, FridgeInputPayload, RemovedStockItem } from "../api/suggestions";
import {
  createSuggestionsStream,
  respondToClarificationStream,
  selectIdeasStream,
} from "../api/suggestions";

export interface PendingClarification {
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

interface CookRunState {
  submitting: boolean;
  error: unknown;
  reasoning: string;
  streamingActive: boolean;
  clarification: PendingClarification | null;
  ideas: DishIdea[] | null;
  mode: "batch" | "single";
}

interface CookRunContextValue extends CookRunState {
  startRun: (payload: FridgeInputPayload) => Promise<void>;
  answerClarification: (answer: string) => Promise<void>;
  confirmIdeas: (selectedIndexes: number[]) => Promise<void>;
  dismissError: () => void;
}

const CookRunContext = createContext<CookRunContextValue | null>(null);

const initialState: CookRunState = {
  submitting: false,
  error: null,
  reasoning: "",
  streamingActive: false,
  clarification: null,
  ideas: null,
  mode: "batch",
};

/** Owns the lifecycle of an in-flight "Cook" generation — the SSE
 * connection, accumulated reasoning tokens, and any clarification/idea-
 * selection pause — above the router's `<Routes>` (see `App.tsx`), so
 * navigating to another page never drops it. `FridgeInputForm` is the only
 * (re)mounting consumer: it keeps rendering whatever this holds even after
 * being unmounted and remounted by a trip away from and back to Home. */
export function CookRunProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [state, setState] = useState<CookRunState>(initialState);
  const runIdRef = useRef<number | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const closeStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // Only fires when the whole app tears down — this provider lives above
  // every route.
  useEffect(() => closeStream, [closeStream]);

  const handleSseEvent = useCallback(
    (event: SseEvent): void => {
      switch (event.type) {
        case "reasoning":
          setState((prev) => ({ ...prev, reasoning: prev.reasoning + (event.content ?? "") }));
          break;

        case "clarification": {
          const question = event.question ?? "";
          const options = event.options ?? null;
          const runId = event.run_id ?? 0;
          setState((prev) => ({
            ...prev,
            ideas: null,
            clarification: { runId, question, options },
          }));
          break;
        }

        case "ideas":
          setState((prev) => ({ ...prev, clarification: null, ideas: event.ideas ?? [] }));
          break;

        case "completed":
          setState((prev) => ({
            ...prev,
            clarification: null,
            ideas: null,
            streamingActive: false,
          }));
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
          setState((prev) => ({
            ...prev,
            ideas: null,
            error: new Error(event.detail ?? "An unknown error occurred."),
            streamingActive: false,
          }));
          break;

        case "done":
          setState((prev) => ({ ...prev, streamingActive: false }));
          break;
      }
    },
    [navigate],
  );

  const startRun = useCallback(
    async (payload: FridgeInputPayload): Promise<void> => {
      closeStream();
      setState({ ...initialState, submitting: true, mode: payload.mode });

      try {
        const { run_id } = await createSuggestionsStream(payload);
        runIdRef.current = run_id;
        setState((prev) => ({ ...prev, submitting: false, streamingActive: true }));

        // Open a single SSE connection for the entire run — it lives as
        // long as this provider does, not as long as whichever page
        // happens to be mounted.
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
        setState((prev) => ({ ...prev, error: err, submitting: false, streamingActive: false }));
      }
    },
    [closeStream, handleSseEvent],
  );

  const answerClarification = useCallback(async (answer: string): Promise<void> => {
    const runId = runIdRef.current;
    if (!runId) return;
    setState((prev) => ({ ...prev, clarification: null }));
    try {
      await respondToClarificationStream(runId, answer);
    } catch (err) {
      setState((prev) => ({ ...prev, error: err }));
    }
  }, []);

  const confirmIdeas = useCallback(async (selectedIndexes: number[]): Promise<void> => {
    const runId = runIdRef.current;
    if (!runId) return;
    setState((prev) => ({ ...prev, ideas: null }));
    try {
      await selectIdeasStream(runId, selectedIndexes);
    } catch (err) {
      setState((prev) => ({ ...prev, error: err }));
    }
  }, []);

  const dismissError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return (
    <CookRunContext.Provider
      value={{ ...state, startRun, answerClarification, confirmIdeas, dismissError }}
    >
      {children}
    </CookRunContext.Provider>
  );
}

export function useCookRun(): CookRunContextValue {
  const ctx = useContext(CookRunContext);
  if (!ctx) {
    throw new Error("useCookRun must be used within a CookRunProvider");
  }
  return ctx;
}
