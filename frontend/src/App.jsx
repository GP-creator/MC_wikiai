import React, { useState } from "react";
import SearchBar from "./SearchBar.jsx";
import AnswerCard from "./AnswerCard.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const EXAMPLES = [
  "Cheapest enchant order for Sharpness V, Unbreaking III, Mending on a sword",
  "Where should I dig for diamonds in 1.21?",
  "Fortune vs Silk Touch on diamond ore — which is better?",
  "What drops from Blazes and where do they spawn?",
];

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function ask(question) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `request failed (${res.status})`);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full bg-ink">
      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-16 pt-16">
        <header className="flex items-baseline gap-3">
          <h1 className="font-mono text-2xl font-bold tracking-tight text-text">
            <span className="text-accent">&gt;</span> CraftMind
          </h1>
          <span className="font-mono text-xs uppercase tracking-wider text-muted">
            Minecraft Java 1.21 wiki AI
          </span>
        </header>

        <SearchBar onSubmit={ask} loading={loading} />

        {!result && !loading && !error && (
          <section>
            <p className="mb-2 font-mono text-xs uppercase tracking-wider text-muted">
              Try
            </p>
            <ul className="space-y-1">
              {EXAMPLES.map((q) => (
                <li key={q}>
                  <button
                    type="button"
                    onClick={() => ask(q)}
                    className="text-left text-[14px] text-muted transition hover:text-accent"
                  >
                    — {q}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {loading && (
          <div className="rounded-md border border-edge bg-panel p-6 font-mono text-sm text-muted">
            <span className="inline-block animate-pulse">searching wiki…</span>
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-500/40 bg-red-500/10 p-4 font-mono text-sm text-red-300">
            {error}
          </div>
        )}

        {result && <AnswerCard result={result} />}

        <footer className="mt-8 border-t border-edge pt-4 font-mono text-[11px] uppercase tracking-wider text-muted">
          Answers grounded in minecraft.wiki · CC BY-NC-SA 3.0
        </footer>
      </main>
    </div>
  );
}
