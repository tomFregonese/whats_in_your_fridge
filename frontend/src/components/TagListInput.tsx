import { useState } from "react";
import type { FormEvent } from "react";

interface TagListInputProps {
  label: string;
  placeholder?: string;
  values: string[];
  onChange: (values: string[]) => void;
}

export function TagListInput({ label, placeholder, values, onChange }: TagListInputProps) {
  const [draft, setDraft] = useState("");

  function handleAdd(event: FormEvent): void {
    event.preventDefault();
    const trimmed = draft.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setDraft("");
  }

  function handleRemove(value: string): void {
    onChange(values.filter((v) => v !== value));
  }

  return (
    <div className="tag-list-input">
      <label htmlFor={`tag-input-${label}`}>{label}</label>
      <form onSubmit={handleAdd} className="tag-list-input-form">
        <input
          id={`tag-input-${label}`}
          type="text"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={placeholder}
        />
        <button type="submit">Add</button>
      </form>
      {values.length > 0 && (
        <ul className="tag-list">
          {values.map((value) => (
            <li key={value}>
              <span>{value}</span>
              <button type="button" onClick={() => handleRemove(value)} aria-label={`Remove ${value}`}>
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
