import { Link } from "react-router-dom";
import type { FridgeStockItem } from "../api/fridgeStock";

interface FridgeStockPickerProps {
  items: FridgeStockItem[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

/** Click-to-select chips for the persistent fridge inventory (see
 * `pages/Fridge.tsx`) — lets `FridgeInputForm` reuse what's already saved
 * instead of retyping it every time. `items` is fetched once by the parent
 * (which also needs it to build the submission payload — see
 * `FridgeInputForm.handleSubmit`) rather than re-fetched here.
 *
 * Selecting a chip only makes that ingredient *available* to the agent for
 * this generation, same as a free-typed one always was; only what the
 * recipe(s) actually end up using gets deducted afterward (see the project
 * plan). */
export function FridgeStockPicker({ items, selectedIds, onChange }: FridgeStockPickerProps) {
  function toggle(id: number): void {
    onChange(
      selectedIds.includes(id) ? selectedIds.filter((i) => i !== id) : [...selectedIds, id],
    );
  }

  if (items.length === 0) {
    return (
      <p className="empty">
        Your fridge is empty — <Link to="/fridge">add what you've got</Link> to pick from it here.
      </p>
    );
  }

  return (
    <ul className="tag-list tag-list--selectable">
      {items.map((item) => (
        <li key={item.id}>
          <label>
            <input
              type="checkbox"
              checked={selectedIds.includes(item.id)}
              onChange={() => toggle(item.id)}
            />
            <span>
              {item.ingredient_name}
              {item.quantity_raw && <span className="model-meta"> · {item.quantity_raw}</span>}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
}
