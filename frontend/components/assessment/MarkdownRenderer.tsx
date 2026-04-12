// components/assessment/MarkdownRenderer.tsx
// Minimal markdown renderer for MCQ stem text.
// Handles: fenced code blocks · inline code · bold · italics · line breaks
// No external dependencies.

import React from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Split text on fenced code blocks and return an array of typed segments. */
function splitSegments(text: string): Array<{ type: "code"; lang: string; body: string } | { type: "text"; body: string }> {
  const segments: Array<{ type: "code"; lang: string; body: string } | { type: "text"; body: string }> = [];
  const codeBlockRe = /```(\w*)\n([\s\S]*?)```/g;

  let lastIdx = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRe.exec(text)) !== null) {
    if (match.index > lastIdx) {
      segments.push({ type: "text", body: text.slice(lastIdx, match.index) });
    }
    segments.push({ type: "code", lang: match[1] || "text", body: match[2] });
    lastIdx = match.index + match[0].length;
  }

  if (lastIdx < text.length) {
    segments.push({ type: "text", body: text.slice(lastIdx) });
  }

  return segments;
}

/** Render an inline markdown string (bold, italic, inline code, newlines). */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  // Split on bold, italic, inline code patterns
  const parts = text.split(/(\*\*[\s\S]+?\*\*|`[^`]+`|\*[\s\S]+?\*)/g);

  return parts.flatMap((part, i): React.ReactNode[] => {
    const key = `${keyPrefix}-${i}`;

    // Bold
    if (part.startsWith("**") && part.endsWith("**")) {
      return [<strong key={key} className="font-semibold">{part.slice(2, -2)}</strong>];
    }
    // Inline code
    if (part.startsWith("`") && part.endsWith("`")) {
      return [
        <code
          key={key}
          className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-sm text-primary-700 dark:text-primary-300"
        >
          {part.slice(1, -1)}
        </code>,
      ];
    }
    // Italic
    if (part.startsWith("*") && part.endsWith("*")) {
      return [<em key={key}>{part.slice(1, -1)}</em>];
    }
    // Plain text — convert newlines to <br>
    return part.split("\n").flatMap((line, j, arr): React.ReactNode[] => {
      const nodes: React.ReactNode[] = [<React.Fragment key={`${key}-${j}`}>{line}</React.Fragment>];
      if (j < arr.length - 1) nodes.push(<br key={`${key}-${j}-br`} />);
      return nodes;
    });
  });
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface Props {
  text: string;
  className?: string;
}

export default function MarkdownRenderer({ text, className = "" }: Props) {
  const segments = splitSegments(text.trim());

  return (
    <div className={className}>
      {segments.map((seg, i) => {
        if (seg.type === "code") {
          return (
            <pre
              key={i}
              className="my-3 overflow-x-auto rounded-xl bg-slate-900 dark:bg-slate-950 p-4 text-sm leading-relaxed shadow-inner"
            >
              {seg.lang && (
                <span className="mb-2 block text-xs font-medium text-slate-500 uppercase tracking-wide">
                  {seg.lang}
                </span>
              )}
              <code className="font-mono text-slate-100">{seg.body.trimEnd()}</code>
            </pre>
          );
        }
        return (
          <p key={i} className="leading-relaxed">
            {renderInline(seg.body, String(i))}
          </p>
        );
      })}
    </div>
  );
}
