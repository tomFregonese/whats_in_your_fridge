import { useState } from "react";
import type { KeyboardEvent } from "react";

interface TagListInputProps {
  label: string;
  placeholder?: string;
  values: string[];
  onChange: (values: string[]) => void;
}

export function TagListInput({ label, placeholder, values, onChange }: TagListInputProps) {
  const [draft, setDraft] = useState("");

  function handleAdd(): void {
    const trimmed = draft.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setDraft("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    // No <form> here on purpose: this component is always used inside
    // another <form> (see Onboarding's DetailsStep), and HTML doesn't
    // support nested forms — the inner one gets silently absorbed into the
    // outer one, so its submit button would submit the wrong form. Handle
    // Enter manually instead, and stop it from bubbling to the real form.
    if (event.key === "Enter") {
      event.preventDefault();
      handleAdd();
    }
  }

  function handleRemove(value: string): void {
    onChange(values.filter((v) => v !== value));
  }

  return (
    <div className="field">
      <label htmlFor={`tag-input-${label}`}>{label}</label>
      <div className="tag-list-input-form">
        <input
          id={`tag-input-${label}`}
          type="text"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
        />
        <button type="button" className="btn btn-secondary" onClick={handleAdd}>
          Add
        </button>
      </div>
      {values.length > 0 && (
        <ul className="tag-list">
          {values.map((value) => (
            <li key={value}>
              <span>{value}</span>
              <button
                type="button"
                onClick={() => handleRemove(value)}
                aria-label={`Remove ${value}`}
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
