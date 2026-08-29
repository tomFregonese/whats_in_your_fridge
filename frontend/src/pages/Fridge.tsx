import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { FridgeStockItem } from "../api/fridgeStock";
import {
  addFridgeStockItem,
  deleteFridgeStockItem,
  listFridgeStockItems,
  updateFridgeStockItem,
} from "../api/fridgeStock";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import { AppLayout } from "../components/AppLayout";
import { VoiceDictation } from "../components/VoiceDictation";

/** Routed at `/fridge` — the persistent ingredient inventory (unlike
 * `FridgeInputForm`'s per-generation, throwaway entry). What's added or
 * edited here is what shows up as clickable chips on the suggestion page
 * (`FridgeStockPicker`), and what automatic deduction removes from once a
 * meal plan is generated (see the project plan). */
export function Fridge() {
  const [items, setItems] = useState<FridgeStockItem[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    void listFridgeStockItems()
      .then(setItems)
      .catch((err: unknown) => setError(err));
  }, []);

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
