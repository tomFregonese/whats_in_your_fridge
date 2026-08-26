import { useState } from "react";
import { ModelPicker } from "./ModelPicker";

interface ModelFieldProps {
  selectedId: string | null;
  onSelect: (id: string) => Promise<void>;
}

/** Collapsed by default (shows the current model id + a "Change" button);
 * expands into the full `ModelPicker` list. Used on both Home (quick
 * access) and Settings (full config). */
export function ModelField({ selectedId, onSelect }: ModelFieldProps) {
  const [expanded, setExpanded] = useState(false);

  async function handleSelect(id: string): Promise<void> {
    await onSelect(id);
    setExpanded(false);
  }

  if (!expanded) {
    return (
      <div className="field-row">
        <div className="field">
          <span className="field-label">Model</span>
          {selectedId ? (
            <span className="field-value">{selectedId}</span>
          ) : (
            <span className="empty">Not set</span>
          )}
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setExpanded(true)}
        >
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="field">
      <div className="field-row">
        <span className="field-label">Model</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded(false)}>
          Cancel
        </button>
      </div>
      <ModelPicker selectedId={selectedId} onSelect={(id) => void handleSelect(id)} />
    </div>
  );
}
