import React from "react";

function ConfidenceBadge({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  let label = "low";
  let color = "text-muted border-edge";
  if (pct >= 70) {
    label = "high";
    color = "text-accent border-accent/40";
  } else if (pct >= 40) {
    label = "medium";
    color = "text-text border-edge";
  }
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-sm border px-2 py-1 font-mono text-[11px] uppercase tracking-wider ${color}`}
      title={`${pct}% confidence`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label} confidence
    </span>
  );
}

function VersionBadge() {
  return (
    <span className="rounded-sm border border-edge px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-muted">
      Java Edition 1.21
    </span>
  );
}

function renderAnswer(text) {
  if (!text) return null;
  // Split on blank lines into paragraphs, render bullet runs as a list.
  const blocks = text.split(/\n\s*\n/);
  return blocks.map((block, i) => {
    const lines = block.split(/\n/).map((l) => l.trim()).filter(Boolean);
    const allBullets = lines.length > 1 && lines.every((l) => /^[-*]\s+/.test(l));
    if (allBullets) {
      return (
        <ul key={i} className="my-2 list-disc space-y-1 pl-5 text-[15px] leading-relaxed text-text">
          {lines.map((l, j) => (
            <li key={j}>{l.replace(/^[-*]\s+/, "")}</li>
          ))}
        </ul>
      );
    }
    return (
      <p key={i} className="my-2 text-[15px] leading-relaxed text-text">
        {block}
      </p>
    );
  });
}

export default function AnswerCard({ result }) {
  if (!result) return null;
  const { answer, sources = [], confidence } = result;

  return (
    <article className="w-full rounded-md border border-edge bg-panel p-6">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-mono text-xs uppercase tracking-wider text-muted">Answer</h2>
        <div className="flex items-center gap-2">
          <ConfidenceBadge value={confidence} />
          <VersionBadge />
        </div>
      </header>

      <div className="border-l-2 border-accent/50 pl-4">{renderAnswer(answer)}</div>

      {sources.length > 0 && (
        <section className="mt-6">
          <h3 className="mb-3 font-mono text-xs uppercase tracking-wider text-muted">Sources</h3>
          <ul className="space-y-3">
            {sources.map((s, i) => (
              <li key={i} className="rounded-sm border border-edge bg-ink/40 p-3">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-sm font-medium text-accent hover:underline"
                >
                  {s.title}
                </a>
                <p className="mt-1 text-[13px] leading-relaxed text-muted">{s.snippet}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
