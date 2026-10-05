import React, { useMemo } from 'react';
import katex from 'katex';
import { MathToken } from '../types';

interface MathRendererProps {
  text: string;
  mathTokens?: MathToken[];
  className?: string;
}

export const MathRenderer: React.FC<MathRendererProps> = ({ text, mathTokens = [], className = '' }) => {
  const renderedElements = useMemo(() => {
    if (!text) return null;

    const tokenMap = new Map<string, MathToken>();
    mathTokens.forEach((t) => tokenMap.set(t.token_placeholder, t));

    // Split text by placeholder tokens <<<MATH_TOKEN_\d+>>>
    const parts = text.split(/(<<<MATH_TOKEN_\d+>>>)/g);

    return parts.map((part, index) => {
      const token = tokenMap.get(part);
      if (token) {
        try {
          const html = katex.renderToString(token.raw_latex, {
            displayMode: token.is_display_math,
            throwOnError: false,
          });
          return (
            <span
              key={`token-${index}`}
              className={token.is_display_math ? 'math-display my-2 block overflow-x-auto text-center' : 'math-inline px-0.5 inline-block align-baseline'}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        } catch {
          return (
            <code key={`token-err-${index}`} className="text-rose-600 bg-rose-50 px-1 py-0.5 rounded text-xs font-mono">
              {token.raw_latex}
            </code>
          );
        }
      }

      return <span key={`text-${index}`}>{part}</span>;
    });
  }, [text, mathTokens]);

  return <div className={`leading-relaxed text-slate-800 ${className}`}>{renderedElements}</div>;
};
