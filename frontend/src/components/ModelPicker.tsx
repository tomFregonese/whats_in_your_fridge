import { useEffect, useState } from "react";
import type { FreeModel } from "../api/settings";
import { listFreeModels } from "../api/settings";

interface ModelPickerProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

type State = "loading" | "ready" | "error";

export function ModelPicker({ selectedId, onSelect }: ModelPickerProps) {
  const [models, setModels] = useState<FreeModel[]>([]);
  const [state, setState] = useState<State>("loading");

  async function load(): Promise<void> {
    setState("loading");
    try {
      setModels(await listFreeModels());
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") {
    return <p className="empty">Loading available models…</p>;
  }

  if (state === "error") {
    return (
      <div className="model-picker-error">
        <p className="error">Couldn't reach OpenRouter's model catalog.</p>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => void load()}>
          Retry
        </button>
      </div>
    );
  }

  if (models.length === 0) {
    return <p className="empty">No free models currently listed by OpenRouter.</p>;
  }

  return (
    <ul className="model-picker">
      {models.map((model) => (
        <li key={model.id}>
          <label>
            <input
              type="radio"
              name="model"
              value={model.id}
              checked={selectedId === model.id}
              onChange={() => onSelect(model.id)}
            />
            <span className="model-name">{model.name}</span>
            {model.context_length !== null && (
              <span className="model-meta">{model.context_length.toLocaleString()} tokens</span>
            )}
          </label>
        </li>
      ))}
    </ul>
  );
}
