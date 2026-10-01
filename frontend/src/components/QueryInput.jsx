import { useState } from "react";

export default function QueryInput({ onSubmit, disabled }) {
  const [query, setQuery] = useState("");

  const submit = (event) => {
    event.preventDefault();
    if (query.trim()) onSubmit(query.trim());
  };

  return (
    <form className="search" onSubmit={submit}>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Ask a research question about AI/ML literature"
        disabled={disabled}
      />
      <button className="btn-primary" type="submit" disabled={disabled || !query.trim()}>
        Ask
      </button>
    </form>
  );
}
