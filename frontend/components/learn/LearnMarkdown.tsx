// components/learn/LearnMarkdown.tsx
// Full markdown renderer for learning content.
// Supports: h1–h3 (with anchor IDs), fenced code blocks, bullet/ordered lists,
//           horizontal rules, blockquotes, inline code, bold, italic, line breaks.
// No external dependencies.

import React from "react";

// ---------------------------------------------------------------------------
// Heading extraction — used by parent for TOC
// ---------------------------------------------------------------------------

export interface Heading {
  id: string;
  text: string;
  level: 1 | 2 | 3;
}

export function extractHeadings(markdown: string): Heading[] {
  const headings: Heading[] = [];
  const lines = markdown.split("\n");
  for (const line of lines) {
    const m = line.match(/^(#{1,3})\s+(.+)/);
    if (m) {
      const level = m[1].length as 1 | 2 | 3;
      const text = m[2].trim();
      headings.push({ id: toSlug(text), text, level });
    }
  }
  return headings;
}

function toSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

// ---------------------------------------------------------------------------
// Inline rendering (bold, italic, inline code)
// ---------------------------------------------------------------------------

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[\s\S]+?\*\*|`[^`]+`|\*[\s\S]+?\*)/g);
  return parts.flatMap((part, i): React.ReactNode[] => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return [<strong key={key} className="font-semibold">{part.slice(2, -2)}</strong>];
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return [
        <code
          key={key}
          className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-sm"
          style={{ color: "var(--color-primary-600)" }}
        >
          {part.slice(1, -1)}
        </code>,
      ];
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return [<em key={key}>{part.slice(1, -1)}</em>];
    }
    return part.split("\n").flatMap((line, j, arr): React.ReactNode[] => {
      const nodes: React.ReactNode[] = [
        <React.Fragment key={`${key}-${j}`}>{line}</React.Fragment>,
      ];
      if (j < arr.length - 1) nodes.push(<br key={`${key}-${j}-br`} />);
      return nodes;
    });
  });
}

// ---------------------------------------------------------------------------
// Block-level token types
// ---------------------------------------------------------------------------

type Token =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "code"; lang: string; body: string }
  | { type: "hr" }
  | { type: "blockquote"; lines: string[] }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "paragraph"; text: string };

// ---------------------------------------------------------------------------
// Tokenizer
// ---------------------------------------------------------------------------

function tokenize(markdown: string): Token[] {
  const tokens: Token[] = [];
  const lines = markdown.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const body: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        body.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      tokens.push({ type: "code", lang, body: body.join("\n") });
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}\s*$/.test(line)) {
      tokens.push({ type: "hr" });
      i++;
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headingMatch) {
      tokens.push({
        type: "heading",
        level: headingMatch[1].length as 1 | 2 | 3,
        text: headingMatch[2].trim(),
      });
      i++;
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      const bqLines: string[] = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        bqLines.push(lines[i].slice(2));
        i++;
      }
      tokens.push({ type: "blockquote", lines: bqLines });
      continue;
    }

    // Unordered list
    if (/^[-*+]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*+]\s/, ""));
        i++;
      }
      tokens.push({ type: "ul", items });
      continue;
    }

    // Ordered list
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ""));
        i++;
      }
      tokens.push({ type: "ol", items });
      continue;
    }

    // Blank line — skip
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph: collect until blank line or block-start
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,3}\s|```|[-*+]\s|\d+\.\s|> |[-*_]{3,})/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      tokens.push({ type: "paragraph", text: paraLines.join("\n") });
    }
  }

  return tokens;
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

function renderToken(token: Token, idx: number): React.ReactNode {
  switch (token.type) {
    case "heading": {
      const id = toSlug(token.text);
      const inline = renderInline(token.text, `h${idx}`);
      if (token.level === 1)
        return (
          <h1 key={idx} id={id} className="mt-8 mb-3 text-2xl font-bold scroll-mt-20" style={{ color: "var(--text-primary)" }}>
            {inline}
          </h1>
        );
      if (token.level === 2)
        return (
          <h2 key={idx} id={id} className="mt-6 mb-2 text-xl font-semibold scroll-mt-20" style={{ color: "var(--text-primary)" }}>
            {inline}
          </h2>
        );
      return (
        <h3 key={idx} id={id} className="mt-5 mb-2 text-base font-semibold scroll-mt-20" style={{ color: "var(--text-primary)" }}>
          {inline}
        </h3>
      );
    }

    case "code":
      return (
        <pre
          key={idx}
          className="my-4 overflow-x-auto rounded-xl bg-slate-900 dark:bg-slate-950 p-4 text-sm leading-relaxed shadow-inner"
        >
          {token.lang && (
            <span className="mb-2 block text-xs font-medium text-slate-500 uppercase tracking-wide">
              {token.lang}
            </span>
          )}
          <code className="font-mono text-slate-100">{token.body.trimEnd()}</code>
        </pre>
      );

    case "hr":
      return <hr key={idx} className="my-6 border-slate-200 dark:border-slate-700" />;

    case "blockquote":
      return (
        <blockquote
          key={idx}
          className="my-3 border-l-4 border-primary-400 pl-4 italic"
          style={{ color: "var(--text-secondary)" }}
        >
          {token.lines.map((l, j) => (
            <p key={j} className="leading-relaxed">
              {renderInline(l, `bq${idx}-${j}`)}
            </p>
          ))}
        </blockquote>
      );

    case "ul":
      return (
        <ul key={idx} className="my-3 ml-5 list-disc space-y-1" style={{ color: "var(--text-primary)" }}>
          {token.items.map((item, j) => (
            <li key={j} className="leading-relaxed">
              {renderInline(item, `ul${idx}-${j}`)}
            </li>
          ))}
        </ul>
      );

    case "ol":
      return (
        <ol key={idx} className="my-3 ml-5 list-decimal space-y-1" style={{ color: "var(--text-primary)" }}>
          {token.items.map((item, j) => (
            <li key={j} className="leading-relaxed">
              {renderInline(item, `ol${idx}-${j}`)}
            </li>
          ))}
        </ol>
      );

    case "paragraph":
      return (
        <p key={idx} className="my-3 leading-7" style={{ color: "var(--text-primary)" }}>
          {renderInline(token.text, `p${idx}`)}
        </p>
      );
  }
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface Props {
  markdown: string;
  className?: string;
}

export default function LearnMarkdown({ markdown, className = "" }: Props) {
  const tokens = tokenize(markdown.trim());
  return (
    <div className={`prose-learn ${className}`}>
      {tokens.map((t, i) => renderToken(t, i))}
    </div>
  );
}
