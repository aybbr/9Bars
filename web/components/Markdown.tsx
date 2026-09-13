"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/cn";

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("text-[15px] leading-relaxed text-cream", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-crema-soft">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 marker:text-copper">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 marker:text-copper">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-copper underline decoration-copper/40 underline-offset-2 hover:text-crema-soft">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-crema/40 pl-3 text-cream-dim">{children}</blockquote>
          ),
          code: ({ className, children }) => (
            <code className={cn("rounded bg-ground-3 px-1.5 py-0.5 font-mono text-[13px] text-cream-soft", className)}>
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="my-2 overflow-x-auto rounded-lg border border-line-soft bg-ground-3 p-3 font-mono text-[13px]">
              {children}
            </pre>
          ),
          h1: ({ children }) => <h3 className="mt-4 font-display text-lg text-cream">{children}</h3>,
          h2: ({ children }) => <h3 className="mt-4 font-display text-lg text-cream">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-3 font-display text-base text-cream">{children}</h4>,
          h4: ({ children }) => <h4 className="mt-3 text-sm font-semibold text-cream">{children}</h4>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
