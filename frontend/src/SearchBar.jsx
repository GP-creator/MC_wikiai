import React, { useState } from "react";

export default function SearchBar({ onSubmit, loading }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    onSubmit(q);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex w-full items-stretch gap-2 rounded-md border border-edge bg-panel p-1 focus-within:border-accent">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask anything about Minecraft Java 1.21…"
          spellCheck={false}
          autoFocus
          disabled={loading}
          className="flex-1 bg-transparent px-3 py-3 font-mono text-[15px] text-text placeholder:text-muted focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="select-none rounded-sm bg-accent px-4 font-mono text-sm font-medium text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-edge disabled:text-muted"
        >
          {loading ? "…" : "ask"}
        </button>
      </div>
    </form>
  );
}
