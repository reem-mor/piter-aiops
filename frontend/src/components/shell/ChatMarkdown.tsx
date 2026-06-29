import { useMemo, useState } from "react";

const COLLAPSE_CHARS = 900;

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*|__([^_]+)__/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(
      <strong key={key++}>{m[1] ?? m[2]}</strong>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : [text];
}

function parseBlocks(raw: string): React.ReactNode[] {
  const lines = raw.replace(/\r\n/g, "\n").split("\n");
  const out: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    if (/^#{1,3}\s+/.test(line)) {
      const text = line.replace(/^#{1,3}\s+/, "");
      out.push(
        <p key={key++} className="chat-md-heading">
          {renderInline(text)}
        </p>,
      );
      i += 1;
      continue;
    }
    if (/^[-*•]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*•]\s+/, ""));
        i += 1;
      }
      out.push(
        <ul key={key++} className="chat-md-list">
          {items.map((item, j) => (
            <li key={j}>{renderInline(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      out.push(
        <ol key={key++} className="chat-md-list chat-md-olist">
          {items.map((item, j) => (
            <li key={j}>{renderInline(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^#{1,3}\s+/.test(lines[i]) && !/^[-*•]\s+/.test(lines[i]) && !/^\d+\.\s+/.test(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    out.push(
      <p key={key++} className="chat-md-para">
        {renderInline(para.join(" "))}
      </p>,
    );
  }
  return out;
}

export function ChatMarkdown({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const cleaned = useMemo(() => text.replace(/^#{1,6}\s+/gm, "").trim(), [text]);
  const needsCollapse = cleaned.length > COLLAPSE_CHARS;
  const display = needsCollapse && !expanded ? `${cleaned.slice(0, COLLAPSE_CHARS)}…` : cleaned;
  const blocks = useMemo(() => parseBlocks(display), [display]);

  return (
    <div className="chat-md">
      {blocks}
      {needsCollapse ? (
        <button type="button" className="chat-md-more" onClick={() => setExpanded((e) => !e)}>
          {expanded ? "Show less" : "Show more"}
        </button>
      ) : null}
    </div>
  );
}
