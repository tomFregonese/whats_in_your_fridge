import { useState } from "react";
import type { KeyboardEvent } from "react";

export interface IngredientEntry {
  name: string;
  quantity: string;
}

interface IngredientListInputProps {
  items: IngredientEntry[];
  onChange: (items: IngredientEntry[]) => void;
  label?: string;
}

export function IngredientListInput({
  items,
  onChange,
  label = "Ingredients",
}: IngredientListInputProps) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");

  function handleAdd(): void {
    const trimmed = name.trim();
    if (!trimmed) return;
    onChange([...items, { name: trimmed, quantity: quantity.trim() }]);
    setName("");
    setQuantity("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    // No <form> here on purpose — same reasoning as TagListInput: this
    // lives inside FridgeInputForm's own <form>, and HTML doesn't support
    // nested forms.
    if (event.key === "Enter") {
      event.preventDefault();
      handleAdd();
    }
  }

  function handleRemove(index: number): void {
    onChange(items.filter((_, i) => i !== index));
  }

  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="ingredient-input-row">
        <input
          type="text"
          placeholder="Ingredient (e.g. carrot)"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          type="text"
          placeholder="Quantity (optional)"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="button" className="btn btn-secondary" onClick={handleAdd}>
          Add
        </button>
      </div>
      {items.length > 0 && (
        <ul className="tag-list">
          {items.map((item, index) => (
            <li key={`${item.name}-${index}`}>
              <span>
                {item.name}
                {item.quantity && <span className="model-meta"> · {item.quantity}</span>}
              </span>
              <button
                type="button"
                onClick={() => handleRemove(index)}
                aria-label={`Remove ${item.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
