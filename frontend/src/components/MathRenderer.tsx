import React, { useMemo } from 'react';
import katex from 'katex';
import { MathToken } from '../types';

interface MathRendererProps {
  text: string;
  mathTokens?: MathToken[];
  className?: string;
}

interface SegmentItem {
  type: 'text' | 'token' | 'display_math' | 'inline_math';
  content: string;
}

export const MathRenderer: React.FC<MathRendererProps> = ({
  text,
  mathTokens = [],
  className = '',
}) => {
  const renderedElements = useMemo(() => {
    if (!text) return null;

    const tokenMap = new Map<string, MathToken>();
    mathTokens.forEach((t) => tokenMap.set(t.token_placeholder, t));

    // Regex kết hợp nhận diện:
    // 1. Placeholder Token: <<<MATH_TOKEN_\d+>>>
    // 2. Display Math: $$ ... $$ hoặc \[ ... \]
    // 3. Inline Math: $ ... $ hoặc \( ... \)
    const MATH_REGEX =
      /(<<<MATH_TOKEN_\d+>>>|\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\$[^\$\n]+?\$|\\\([\s\S]+?\\\))/g;

    const parts = text.split(MATH_REGEX);

    const segments: SegmentItem[] = [];

    for (const part of parts) {
      if (!part) continue;

      if (part.startsWith('<<<MATH_TOKEN_') && part.endsWith('>>>')) {
        segments.push({ type: 'token', content: part });
      } else if (
        (part.startsWith('$$') && part.endsWith('$$') && part.length >= 4) ||
        (part.startsWith('\\[') && part.endsWith('\\]') && part.length >= 4)
      ) {
        const rawLatex = part.startsWith('$$')
          ? part.slice(2, -2).trim()
          : part.slice(2, -2).trim();
        segments.push({ type: 'display_math', content: rawLatex });
      } else if (
        (part.startsWith('$') && part.endsWith('$') && part.length >= 2) ||
        (part.startsWith('\\(') && part.endsWith('\\)') && part.length >= 4)
      ) {
        const rawLatex = part.startsWith('$')
          ? part.slice(1, -1).trim()
          : part.slice(2, -2).trim();
        segments.push({ type: 'inline_math', content: rawLatex });
      } else {
        segments.push({ type: 'text', content: part });
      }
    }

    return segments.map((seg, idx) => {
      if (seg.type === 'token') {
        const token = tokenMap.get(seg.content);
        if (token) {
          try {
            const html = katex.renderToString(token.raw_latex, {
              displayMode: token.is_display_math,
              throwOnError: false,
            });
            return (
              <span
                key={`tok-${idx}`}
                className={
                  token.is_display_math
                    ? 'math-display my-2 block overflow-x-auto text-center'
                    : 'math-inline px-0.5 inline-block align-baseline'
                }
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          } catch {
            return (
              <code
                key={`tok-err-${idx}`}
                className="text-rose-600 bg-rose-50 px-1 py-0.5 rounded text-xs font-mono"
              >
                {token.raw_latex}
              </code>
            );
          }
        }
        return <span key={`raw-tok-${idx}`}>{seg.content}</span>;
      }

      if (seg.type === 'display_math') {
        try {
          const html = katex.renderToString(seg.content, {
            displayMode: true,
            throwOnError: false,
          });
          return (
            <span
              key={`disp-${idx}`}
              className="math-display my-2 block overflow-x-auto text-center"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        } catch {
          return (
            <code
              key={`disp-err-${idx}`}
              className="text-rose-600 bg-rose-50 px-1 py-0.5 rounded text-xs font-mono block text-center"
            >
              $${seg.content}$$
            </code>
          );
        }
      }

      if (seg.type === 'inline_math') {
        try {
          const html = katex.renderToString(seg.content, {
            displayMode: false,
            throwOnError: false,
          });
          return (
            <span
              key={`inl-${idx}`}
              className="math-inline px-0.5 inline-block align-baseline"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        } catch {
          return (
            <code
              key={`inl-err-${idx}`}
              className="text-rose-600 bg-rose-50 px-1 py-0.5 rounded text-xs font-mono"
            >
              ${seg.content}$
            </code>
          );
        }
      }

      return <span key={`txt-${idx}`}>{seg.content}</span>;
    });
  }, [text, mathTokens]);

  return <div className={`leading-relaxed text-slate-800 ${className}`}>{renderedElements}</div>;
};
