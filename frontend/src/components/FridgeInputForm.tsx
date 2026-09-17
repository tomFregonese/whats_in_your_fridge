import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { FridgeStockItem } from "../api/fridgeStock";
import { listFridgeStockItems } from "../api/fridgeStock";
import type { SourcingMode } from "../api/suggestions";
import { useCookRun } from "../context/CookRunContext";
import { ApiErrorMessage } from "./ApiErrorMessage";
import { ClarificationModal } from "./ClarificationModal";
import { DishIdeaSelector } from "./DishIdeaSelector";
import { FridgeStockPicker } from "./FridgeStockPicker";
import { ReasoningBlock } from "./ReasoningBlock";
import type { IngredientEntry } from "./IngredientListInput";
import { IngredientListInput } from "./IngredientListInput";

const DEFAULT_DAYS = 5;
const MIN_DAYS = 1;
const MAX_DAYS = 14;

/** The fridge-contents input form plus whatever `CookRunProvider` reports
 * about the "Cook" request it started — reasoning, clarification, and idea
 * selection all keep rendering here even after a trip away from and back
 * to Home, since that state lives above the router, not in this
 * component's own state (see `CookRunContext`). */
export function FridgeInputForm() {
  const {
    submitting,
    error: runError,
    reasoning,
    streamingActive,
    clarification,
    ideas,
    mode: runMode,
    startRun,
    answerClarification,
    confirmIdeas,
    dismissError,
  } = useCookRun();

  const [mode, setMode] = useState<"batch" | "single">("batch");
  const [sourcingMode, setSourcingMode] = useState<SourcingMode>("fridge_plus_shopping");
  const [days, setDays] = useState(DEFAULT_DAYS);
  const [stockItems, setStockItems] = useState<FridgeStockItem[]>([]);
  const [selectedStockIds, setSelectedStockIds] = useState<number[]>([]);
  const [ingredients, setIngredients] = useState<IngredientEntry[]>([]);
  const [freeText, setFreeText] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  // Loaded once on mount — the picker below reads from it, and submit
  // needs the full items (not just ids) to build the request payload.
  useEffect(() => {
    void listFridgeStockItems().then(setStockItems);
  }, []);

  /** Build the request payload and hand it to `CookRunProvider`, which
   * owns everything from here on (the SSE connection, reasoning, any
   * clarification/idea-selection pause). */
  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (selectedStockIds.length === 0 && ingredients.length === 0 && !freeText.trim()) {
      setValidationError("Pick something from your fridge, add an ingredient, or describe what you have.");
      return;
    }
    setValidationError(null);
    dismissError();

    const selectedStockItems = stockItems.filter((item) => selectedStockIds.includes(item.id));
    await startRun({
      mode,
      sourcing_mode: sourcingMode,
      days: mode === "batch" ? days : undefined,
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
  };

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

          {mode === "batch" && (
            <div className="field">
              <label htmlFor="days">Number of days to cook for</label>
              <input
                id="days"
                type="number"
                min={MIN_DAYS}
                max={MAX_DAYS}
                value={days}
                onChange={(event) => setDays(Number(event.target.value))}
              />
            </div>
          )}

          <div className="field">
            <span className="field-label">From your fridge</span>
            <FridgeStockPicker
              items={stockItems}
              selectedIds={selectedStockIds}
              onChange={setSelectedStockIds}
            />
          </div>

          <div className="field">
            <span className="field-label">Sourcing</span>
            <div className="segmented">
              <button
                type="button"
                className={sourcingMode === "fridge_only" ? "active" : ""}
                onClick={() => setSourcingMode("fridge_only")}
              >
                Fridge only
              </button>
              <button
                type="button"
                className={sourcingMode === "fridge_plus_shopping" ? "active" : ""}
                onClick={() => setSourcingMode("fridge_plus_shopping")}
              >
                Fridge + top-up
              </button>
              <button
                type="button"
                className={sourcingMode === "shopping_only" ? "active" : ""}
                onClick={() => setSourcingMode("shopping_only")}
              >
                Shopping list
              </button>
            </div>
            <p className="field-hint">
              {sourcingMode === "fridge_only" &&
                "Only what's already available — nothing to buy."}
              {sourcingMode === "fridge_plus_shopping" &&
                "Prefer the fridge, but a few extra ingredients can go on a shopping list."}
              {sourcingMode === "shopping_only" &&
                "Plan freely — everything beyond pantry staples goes on the shopping list."}
            </p>
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

          <ApiErrorMessage error={validationError ?? runError} />

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Thinking…" : "Get suggestions"}
          </button>
        </form>
      </div>

      {streamingActive && <ReasoningBlock reasoning={reasoning} active={true} />}
      {reasoning && !streamingActive && !runError && (
        <ReasoningBlock reasoning={reasoning} active={false} />
      )}

      {ideas && ideas.length > 0 && (
        <DishIdeaSelector
          ideas={ideas}
          mode={runMode}
          submitting={false}
          onConfirm={(selectedIndexes) => void confirmIdeas(selectedIndexes)}
        />
      )}

      {clarification && (
        <ClarificationModal
          question={clarification.question}
          options={clarification.options}
          submitting={false}
          onAnswer={(answer) => void answerClarification(answer)}
        />
      )}
    </>
  );
}
