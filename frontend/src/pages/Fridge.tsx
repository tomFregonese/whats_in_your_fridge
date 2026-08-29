import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { FridgeStockItem, MergeSuggestion } from "../api/fridgeStock";
import {
  addFridgeStockItem,
  deleteFridgeStockItem,
  dismissMergeSuggestion,
  listFridgeStockItems,
  listMergeSuggestions,
  mergeFridgeStockItems,
  updateFridgeStockItem,
} from "../api/fridgeStock";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import { AppLayout } from "../components/AppLayout";
import { VoiceDictation } from "../components/VoiceDictation";

// How long to wait after the ingredient list settles before rechecking
// for duplicates — collapses a burst of quick edits (e.g. dictating
// several items in a row) into one check instead of one per mutation.
const DUPLICATE_CHECK_DEBOUNCE_MS = 400;

/** Routed at `/fridge` — the persistent ingredient inventory (unlike
 * `FridgeInputForm`'s per-generation, throwaway entry). What's added or
 * edited here is what shows up as clickable chips on the suggestion page
 * (`FridgeStockPicker`), and what automatic deduction removes from once a
 * meal plan is generated (see the project plan). */
export function Fridge() {
  const [items, setItems] = useState<FridgeStockItem[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([]);
  const [checkingDuplicates, setCheckingDuplicates] = useState(false);
  const [busyItemIds, setBusyItemIds] = useState<Set<number>>(new Set());
  // Discards a duplicate-check result that's no longer the latest one in
  // flight — same "stale async result" guard shape as `VoiceDictation.tsx`'s
  // `sessionIdRef`, needed here because the list can change again (another
  // edit, another dictation) before a slower check from before it resolves.
  const duplicateCheckGenerationRef = useRef(0);

  useEffect(() => {
    void listFridgeStockItems()
      .then(setItems)
      .catch((err: unknown) => setError(err));
  }, []);

  // Rechecks for duplicates on the initial load (satisfies "every time the
  // app opens") and after every settled mutation (add/save/delete/dictate/
  // merge/dismiss all change `items`; in-progress edit keystrokes live in
  // `FridgeItemRow`'s own local state and never touch it, so they don't
  // spuriously retrigger this). Silent on failure by design — the
  // household's own fridge list must never show an error just because the
  // local model is briefly slow or the `nlp` container is down.
  useEffect(() => {
    if (items === null || items.length < 2) {
      setSuggestions([]);
      return;
    }
    const generation = ++duplicateCheckGenerationRef.current;
    const timer = window.setTimeout(() => {
      setCheckingDuplicates(true);
      listMergeSuggestions()
        .then((result) => {
          if (duplicateCheckGenerationRef.current === generation) setSuggestions(result);
        })
        .catch(() => {
          if (duplicateCheckGenerationRef.current === generation) setSuggestions([]);
        })
        .finally(() => {
          if (duplicateCheckGenerationRef.current === generation) setCheckingDuplicates(false);
        });
    }, DUPLICATE_CHECK_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [items]);

  function markBusy(ids: number[]): void {
    setBusyItemIds((prev) => new Set([...prev, ...ids]));
  }

  function clearBusy(ids: number[]): void {
    setBusyItemIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) next.delete(id);
      return next;
    });
  }

  async function handleMergeSuggestion(suggestion: MergeSuggestion): Promise<void> {
    const { item_a, item_b, suggested_name } = suggestion;
    markBusy([item_a.id, item_b.id]);
    try {
      const merged = await mergeFridgeStockItems(item_a.id, item_b.id, suggested_name);
      setItems((prev) =>
        (prev ?? [])
          .filter((item) => item.id !== item_b.id)
          .map((item) => (item.id === merged.id ? merged : item))
          .sort((a, b) => a.ingredient_name.localeCompare(b.ingredient_name)),
      );
      // Cosmetic only — the `items` change above re-triggers the debounced
      // recheck effect a moment later, which is the source of truth.
      setSuggestions((prev) => prev.filter((s) => s !== suggestion));
    } catch (err) {
      setError(err);
      // A concurrent action (e.g. an overlapping merge on one of these two
      // items) most likely changed something here — reconcile with the
      // server rather than guess.
      void listFridgeStockItems().then(setItems);
    } finally {
      clearBusy([item_a.id, item_b.id]);
    }
  }

  async function handleDismissSuggestion(suggestion: MergeSuggestion): Promise<void> {
    const { item_a, item_b } = suggestion;
    markBusy([item_a.id, item_b.id]);
    try {
      await dismissMergeSuggestion(item_a.ingredient_name, item_b.ingredient_name);
      setSuggestions((prev) => prev.filter((s) => s !== suggestion));
    } catch (err) {
      setError(err);
    } finally {
      clearBusy([item_a.id, item_b.id]);
    }
  }

  async function handleAdd(name: string, quantity: string): Promise<void> {
    setError(null);
    try {
      const created = await addFridgeStockItem({
        ingredient_name: name,
        quantity_raw: quantity || null,
      });
      setItems((prev) =>
        [...(prev ?? []), created].sort((a, b) =>
          a.ingredient_name.localeCompare(b.ingredient_name),
        ),
      );
    } catch (err) {
      setError(err);
    }
  }

  async function handleSave(id: number, name: string, quantity: string): Promise<void> {
    setError(null);
    try {
      const updated = await updateFridgeStockItem(id, {
        ingredient_name: name,
        quantity_raw: quantity || null,
      });
      setItems((prev) => prev?.map((item) => (item.id === id ? updated : item)) ?? null);
    } catch (err) {
      setError(err);
    }
  }

  async function handleDelete(id: number): Promise<void> {
    setError(null);
    try {
      await deleteFridgeStockItem(id);
      setItems((prev) => prev?.filter((item) => item.id !== id) ?? null);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <AppLayout>
      <div className="page-header">
        <h1>🧊 Your fridge</h1>
        <p>What's in stock, saved between sessions — pick from it next time you ask for ideas.</p>
      </div>

      <ApiErrorMessage error={error} />

      <div className="card">
        <div className="card-header">
          <h2>🎙️ Dictate</h2>
        </div>
        <p className="card-description">
          Say what you've got — we'll figure out the ingredients and quantities.
        </p>
        <VoiceDictation
          onCommitted={(committed) => {
            setItems((prev) => {
              const byId = new Map((prev ?? []).map((item) => [item.id, item]));
              for (const item of committed) byId.set(item.id, item);
              return [...byId.values()].sort((a, b) =>
                a.ingredient_name.localeCompare(b.ingredient_name),
              );
            });
          }}
        />
      </div>

      {suggestions.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2>Possible duplicates</h2>
            {checkingDuplicates && (
              <span className="connection-status">
                <span className="connection-dot pending" />
                Checking…
              </span>
            )}
          </div>
          <ul className="merge-suggestion-list">
            {suggestions.map((suggestion) => {
              const busy =
                busyItemIds.has(suggestion.item_a.id) || busyItemIds.has(suggestion.item_b.id);
              return (
                <li
                  key={`${String(suggestion.item_a.id)}-${String(suggestion.item_b.id)}`}
                  className="merge-suggestion-row"
                >
                  <span className="merge-suggestion-names">
                    <span>{suggestion.item_a.ingredient_name}</span>
                    <span className="merge-suggestion-connector" aria-hidden="true">
                      ↔
                    </span>
                    <span>{suggestion.item_b.ingredient_name}</span>
                  </span>
                  <span className="merge-suggestion-actions">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={busy}
                      onClick={() => void handleMergeSuggestion(suggestion)}
                    >
                      {busy ? "Working…" : `Merge as "${suggestion.suggested_name}"?`}
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={busy}
                      onClick={() => void handleDismissSuggestion(suggestion)}
                    >
                      Dismiss
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>Add an ingredient</h2>
        </div>
        <AddItemForm onAdd={handleAdd} />
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Ingredients</h2>
        </div>
        {items === null ? (
          <p className="empty">Loading…</p>
        ) : items.length === 0 ? (
          <p className="empty">Nothing in your fridge yet — add what you've got above.</p>
        ) : (
          <ul className="fridge-item-list">
            {items.map((item) => (
              <FridgeItemRow
                key={item.id}
                item={item}
                onSave={(name, quantity) => void handleSave(item.id, name, quantity)}
                onDelete={() => void handleDelete(item.id)}
              />
            ))}
          </ul>
        )}
      </div>
    </AppLayout>
  );
}

function AddItemForm({
  onAdd,
}: {
  onAdd: (name: string, quantity: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setSubmitting(true);
    await onAdd(trimmed, quantity.trim());
    setSubmitting(false);
    setName("");
    setQuantity("");
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="ingredient-input-row">
      <input
        type="text"
        placeholder="Ingredient (e.g. carrot)"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <input
        type="text"
        placeholder="Quantity (optional)"
        value={quantity}
        onChange={(event) => setQuantity(event.target.value)}
      />
      <button type="submit" className="btn btn-secondary" disabled={submitting}>
        Add
      </button>
    </form>
  );
}

function FridgeItemRow({
  item,
  onSave,
  onDelete,
}: {
  item: FridgeStockItem;
  onSave: (name: string, quantity: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(item.ingredient_name);
  const [quantity, setQuantity] = useState(item.quantity_raw ?? "");

  if (editing) {
    return (
      <li className="fridge-item-row fridge-item-row-editing">
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          aria-label="Ingredient name"
          autoFocus
        />
        <input
          type="text"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          aria-label="Quantity"
        />
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => {
            const trimmed = name.trim();
            if (!trimmed) return;
            onSave(trimmed, quantity.trim());
            setEditing(false);
          }}
        >
          Save
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => {
            setName(item.ingredient_name);
            setQuantity(item.quantity_raw ?? "");
            setEditing(false);
          }}
        >
          Cancel
        </button>
      </li>
    );
  }

  return (
    <li className="fridge-item-row">
      <span className="fridge-item-name">
        {item.ingredient_name}
        {item.quantity_raw && <span className="model-meta"> · {item.quantity_raw}</span>}
      </span>
      <span className="fridge-item-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
          Edit
        </button>
        <button
          type="button"
          className="btn btn-danger-ghost btn-sm"
          onClick={onDelete}
          aria-label={`Remove ${item.ingredient_name}`}
        >
          ×
        </button>
      </span>
    </li>
  );
}
